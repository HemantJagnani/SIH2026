"""
Tests for GeminiAiFallbackResolver — all using mocks (no live API calls).
"""
import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from normalization.ai_fallback.models import AiResolutionResponse
from normalization.ai_fallback.resolver import GeminiAiFallbackResolver


def make_resolver() -> GeminiAiFallbackResolver:
    """Create resolver with a fake API key (no real network call)."""
    with patch("normalization.ai_fallback.resolver.genai.Client"):
        return GeminiAiFallbackResolver(
            api_key="fake-api-key",
            model="gemini-2.0-flash",
            timeout_seconds=5.0,
            max_retries=2,
        )


def make_valid_ai_json(**overrides) -> str:
    base = {
        "field": "airline",
        "raw_value": "6E",
        "candidate_value": "IndiGo",
        "confidence": 0.98,
        "needs_review": False,
        "reason": "IATA designator for IndiGo.",
    }
    base.update(overrides)
    return json.dumps(base)


@pytest.mark.asyncio
async def test_resolve_returns_valid_response():
    resolver = make_resolver()

    with patch.object(resolver, "_call_gemini", new=AsyncMock(return_value=make_valid_ai_json())):
        result = await resolver.resolve("airline", "6E", "AIRLINE")

    assert result is not None
    assert isinstance(result, AiResolutionResponse)
    assert result.candidate_value == "IndiGo"
    assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_resolve_returns_none_on_invalid_json():
    resolver = make_resolver()

    with patch.object(resolver, "_call_gemini", new=AsyncMock(return_value="not json at all")):
        result = await resolver.resolve("airline", "XYZZY", "AIRLINE")

    assert result is None


@pytest.mark.asyncio
async def test_resolve_returns_none_on_invalid_schema():
    """AI returns JSON but wrong shape — must fail Pydantic validation."""
    bad_json = json.dumps({"something": "unexpected"})
    resolver = make_resolver()

    with patch.object(resolver, "_call_gemini", new=AsyncMock(return_value=bad_json)):
        result = await resolver.resolve("airline", "XYZ", "AIRLINE")

    assert result is None


@pytest.mark.asyncio
async def test_resolve_retries_on_timeout():
    """Resolver should retry up to max_retries times on timeout."""
    resolver = make_resolver()
    call_count = 0

    async def timeout_then_success(prompt):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise asyncio.TimeoutError()
        return make_valid_ai_json()

    with patch.object(resolver, "_call_gemini", new=timeout_then_success):
        result = await resolver.resolve("airline", "6E", "AIRLINE")

    assert result is not None
    assert call_count == 2  # Failed once, then succeeded


@pytest.mark.asyncio
async def test_resolve_returns_none_after_all_retries_timeout():
    """If ALL retries time out, returns None (never raises)."""
    resolver = make_resolver()

    async def always_timeout(prompt):
        raise asyncio.TimeoutError()

    with patch.object(resolver, "_call_gemini", new=always_timeout):
        result = await resolver.resolve("airline", "BadValue", "AIRLINE")

    assert result is None


@pytest.mark.asyncio
async def test_prompt_contains_only_safe_context():
    """
    Spec §18 guardrail: prompt must contain ONLY field_name, raw_value, entity_type.
    Credentials or PII must not appear in the prompt.
    """
    resolver = make_resolver()
    captured_prompts = []

    async def capture_prompt(prompt):
        captured_prompts.append(prompt)
        return make_valid_ai_json()

    with patch.object(resolver, "_call_gemini", new=capture_prompt):
        await resolver.resolve("airline", "IndigoAirlines", "AIRLINE")

    assert len(captured_prompts) == 1
    prompt = captured_prompts[0]

    # Must contain the safe context
    assert "IndigoAirlines" in prompt
    assert "AIRLINE" in prompt
    assert "airline" in prompt.lower()

    # Must NOT contain sensitive patterns (passwords, auth tokens, etc.)
    assert "password" not in prompt.lower()
    assert "secret" not in prompt.lower()
    assert "api_key" not in prompt.lower()
    assert "token" not in prompt.lower()
