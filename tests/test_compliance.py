"""
Tests for compliance.py – Phase 2.

Tests:
- A disallowed URL is refused and never fetched
- An allowed URL is logged as allowed
- robots.txt parse failure is treated as refused (conservative)
- Cache behaviour: same host not re-fetched
"""
from __future__ import annotations

import urllib.robotparser
from unittest.mock import MagicMock, patch

import pytest

from apix.compliance import Allowed, ComplianceGate, Refused


@pytest.fixture(autouse=True)
def clear_cache():
    """Ensure the per-host parser cache is empty between tests."""
    ComplianceGate.clear_cache()
    yield
    ComplianceGate.clear_cache()


def _make_gate(user_agent: str = "APIx-Prototype/0.1") -> ComplianceGate:
    return ComplianceGate(user_agent=user_agent)


def _mock_parser(can_fetch_result: bool):
    """Return a mock RobotFileParser that always returns can_fetch_result."""
    parser = MagicMock(spec=urllib.robotparser.RobotFileParser)
    parser.can_fetch.return_value = can_fetch_result
    return parser


class TestComplianceGateAllowed:
    def test_allowed_url_returns_allowed(self):
        gate = _make_gate()
        with patch.object(gate, "_get_parser", return_value=_mock_parser(True)):
            result = gate.check("https://example.com/flights?from=DEL&to=BOM")
        assert isinstance(result, Allowed)

    def test_allowed_url_is_logged(self):
        gate = _make_gate()
        with patch.object(gate, "_get_parser", return_value=_mock_parser(True)):
            gate.check("https://example.com/search")
        log = gate.get_log()
        assert len(log) == 1
        assert log[0]["decision"] == "allowed"

    def test_allowed_url_is_never_refused(self):
        gate = _make_gate()
        with patch.object(gate, "_get_parser", return_value=_mock_parser(True)):
            result = gate.check("https://example.com/search")
        assert not isinstance(result, Refused)


class TestComplianceGateRefused:
    def test_disallowed_url_returns_refused(self):
        gate = _make_gate()
        with patch.object(gate, "_get_parser", return_value=_mock_parser(False)):
            result = gate.check("https://example.com/disallowed/search")
        assert isinstance(result, Refused)
        assert "robots" in result.reason.lower()

    def test_disallowed_url_is_logged(self):
        gate = _make_gate()
        with patch.object(gate, "_get_parser", return_value=_mock_parser(False)):
            gate.check("https://example.com/disallowed/path")
        log = gate.get_log()
        assert log[0]["decision"] == "refused"

    def test_robots_fetch_failure_is_conservative_refusal(self):
        """If robots.txt cannot be fetched, the URL must be refused."""
        gate = _make_gate()

        def raising_parser(url):
            raise ConnectionError("Network unreachable")

        with patch.object(gate, "_get_parser", side_effect=raising_parser):
            result = gate.check("https://unreachable.example.com/flights")
        assert isinstance(result, Refused)
        assert len(gate.get_log()) == 1
        assert gate.get_log()[0]["decision"] == "refused"


class TestComplianceLog:
    def test_multiple_checks_all_logged(self):
        gate = _make_gate()
        with patch.object(gate, "_get_parser", return_value=_mock_parser(True)):
            gate.check("https://example.com/a")
            gate.check("https://example.com/b")
        assert len(gate.get_log()) == 2

    def test_get_log_returns_copy(self):
        """Mutating the returned log should not affect the gate's internal log."""
        gate = _make_gate()
        with patch.object(gate, "_get_parser", return_value=_mock_parser(True)):
            gate.check("https://example.com/a")
        log = gate.get_log()
        log.clear()
        assert len(gate.get_log()) == 1
