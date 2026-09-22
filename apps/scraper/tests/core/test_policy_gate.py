"""
Unit tests for RobotsPolicyGate (Milestone 1).

All tests use the local fixture file at tests/fixtures/robots_test.txt.
No real HTTP requests are made in this test module — this is a hard
requirement for Milestone 1 (no network calls yet).

Run with:
    pytest apps/scraper/tests/core/test_policy_gate.py -v
"""

import pytest
from pathlib import Path

from apps.scraper.src.core.policy_gate import RobotsPolicyGate

# Path to the local robots.txt fixture used for all tests here.
FIXTURE = Path(__file__).parent.parent / "fixtures" / "robots_test.txt"


@pytest.fixture
def gate() -> RobotsPolicyGate:
    """Construct a policy gate backed by the local fixture (no network)."""
    return RobotsPolicyGate(fixture_path=FIXTURE)


# ---------------------------------------------------------------------------
# Allowed paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_root_is_allowed(gate: RobotsPolicyGate) -> None:
    """The root path should be accessible to our bot."""
    allowed, reason = await gate.check("https://example.com/")
    assert allowed is True
    assert reason == "allowed"


@pytest.mark.asyncio
async def test_public_search_page_is_allowed(gate: RobotsPolicyGate) -> None:
    """The normal public flight search path should be accessible."""
    allowed, reason = await gate.check("https://example.com/flights/search")
    assert allowed is True


@pytest.mark.asyncio
async def test_about_page_is_allowed(gate: RobotsPolicyGate) -> None:
    """Static public pages should be accessible."""
    allowed, reason = await gate.check("https://example.com/about")
    assert allowed is True


# ---------------------------------------------------------------------------
# Disallowed paths — these must return False with a descriptive reason
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_path_is_disallowed(gate: RobotsPolicyGate) -> None:
    """Admin paths are disallowed; gate must return False."""
    allowed, reason = await gate.check("https://example.com/admin/dashboard")
    assert allowed is False
    assert "disallow" in reason.lower() or "DISALLOWED" in reason.upper()


@pytest.mark.asyncio
async def test_internal_path_is_disallowed(gate: RobotsPolicyGate) -> None:
    """Internal paths are disallowed."""
    allowed, reason = await gate.check("https://example.com/internal/stats")
    assert allowed is False


@pytest.mark.asyncio
async def test_automated_booking_path_is_disallowed(gate: RobotsPolicyGate) -> None:
    """Automated booking paths are disallowed — our bot must respect this."""
    allowed, reason = await gate.check("https://example.com/booking/automated/reserve")
    assert allowed is False


@pytest.mark.asyncio
async def test_automated_api_path_is_disallowed(gate: RobotsPolicyGate) -> None:
    """Automated API paths are disallowed."""
    allowed, reason = await gate.check("https://example.com/api/v1/automated/fares")
    assert allowed is False


# ---------------------------------------------------------------------------
# Caching behaviour: same domain should not re-read the fixture twice
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_returns_same_parser(gate: RobotsPolicyGate) -> None:
    """Two checks on the same domain should use the cached parser."""
    await gate.check("https://example.com/")
    await gate.check("https://example.com/about")
    # The internal cache should have exactly one entry for the domain.
    assert len(gate._cache) == 1


@pytest.mark.asyncio
async def test_separate_domains_get_separate_cache_entries(gate: RobotsPolicyGate) -> None:
    """Different domains should each get their own cache entry."""
    await gate.check("https://example.com/")
    await gate.check("https://other.example.org/")
    assert len(gate._cache) == 2
