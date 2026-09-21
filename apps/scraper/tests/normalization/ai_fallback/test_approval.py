"""
Tests for the approval flow (handle_normalization_exception, approve, reject, quarantine).
All DB interactions are mocked.
"""
import asyncio
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from normalization.ai_fallback.approval import (
    ResolutionStatus,
    handle_normalization_exception,
)
from normalization.ai_fallback.models import AiResolutionResponse
from normalization.core import NormalizationException as NormExc


def make_norm_exception() -> NormExc:
    return NormExc(
        field_name="airline",
        raw_value="XYZ_UNKNOWN",
        message="No deterministic mapping found for AIRLINE",
    )


def make_ai_response(**overrides) -> AiResolutionResponse:
    defaults = {
        "field": "airline",
        "raw_value": "XYZ_UNKNOWN",
        "candidate_value": "IndiGo",
        "confidence": 0.98,
        "needs_review": False,
        "reason": "Recognized from context.",
    }
    defaults.update(overrides)
    return AiResolutionResponse.model_validate(defaults)


def make_mock_db() -> MagicMock:
    """Mock DatabaseClient with async session context manager."""
    db = MagicMock()
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    db.session = MagicMock(return_value=mock_session)
    return db


@pytest.mark.asyncio
async def test_quarantined_when_ai_returns_none():
    """Spec §17: If AI cannot resolve, set status = QUARANTINED."""
    db = make_mock_db()
    exc = make_norm_exception()

    status = await handle_normalization_exception(
        exc=exc,
        source="indigo",
        ai_response=None,
        db_client=db,
    )

    assert status == ResolutionStatus.QUARANTINED


@pytest.mark.asyncio
async def test_auto_approved_when_confidence_above_threshold():
    """High-confidence response above threshold → AUTO-APPROVED and promoted."""
    db = make_mock_db()
    exc = make_norm_exception()
    ai_resp = make_ai_response(confidence=0.98, needs_review=False)

    with patch(
        "normalization.ai_fallback.approval._promote_to_mapping",
        new=AsyncMock(),
    ) as mock_promote:
        status = await handle_normalization_exception(
            exc=exc,
            source="indigo",
            ai_response=ai_resp,
            db_client=db,
            auto_approve_threshold=0.95,
        )

    assert status == ResolutionStatus.APPROVED
    mock_promote.assert_awaited_once()


@pytest.mark.asyncio
async def test_manual_review_when_confidence_below_threshold():
    """Confidence below threshold → MANUAL_REVIEW, no promotion."""
    db = make_mock_db()
    exc = make_norm_exception()
    ai_resp = make_ai_response(confidence=0.75, needs_review=True)

    with patch(
        "normalization.ai_fallback.approval._promote_to_mapping",
        new=AsyncMock(),
    ) as mock_promote:
        status = await handle_normalization_exception(
            exc=exc,
            source="indigo",
            ai_response=ai_resp,
            db_client=db,
            auto_approve_threshold=0.95,
        )

    assert status == ResolutionStatus.MANUAL_REVIEW
    mock_promote.assert_not_awaited()


@pytest.mark.asyncio
async def test_manual_review_when_needs_review_true_even_if_high_confidence():
    """If needs_review=True, never auto-approve even if confidence is high."""
    db = make_mock_db()
    exc = make_norm_exception()
    # The model enforces: confidence=0.98 with needs_review=True is allowed
    ai_resp = make_ai_response(confidence=0.98, needs_review=True)

    with patch(
        "normalization.ai_fallback.approval._promote_to_mapping",
        new=AsyncMock(),
    ) as mock_promote:
        status = await handle_normalization_exception(
            exc=exc,
            source="indigo",
            ai_response=ai_resp,
            db_client=db,
            auto_approve_threshold=0.95,
        )

    assert status == ResolutionStatus.MANUAL_REVIEW
    mock_promote.assert_not_awaited()
