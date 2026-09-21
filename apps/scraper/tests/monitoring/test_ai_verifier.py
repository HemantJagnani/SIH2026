"""
Tests for Phase 9: Gemini AI Verifier.

All tests mock the Gemini API — no live API calls are made.
This ensures the tests are deterministic and do not require credentials.

Covers:
- PLAUSIBLE assessment
- SUPPORTED_BY_SOURCE assessment
- SUSPICIOUS assessment
- UNRESOLVED assessment
- Malformed Gemini response
- Invalid confidence value
- API timeout / error
- Gemini never modifies original fare
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from models.observation import FareObservation, AvailabilityStatus
from models.enums import TripType, CabinClass
from models.version import SCHEMA_VERSION
from monitoring.models import (
    AIVerificationAssessment,
    AIVerificationResult,
    RefetchOutcome,
    RefetchResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)
_RUN_ID = uuid.uuid4()


def _obs(total_fare: Decimal = Decimal("4740.00")) -> FareObservation:
    return FareObservation(
        collection_run_id=_RUN_ID,
        source="cleartrip",
        collected_at=_NOW,
        travel_date=date(2026, 9, 28),
        lead_days=7,
        origin="DEL",
        destination="BOM",
        airline="IndiGo",
        flight_number="6E-5001",
        trip_type=TripType.ONE_WAY,
        cabin=CabinClass.ECONOMY,
        passenger_count=1,
        availability=AvailabilityStatus.AVAILABLE,
        total_fare=total_fare,
        currency="INR",
        adapter_version="1.0.0",
        normalizer_version="1.0.0",
        schema_version=SCHEMA_VERSION,
    )


def _make_mock_gemini_response(
    assessment: str,
    confidence: float,
    reason: str = "Test reason",
    evidence_references: list[str] | None = None,
) -> MagicMock:
    """Create a mock Gemini response object."""
    response = MagicMock()
    response.text = json.dumps({
        "assessment": assessment,
        "confidence": confidence,
        "reason": reason,
        "evidence_references": evidence_references or [],
    })
    return response


def _create_verifier_with_mock(mock_response: MagicMock):
    """
    Create a GeminiAIVerifier with a mocked Gemini model.
    Does NOT require a live API key or network access.
    """
    # Patch google.generativeai at the module level before import
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-fake-key"}):
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel") as MockModel:
                mock_model_instance = MagicMock()
                mock_model_instance.generate_content.return_value = mock_response
                MockModel.return_value = mock_model_instance

                from monitoring.ai_verifier import GeminiAIVerifier
                verifier = GeminiAIVerifier(api_key="test-fake-key")
                # Inject the mock model directly
                verifier.model = mock_model_instance
                return verifier


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_verifier_plausible():
    """PLAUSIBLE assessment should be correctly parsed."""
    mock_resp = _make_mock_gemini_response(
        "PLAUSIBLE", 0.92,
        reason="Fare is consistent with historical observations on this route.",
        evidence_references=["historical_median=4500"],
    )
    verifier = _create_verifier_with_mock(mock_resp)
    obs = _obs()

    result = await verifier.verify(obs)

    assert result.assessment == AIVerificationAssessment.PLAUSIBLE
    assert result.confidence == 0.92
    # Original fare must NOT be modified
    assert obs.total_fare == Decimal("4740.00")


@pytest.mark.asyncio
async def test_ai_verifier_suspicious():
    """SUSPICIOUS assessment should be correctly parsed."""
    mock_resp = _make_mock_gemini_response(
        "SUSPICIOUS", 0.85,
        reason="Fare is 4× the group median with no supporting evidence.",
    )
    verifier = _create_verifier_with_mock(mock_resp)
    obs = _obs(total_fare=Decimal("19000"))

    result = await verifier.verify(obs)

    assert result.assessment == AIVerificationAssessment.SUSPICIOUS
    assert result.confidence == 0.85
    # Original fare must remain unchanged
    assert obs.total_fare == Decimal("19000")


@pytest.mark.asyncio
async def test_ai_verifier_unresolved():
    """UNRESOLVED assessment should be correctly handled."""
    mock_resp = _make_mock_gemini_response(
        "UNRESOLVED", 0.4,
        reason="Conflicting signals — refetch returned different fare.",
    )
    verifier = _create_verifier_with_mock(mock_resp)
    obs = _obs()

    result = await verifier.verify(obs)

    assert result.assessment == AIVerificationAssessment.UNRESOLVED


@pytest.mark.asyncio
async def test_ai_verifier_supported_by_source():
    """SUPPORTED_BY_SOURCE should be parsed when refetch confirmed the fare."""
    mock_resp = _make_mock_gemini_response(
        "SUPPORTED_BY_SOURCE", 0.97,
        reason="Refetch returned identical fare, confirmed by source.",
    )
    refetch = RefetchResult(
        observation_id=uuid.uuid4(),
        original_total_fare=Decimal("4740"),
        refetched_total_fare=Decimal("4740"),
        outcome=RefetchOutcome.CONSISTENT,
    )
    verifier = _create_verifier_with_mock(mock_resp)
    obs = _obs()

    result = await verifier.verify(obs, refetch_result=refetch)

    assert result.assessment == AIVerificationAssessment.SUPPORTED_BY_SOURCE
    assert result.refetch_outcome == RefetchOutcome.CONSISTENT


@pytest.mark.asyncio
async def test_ai_verifier_malformed_response():
    """Malformed Gemini response (invalid JSON) → UNRESOLVED with confidence=0."""
    mock_resp = MagicMock()
    mock_resp.text = "This is not valid JSON {{{{"
    verifier = _create_verifier_with_mock(mock_resp)
    obs = _obs()

    result = await verifier.verify(obs)

    assert result.assessment == AIVerificationAssessment.UNRESOLVED
    assert result.confidence == 0.0
    assert "Malformed" in result.reason


@pytest.mark.asyncio
async def test_ai_verifier_invalid_confidence_clamped():
    """Confidence outside [0,1] must be clamped to valid range."""
    mock_resp = _make_mock_gemini_response(
        "PLAUSIBLE", 2.5,   # Invalid: > 1.0
        reason="Test confidence clamping.",
    )
    verifier = _create_verifier_with_mock(mock_resp)
    obs = _obs()

    result = await verifier.verify(obs)

    # Must be clamped to 1.0
    assert result.confidence <= 1.0
    assert result.confidence >= 0.0


@pytest.mark.asyncio
async def test_ai_verifier_api_error_returns_unresolved():
    """Gemini API error must return UNRESOLVED — never raise or crash."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("Gemini API timeout")

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-fake-key"}):
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel", return_value=mock_model):
                from monitoring.ai_verifier import GeminiAIVerifier
                verifier = GeminiAIVerifier(api_key="test-fake-key")
                verifier.model = mock_model

    obs = _obs()
    result = await verifier.verify(obs)

    assert result.assessment == AIVerificationAssessment.UNRESOLVED
    assert result.confidence == 0.0
    assert "error" in result.reason.lower()


@pytest.mark.asyncio
async def test_ai_verifier_unknown_assessment_defaults_to_unresolved():
    """Unknown assessment string from Gemini → UNRESOLVED."""
    mock_resp = _make_mock_gemini_response(
        "TOTALLY_MADE_UP_VALUE", 0.7,
        reason="Invalid assessment value from model.",
    )
    verifier = _create_verifier_with_mock(mock_resp)
    obs = _obs()

    result = await verifier.verify(obs)

    assert result.assessment == AIVerificationAssessment.UNRESOLVED


@pytest.mark.asyncio
async def test_ai_verifier_original_observation_is_immutable():
    """
    Critical safety test: Gemini verification must NEVER modify the original observation.
    """
    original_fare = Decimal("4740.00")
    obs = _obs(total_fare=original_fare)

    mock_resp = _make_mock_gemini_response(
        "SUSPICIOUS", 0.8,
        reason="Fare seems high based on AI assessment.",
    )
    verifier = _create_verifier_with_mock(mock_resp)
    result = await verifier.verify(obs)

    # The original observation must be completely unchanged
    assert obs.total_fare == original_fare
    # The result should record the original fare for auditability
    assert result.original_fare == original_fare
