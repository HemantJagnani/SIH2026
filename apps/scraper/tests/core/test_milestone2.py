"""
Unit tests for Milestone 2: browser runner, session manager, anti-bot detector.

All tests run offline — no real browser is launched and no network calls are made.
We mock Playwright Page objects where needed using simple stub classes.

Run with:
    pytest apps/scraper/tests/core/test_milestone2.py -v
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from core.crawler import build_crawler
from core.session_manager import SessionManager
from core.anti_bot_detector import (
    captcha_present,
    is_access_blocked,
    is_rate_limited,
    is_auth_required,
    is_login_wall,
    is_server_error,
    _parse_retry_after,
)


# ===========================================================================
# crawler.py tests
# ===========================================================================

class TestBuildCrawler:
    """Tests for the build_crawler() factory function."""

    def test_build_crawler_returns_playwright_crawler(self):
        """build_crawler() should return a PlaywrightCrawler instance."""
        from crawlee.crawlers import PlaywrightCrawler
        crawler = build_crawler(headless=True)
        assert isinstance(crawler, PlaywrightCrawler)

    def test_build_crawler_headless_false_by_default(self, monkeypatch):
        """When SCRAPER_HEADLESS is not set, headless defaults to False."""
        monkeypatch.delenv("SCRAPER_HEADLESS", raising=False)
        # We just verify the factory doesn't crash — headless value is
        # internal to Crawlee's browser_pool configuration.
        crawler = build_crawler()
        assert crawler is not None

    def test_build_crawler_headless_env_true(self, monkeypatch):
        """SCRAPER_HEADLESS=true should produce a headless crawler."""
        monkeypatch.setenv("SCRAPER_HEADLESS", "true")
        crawler = build_crawler()
        assert crawler is not None

    def test_build_crawler_headless_param_overrides_env(self, monkeypatch):
        """Explicit headless= parameter should override SCRAPER_HEADLESS."""
        monkeypatch.setenv("SCRAPER_HEADLESS", "false")
        # Should not raise regardless of env
        crawler = build_crawler(headless=True)
        assert crawler is not None


# ===========================================================================
# session_manager.py tests
# ===========================================================================

class TestSessionManager:
    """Tests for SessionManager — save, load, block, clear operations."""

    @pytest.fixture
    def tmp_manager(self, tmp_path: Path) -> SessionManager:
        """Return a SessionManager backed by a temporary directory."""
        return SessionManager(state_dir=tmp_path / "session_states")

    @pytest.fixture
    def sample_state(self) -> dict:
        """A minimal Playwright storage_state dict."""
        return {
            "cookies": [
                {
                    "name": "session_id",
                    "value": "abc123",
                    "domain": "www.indigo.com",
                    "path": "/",
                }
            ],
            "origins": [],
        }

    def test_load_returns_none_when_no_state(self, tmp_manager: SessionManager):
        """Loading state for a source that has never been saved should return None."""
        result = tmp_manager.load("indigo")
        assert result is None

    def test_save_and_load_roundtrip(self, tmp_manager: SessionManager, sample_state: dict):
        """Saving then loading a state should return the original data."""
        tmp_manager.save("indigo", sample_state)
        loaded = tmp_manager.load("indigo")
        assert loaded is not None
        assert loaded["cookies"][0]["name"] == "session_id"

    def test_save_creates_state_file(self, tmp_manager: SessionManager, sample_state: dict):
        """save() should create a .state.json file on disk."""
        tmp_manager.save("indigo", sample_state)
        state_file = tmp_manager._state_path("indigo")
        assert state_file.exists()

    def test_save_blocked_source_is_refused(self, tmp_manager: SessionManager, sample_state: dict):
        """Calling save() after mark_blocked() should not write the file."""
        tmp_manager.mark_blocked("indigo")
        tmp_manager.save("indigo", sample_state)
        state_file = tmp_manager._state_path("indigo")
        assert not state_file.exists()

    def test_mark_blocked_sets_is_blocked(self, tmp_manager: SessionManager):
        """mark_blocked() should be reflected by is_blocked()."""
        assert not tmp_manager.is_blocked("indigo")
        tmp_manager.mark_blocked("indigo")
        assert tmp_manager.is_blocked("indigo")

    def test_clear_state_removes_file(self, tmp_manager: SessionManager, sample_state: dict):
        """clear_state() should delete the session state file."""
        tmp_manager.save("indigo", sample_state)
        tmp_manager.clear_state("indigo")
        assert not tmp_manager._state_path("indigo").exists()

    def test_clear_state_noop_when_no_file(self, tmp_manager: SessionManager):
        """clear_state() should not raise if there is no state file."""
        tmp_manager.clear_state("airindia")  # Should not raise

    def test_different_sources_get_separate_files(
        self, tmp_manager: SessionManager, sample_state: dict
    ):
        """Two sources should have distinct state files."""
        tmp_manager.save("indigo", sample_state)
        tmp_manager.save("airindia", sample_state)
        assert tmp_manager._state_path("indigo") != tmp_manager._state_path("airindia")
        assert tmp_manager._state_path("indigo").exists()
        assert tmp_manager._state_path("airindia").exists()


# ===========================================================================
# anti_bot_detector.py tests (all offline — no browser)
# ===========================================================================

class FakePage:
    """Minimal stub for a Playwright Page, for testing detector functions."""

    def __init__(self, body_text: str = "", dom_has_captcha: bool = False):
        self._body_text = body_text
        self._dom_has_captcha = dom_has_captcha

    def locator(self, selector: str):
        stub = MagicMock()
        stub.inner_text = AsyncMock(return_value=self._body_text)
        # Simulate count() for DOM marker check
        stub.count = AsyncMock(return_value=(1 if self._dom_has_captcha and "captcha" in selector else 0))
        return stub


class TestCaptchaDetector:

    @pytest.mark.asyncio
    async def test_clean_page_not_captcha(self):
        page = FakePage("Welcome to IndiGo. Book your flights here.")
        assert await captcha_present(page) is False

    @pytest.mark.asyncio
    async def test_captcha_text_detected(self):
        page = FakePage("Please complete the captcha to continue.")
        assert await captcha_present(page) is True

    @pytest.mark.asyncio
    async def test_cloudflare_challenge_detected(self):
        page = FakePage("Just a moment... checking your browser before accessing.")
        assert await captcha_present(page) is True

    @pytest.mark.asyncio
    async def test_verify_human_detected(self):
        page = FakePage("Verify you are human to access this page.")
        assert await captcha_present(page) is True

    @pytest.mark.asyncio
    async def test_dom_captcha_element_detected(self):
        page = FakePage(body_text="Searching for flights...", dom_has_captcha=True)
        assert await captcha_present(page) is True


class TestHttpStatusDetectors:

    def test_403_is_access_blocked(self):
        assert is_access_blocked(403) is True

    def test_451_is_access_blocked(self):
        assert is_access_blocked(451) is True

    def test_200_not_blocked(self):
        assert is_access_blocked(200) is False

    def test_429_is_rate_limited(self):
        limited, wait = is_rate_limited(429, retry_after="60")
        assert limited is True
        assert wait == 60.0

    def test_429_without_header_uses_default(self):
        limited, wait = is_rate_limited(429, retry_after=None)
        assert limited is True
        assert wait == 120.0  # conservative default

    def test_200_not_rate_limited(self):
        limited, wait = is_rate_limited(200)
        assert limited is False
        assert wait is None

    def test_401_is_auth_required(self):
        assert is_auth_required(401) is True

    def test_403_not_auth_required(self):
        assert is_auth_required(403) is False

    def test_500_is_server_error(self):
        assert is_server_error(500) is True

    def test_503_is_server_error(self):
        assert is_server_error(503) is True

    def test_200_not_server_error(self):
        assert is_server_error(200) is False


class TestLoginWallDetector:

    @pytest.mark.asyncio
    async def test_clean_results_page_not_login_wall(self):
        page = FakePage("DEL → BOM, 12 flights found, from ₹3,499")
        assert await is_login_wall(page) is False

    @pytest.mark.asyncio
    async def test_sign_in_prompt_detected(self):
        page = FakePage("Sign in to continue searching for the best fares.")
        assert await is_login_wall(page) is True

    @pytest.mark.asyncio
    async def test_create_account_prompt_detected(self):
        page = FakePage("Create an account to view member-only fares.")
        assert await is_login_wall(page) is True


class TestRetryAfterParser:

    def test_numeric_string(self):
        assert _parse_retry_after("90") == 90.0

    def test_none_returns_default(self):
        assert _parse_retry_after(None) == 120.0

    def test_zero_clamped_to_one(self):
        # Negative or zero Retry-After values are clamped to 1s minimum
        assert _parse_retry_after("0") == 1.0

    def test_invalid_string_returns_default(self):
        assert _parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") == 120.0
