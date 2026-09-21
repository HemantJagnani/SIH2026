"""
Gemini Flash AI fallback resolver.

Spec §17–18: AI is an exception mechanism, not the primary normalizer.
This resolver is ONLY invoked when deterministic normalization fails.

Guardrails (spec §18):
- Receives ONLY: field_name, raw_value, entity_type. No credentials, no PII.
- Returns structured JSON validated through AiResolutionResponse Pydantic model.
- Has configurable timeout, retry, and cost limits.
- Logs model version and prompt template version.
- Never silently rewrites historical observations.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Literal

from google import genai
from google.genai import types
from pydantic import ValidationError

from normalization.ai_fallback.models import AiResolutionResponse

logger = logging.getLogger(__name__)

# Prompt template version — must be logged with every AI call (spec §18)
PROMPT_TEMPLATE_VERSION = "1.0.0"

_PROMPT_TEMPLATE = """\
You are a data normalization assistant for the India Airfare Price Index pipeline.

Your ONLY job is to identify the canonical value for a single field that a \
deterministic rule-based normalizer could not recognize.

Entity type: {entity_type}
Field name: {field_name}
Raw value: "{raw_value}"

Known entity types and their expected canonical forms:
- AIRLINE: Use the official airline brand name (e.g. "IndiGo", "Air India", "SpiceJet", "Akasa Air", "Air India Express")
- AIRPORT: Use the 3-letter IATA code (e.g. "DEL", "BOM", "BLR", "HYD", "MAA", "CCU", "AMD", "GOI", "COK", "PNQ", "JAI")

Respond with ONLY a valid JSON object. No prose, no markdown, no code fences. \
Exactly this schema:

{{
  "field": "<field_name>",
  "raw_value": "<raw_value>",
  "candidate_value": "<your best canonical value>",
  "confidence": <float between 0.0 and 1.0>,
  "needs_review": <true if confidence < 0.8 or you are uncertain, else false>,
  "reason": "<one sentence explaining why>"
}}

If you cannot make a reasonable determination, set confidence to 0.0 and \
needs_review to true with reason explaining why.
"""

EntityType = Literal["AIRLINE", "AIRPORT"]


class GeminiAiFallbackResolver:
    """
    Calls Gemini Flash to resolve an unknown entity value.

    Spec §18 guardrails enforced:
    - Only minimal context sent (field_name, raw_value, entity_type)
    - No credentials or PII in prompt
    - Structured JSON response only
    - Response validated through AiResolutionResponse Pydantic model
    - Timeout, retry, and model version are logged
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 15.0,
        max_retries: int = 2,
    ):
        _api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not _api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Set it in your .env file."
            )

        self._model_name = model or os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        # Use the async client via `client.aio` so asyncio.wait_for can
        # actually cancel the in-flight coroutine on timeout
        self._client = genai.Client(api_key=_api_key)

        logger.info(
            "GeminiAiFallbackResolver initialized: model=%s, timeout=%.1fs, max_retries=%d",
            self._model_name,
            self._timeout,
            self._max_retries,
        )

    async def resolve(
        self,
        field_name: str,
        raw_value: str,
        entity_type: EntityType,
    ) -> AiResolutionResponse | None:
        """
        Ask the AI to resolve one unknown entity value.

        Returns:
            AiResolutionResponse if the AI returned a valid structured response.
            None if the AI could not be reached or returned an invalid response.

        Spec §18: Never silently succeed with bad data — always validate the AI output.
        """
        prompt = _PROMPT_TEMPLATE.format(
            entity_type=entity_type,
            field_name=field_name,
            raw_value=raw_value,
        )

        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(
                    "AI fallback attempt %d/%d: model=%s, template_version=%s, "
                    "field=%s, entity_type=%s, raw_value=%r",
                    attempt,
                    self._max_retries,
                    self._model_name,
                    PROMPT_TEMPLATE_VERSION,
                    field_name,
                    entity_type,
                    raw_value,
                )

                response = await asyncio.wait_for(
                    self._call_gemini(prompt),
                    timeout=self._timeout,
                )

                # Parse and validate through Pydantic (spec §18: AI output must pass validation)
                parsed = self._parse_response(response, field_name, raw_value)
                if parsed is not None:
                    return parsed

            except asyncio.TimeoutError:
                logger.warning(
                    "AI fallback timeout on attempt %d/%d (%.1fs): field=%s, raw_value=%r",
                    attempt, self._max_retries, self._timeout, field_name, raw_value,
                )
                last_error = TimeoutError(f"Gemini timeout after {self._timeout}s")

            except Exception as e:
                logger.warning(
                    "AI fallback error on attempt %d/%d: %s: field=%s, raw_value=%r",
                    attempt, self._max_retries, e, field_name, raw_value,
                )
                last_error = e

            if attempt < self._max_retries:
                await asyncio.sleep(1.5 * attempt)  # simple backoff

        logger.error(
            "AI fallback exhausted %d retries for field=%s, raw_value=%r. Last error: %s",
            self._max_retries, field_name, raw_value, last_error,
        )
        return None

    async def _call_gemini(self, prompt: str) -> str:
        """Make the actual Gemini API call using the async client."""
        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,  # Deterministic output for data normalization
                max_output_tokens=256,
            ),
        )
        return response.text

    def _parse_response(
        self,
        raw_text: str,
        field_name: str,
        raw_value: str,
    ) -> AiResolutionResponse | None:
        """
        Parse and Pydantic-validate the AI JSON response.
        Returns None if parsing or validation fails.
        """
        try:
            data = json.loads(raw_text.strip())
        except json.JSONDecodeError as e:
            logger.error(
                "AI returned invalid JSON for field=%s, raw_value=%r: %s | response=%r",
                field_name, raw_value, e, raw_text[:200],
            )
            return None

        try:
            resolution = AiResolutionResponse.model_validate(data)
            logger.info(
                "AI resolution: field=%s, raw_value=%r -> candidate=%r, "
                "confidence=%.2f, needs_review=%s",
                field_name,
                raw_value,
                resolution.candidate_value,
                resolution.confidence,
                resolution.needs_review,
            )
            return resolution

        except ValidationError as e:
            logger.error(
                "AI response failed Pydantic validation for field=%s, raw_value=%r: %s",
                field_name, raw_value, e,
            )
            return None
