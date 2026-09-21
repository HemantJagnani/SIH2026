"""
Gemini AI-Assisted Anomaly Verifier — Phase 9 §7–§9.

Gemini is invoked ONLY when:
1. Deterministic validation passes but an anomaly remains,
2. A controlled refetch did not resolve the anomaly,
3. The observation is sufficiently important to verify.

Safety rules (spec Phase 9 §8):
- Gemini NEVER invents a fare.
- Gemini NEVER modifies the original observation.
- Gemini NEVER bypasses CAPTCHA, 403, or access restrictions.
- Gemini NEVER writes directly to the production observation table.
- Gemini returns a structured classification only (PLAUSIBLE, SUSPICIOUS, etc.)
- The application code makes the final decision based on Gemini output.
- All Gemini responses are validated with Pydantic before use.
- Gemini responses are stored for audit — not just the final decision.

Uses gemini-2.0-flash (free API) with structured JSON output.

Spec Phase 9 §7, §8, §9.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import google.generativeai as genai
from pydantic import ValidationError

from monitoring.models import (
    AIVerificationAssessment,
    AIVerificationResult,
    RefetchOutcome,
    RefetchResult,
)
from models.observation import FareObservation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini model configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "gemini-2.0-flash"
AI_VERIFIER_VERSION = "1.0.0"

# JSON schema for Gemini structured output
_VERIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "assessment": {
            "type": "string",
            "enum": [
                "PLAUSIBLE",
                "SUPPORTED_BY_SOURCE",
                "SUSPICIOUS",
                "UNRESOLVED",
                "INSUFFICIENT_EVIDENCE",
            ],
        },
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
        "evidence_references": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["assessment", "confidence", "reason", "evidence_references"],
}


def _build_verification_prompt(
    observation: FareObservation,
    refetch_result: RefetchResult | None,
    route_context: str | None,
) -> str:
    """Build the structured prompt sent to Gemini."""
    refetch_summary = "No refetch was performed."
    if refetch_result:
        if refetch_result.outcome == RefetchOutcome.CONSISTENT:
            refetch_summary = (
                f"Controlled refetch confirmed the fare. "
                f"Refetched fare: {refetch_result.refetched_total_fare}"
            )
        elif refetch_result.outcome == RefetchOutcome.CHANGED:
            refetch_summary = (
                f"Controlled refetch returned a DIFFERENT fare. "
                f"Original: {refetch_result.original_total_fare}, "
                f"Refetched: {refetch_result.refetched_total_fare}"
            )
        else:
            refetch_summary = (
                f"Refetch was blocked: outcome={refetch_result.outcome.value}. "
                "Source evidence could not be re-verified."
            )

    prompt = f"""You are an aviation fare data quality auditor for the India Airfare Price Index.
A deterministic anomaly detection system has flagged the following observation as a potential outlier.
Your task is to classify whether this fare is PLAUSIBLE based on available evidence.

=== IMPORTANT CONSTRAINTS ===
- You must NOT invent or estimate a fare.
- You must NOT modify the observation.
- You must ONLY classify the fare using the structured output schema.
- You are a verifier/classifier, NOT the decision-maker.
- The application code will make the final accept/quarantine decision.

=== FLAGGED OBSERVATION ===
Source: {observation.source}
Route: {observation.origin} → {observation.destination}
Travel Date: {observation.travel_date}
Lead Days: {observation.lead_days}
Airline: {observation.airline} ({observation.airline_code})
Flight Number: {observation.flight_number}
Cabin: {observation.cabin.value}
Passengers: {observation.passenger_count}
Trip Type: {observation.trip_type.value}
Total Fare: {observation.total_fare} {observation.currency}
Base Fare: {observation.base_fare}
Taxes: {observation.taxes}
Availability: {observation.availability.value}
Collected At: {observation.collected_at}

=== REFETCH RESULT ===
{refetch_summary}

=== ROUTE CONTEXT ===
{route_context or "No historical context available."}

=== YOUR TASK ===
Classify this observation using one of these assessments:
- PLAUSIBLE: The fare is within reasonable bounds for this route/date/airline.
- SUPPORTED_BY_SOURCE: The refetch confirmed the fare from the same source.
- SUSPICIOUS: The fare appears anomalous and inconsistent with available evidence.
- UNRESOLVED: Evidence is contradictory or insufficient to reach a conclusion.
- INSUFFICIENT_EVIDENCE: Not enough information to make a determination.

Return confidence between 0.0 (uncertain) and 1.0 (certain).
Cite specific evidence in evidence_references.
"""
    return prompt


class GeminiAIVerifier:
    """
    Gemini-powered anomaly verifier.

    This verifier is isolated and optional. The application code (not Gemini)
    makes the final accept/quarantine decision. Gemini output is validated
    with Pydantic before use. All results are stored for auditability.

    Spec Phase 9 §7, §8, §9.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
    ):
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "GEMINI_API_KEY must be set (env var or constructor arg) "
                "to use GeminiAIVerifier."
            )
        genai.configure(api_key=resolved_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name

    async def verify(
        self,
        observation: FareObservation,
        refetch_result: RefetchResult | None = None,
        route_context: str | None = None,
    ) -> AIVerificationResult:
        """
        Classify a flagged observation using Gemini structured output.

        Gemini CANNOT:
        - modify the observation
        - return a new fare value
        - access the internet or bypass source restrictions

        Args:
            observation: The flagged FareObservation.
            refetch_result: Optional RefetchResult for additional context.
            route_context: Optional human-readable historical comparison summary.

        Returns:
            AIVerificationResult with structured assessment.
        """
        prompt = _build_verification_prompt(observation, refetch_result, route_context)
        now = datetime.now(timezone.utc)

        logger.info(
            "[ai_verifier] Invoking Gemini (%s) for observation %s "
            "(route=%s->%s date=%s fare=%s)",
            self.model_name,
            observation.observation_id,
            observation.origin,
            observation.destination,
            observation.travel_date,
            observation.total_fare,
        )

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=_VERIFICATION_SCHEMA,
                    temperature=0.0,   # Deterministic output for verification
                    max_output_tokens=512,
                ),
            )
        except Exception as exc:
            logger.error(
                "[ai_verifier] Gemini API error for observation %s: %s",
                observation.observation_id,
                exc,
            )
            return AIVerificationResult(
                observation_id=observation.observation_id,
                assessment=AIVerificationAssessment.UNRESOLVED,
                confidence=0.0,
                reason=f"Gemini API error: {exc}",
                evidence_references=[],
                model_name=self.model_name,
                verified_at=now,
                original_fare=observation.total_fare,
                refetch_outcome=(
                    refetch_result.outcome
                    if refetch_result
                    else RefetchOutcome.NOT_ATTEMPTED
                ),
                route_summary=route_context,
            )

        # --- Parse and validate Gemini response ---
        try:
            raw_text = response.text
            raw_data = json.loads(raw_text)

            # Validate confidence bounds
            confidence = float(raw_data.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))

            # Map assessment string → enum (safe)
            assessment_str = raw_data.get("assessment", "UNRESOLVED")
            try:
                assessment = AIVerificationAssessment(assessment_str)
            except ValueError:
                logger.warning(
                    "[ai_verifier] Unknown assessment '%s' — defaulting to UNRESOLVED",
                    assessment_str,
                )
                assessment = AIVerificationAssessment.UNRESOLVED

            evidence_references = raw_data.get("evidence_references", [])
            reason = raw_data.get("reason", "No reason provided.")

            result = AIVerificationResult(
                observation_id=observation.observation_id,
                assessment=assessment,
                confidence=confidence,
                reason=reason,
                evidence_references=evidence_references,
                model_name=self.model_name,
                verified_at=now,
                original_fare=observation.total_fare,
                refetch_outcome=(
                    refetch_result.outcome
                    if refetch_result
                    else RefetchOutcome.NOT_ATTEMPTED
                ),
                route_summary=route_context,
            )

            logger.info(
                "[ai_verifier] Assessment for %s: %s (confidence=%.2f)",
                observation.observation_id,
                result.assessment.value,
                result.confidence,
            )

            return result

        except (json.JSONDecodeError, ValidationError, KeyError) as exc:
            logger.error(
                "[ai_verifier] Failed to parse Gemini response for observation %s: %s",
                observation.observation_id,
                exc,
            )
            return AIVerificationResult(
                observation_id=observation.observation_id,
                assessment=AIVerificationAssessment.UNRESOLVED,
                confidence=0.0,
                reason=f"Malformed Gemini response: {exc}",
                evidence_references=[],
                model_name=self.model_name,
                verified_at=now,
                original_fare=observation.total_fare,
                refetch_outcome=(
                    refetch_result.outcome
                    if refetch_result
                    else RefetchOutcome.NOT_ATTEMPTED
                ),
                route_summary=route_context,
            )
