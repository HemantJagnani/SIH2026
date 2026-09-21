"""
Tests for AiResolutionResponse Pydantic model.
"""
import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from normalization.ai_fallback.models import AiResolutionResponse


def make_response(**overrides) -> dict:
    base = {
        "field": "airline",
        "raw_value": "6E",
        "candidate_value": "IndiGo",
        "confidence": 0.98,
        "needs_review": False,
        "reason": "Recognized IATA airline designator for IndiGo.",
    }
    base.update(overrides)
    return base


def test_valid_response_parses():
    res = AiResolutionResponse.model_validate(make_response())
    assert res.candidate_value == "IndiGo"
    assert res.confidence == 0.98
    assert res.needs_review is False


def test_confidence_out_of_range():
    with pytest.raises(ValidationError):
        AiResolutionResponse.model_validate(make_response(confidence=1.5))

    with pytest.raises(ValidationError):
        AiResolutionResponse.model_validate(make_response(confidence=-0.1))


def test_low_confidence_must_have_needs_review_true():
    """Spec §18: confidence < 0.8 must have needs_review=True."""
    with pytest.raises(ValidationError):
        AiResolutionResponse.model_validate(make_response(confidence=0.5, needs_review=False))


def test_low_confidence_with_review_passes():
    res = AiResolutionResponse.model_validate(make_response(confidence=0.5, needs_review=True))
    assert res.needs_review is True


def test_empty_candidate_value_fails():
    with pytest.raises(ValidationError):
        AiResolutionResponse.model_validate(make_response(candidate_value=""))


def test_extra_fields_forbidden():
    """Model must reject unexpected fields to prevent prompt injection drift."""
    with pytest.raises(ValidationError):
        AiResolutionResponse.model_validate(make_response(unexpected_key="hack"))


def test_frozen_model():
    res = AiResolutionResponse.model_validate(make_response())
    with pytest.raises(Exception):
        res.candidate_value = "MutateMe"  # type: ignore[misc]
