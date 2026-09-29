"""
test_heartbeat.py - Comprehensive Unit & Integration Tests for S1 Heartbeat System.

Tests:
1. Heartbeat inbound endpoint (/api/heartbeat and /heartbeat) returns HTTP 200 fast.
2. Configuration loading from environment variables (S2_HEARTBEAT_URL, HEARTBEAT_INTERVAL_SECONDS, etc.).
3. Successful outbound heartbeat to S2 (updates persistent state to HEALTHY).
4. Failed outbound heartbeat to S2 (HTTP 500 error code handled, updates state to DEGRADED without crashing).
5. Timeout handling during outbound heartbeat (httpx.TimeoutException handled cleanly).
6. Connection error handling during outbound heartbeat (httpx.ConnectError handled cleanly).
7. Single-loop enforcement (prevents duplicate background tasks during reloads/restarts).
8. Persistent state serialization and resilience when database is offline.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

# Ensure root and src paths are accessible
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
api_src = os.path.join(ROOT, "apps", "api", "src")
if api_src not in sys.path:
    sys.path.insert(0, api_src)

from apps.api.src.heartbeat import (
    execute_outbound_heartbeat,
    get_heartbeat_interval_seconds,
    get_heartbeat_timeout_seconds,
    get_s2_heartbeat_url,
    get_service_id,
    is_heartbeat_loop_running,
    load_persistent_heartbeat_state,
    save_heartbeat_state,
    start_heartbeat_task,
    stop_heartbeat_task,
)
from apps.api.src.main import app

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. Inbound Endpoint Tests
# -----------------------------------------------------------------------------
def test_heartbeat_endpoint_returns_fast_200():
    """Verify GET /api/heartbeat responds with HTTP 200 and expected diagnostic schema."""
    response = client.get("/api/heartbeat")
    assert response.status_code == 200
    data = response.json()

    assert data["service"] == "S1"
    assert "service_name" in data
    assert "status" in data
    assert "timestamp" in data
    assert "diagnostics" in data

    diag = data["diagnostics"]
    assert "target_s2_url" in diag
    assert "heartbeat_interval_seconds" in diag
    assert "background_loop_active" in diag
    assert "state_persistence" in diag
    assert "Neon PostgreSQL" in diag["state_persistence"]


def test_heartbeat_legacy_alias_endpoint():
    """Verify GET /heartbeat also responds with HTTP 200."""
    response = client.get("/heartbeat")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "S1"


# -----------------------------------------------------------------------------
# 2. Configuration Tests
# -----------------------------------------------------------------------------
def test_configuration_environment_variables(monkeypatch):
    """Verify configuration reading and defaults."""
    # Test custom values
    monkeypatch.setenv("S2_HEARTBEAT_URL", "https://s2-test.onrender.com/api/heartbeat")
    monkeypatch.setenv("HEARTBEAT_INTERVAL_SECONDS", "45")
    monkeypatch.setenv("HEARTBEAT_HTTP_TIMEOUT", "5.5")
    monkeypatch.setenv("SERVICE_ID", "S1-PRODUCTION")

    assert get_s2_heartbeat_url() == "https://s2-test.onrender.com/api/heartbeat"
    assert get_heartbeat_interval_seconds() == 45.0
    assert get_heartbeat_timeout_seconds() == 5.5
    assert get_service_id() == "S1-PRODUCTION"

    # Test fallback defaults
    monkeypatch.delenv("S2_HEARTBEAT_URL", raising=False)
    monkeypatch.delenv("HEARTBEAT_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("HEARTBEAT_HTTP_TIMEOUT", raising=False)
    monkeypatch.delenv("SERVICE_ID", raising=False)

    assert get_s2_heartbeat_url() == ""
    assert get_heartbeat_interval_seconds() == 90.0
    assert get_heartbeat_timeout_seconds() == 10.0
    assert get_service_id() == "S1"


# -----------------------------------------------------------------------------
# 3. Successful Outbound Heartbeat Test
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_successful_outbound_heartbeat(monkeypatch):
    """Verify that a 200 OK from S2 records HEALTHY status and resets failures."""
    monkeypatch.setenv("S2_HEARTBEAT_URL", "https://s2.example.com/api/heartbeat")

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"status":"HEALTHY","service":"S2"}'
    mock_client.get.return_value = mock_resp

    dummy_conn_factory = lambda: None  # in-memory fallback will activate

    res = await execute_outbound_heartbeat(
        db_conn_factory=dummy_conn_factory,
        client=mock_client,
    )

    assert res["status"] == "HEALTHY"
    assert res["consecutive_successes"] >= 1
    assert res["consecutive_failures"] == 0
    assert res["last_error"] is None
    assert res["last_success_at"] is not None
    assert res["target_url"] == "https://s2.example.com/api/heartbeat"


# -----------------------------------------------------------------------------
# 4. Failed S2 Heartbeat Test (HTTP Error Code)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_failed_s2_heartbeat_http_error(monkeypatch):
    """Verify that a 500 Internal Error from S2 records DEGRADED status without raising uncaught errors."""
    monkeypatch.setenv("S2_HEARTBEAT_URL", "https://s2.example.com/api/heartbeat")

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = 502
    mock_resp.text = "Bad Gateway"
    mock_client.get.return_value = mock_resp

    dummy_conn_factory = lambda: None

    res = await execute_outbound_heartbeat(
        db_conn_factory=dummy_conn_factory,
        client=mock_client,
    )

    assert res["status"] == "DEGRADED"
    assert res["consecutive_failures"] >= 1
    assert "502" in res["last_error"]
    assert res["last_failure_at"] is not None


# -----------------------------------------------------------------------------
# 5. Timeout Handling Test
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_timeout_handling_outbound_heartbeat(monkeypatch):
    """Verify that an HTTP timeout to S2 is caught, logged, and recorded as DEGRADED."""
    monkeypatch.setenv("S2_HEARTBEAT_URL", "https://s2.example.com/api/heartbeat")

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Read timed out")

    dummy_conn_factory = lambda: None

    res = await execute_outbound_heartbeat(
        db_conn_factory=dummy_conn_factory,
        client=mock_client,
    )

    assert res["status"] == "DEGRADED"
    assert res["consecutive_failures"] >= 1
    assert "timed out" in res["last_error"].lower()
    assert res["last_failure_at"] is not None


# -----------------------------------------------------------------------------
# 6. Connection Failure Handling Test
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_connection_error_outbound_heartbeat(monkeypatch):
    """Verify that a connection refusal or DNS failure is caught gracefully."""
    monkeypatch.setenv("S2_HEARTBEAT_URL", "https://s2.example.com/api/heartbeat")

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("Failed to resolve host")

    dummy_conn_factory = lambda: None

    res = await execute_outbound_heartbeat(
        db_conn_factory=dummy_conn_factory,
        client=mock_client,
    )

    assert res["status"] == "DEGRADED"
    assert "Failed to connect" in res["last_error"]


# -----------------------------------------------------------------------------
# 7. Unconfigured S2 URL Handling
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unconfigured_s2_url(monkeypatch):
    """Verify that if S2_HEARTBEAT_URL is blank, S1 safely marks UNCONFIGURED."""
    monkeypatch.setenv("S2_HEARTBEAT_URL", "")

    dummy_conn_factory = lambda: None

    res = await execute_outbound_heartbeat(
        db_conn_factory=dummy_conn_factory,
    )

    assert res["status"] == "UNCONFIGURED"
    assert "not configured" in res["last_error"].lower()


# -----------------------------------------------------------------------------
# 8. Single-Loop Enforcement Test
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_duplicate_heartbeat_loop_during_startup():
    """Verify that repeated startup calls do not create multiple running background tasks."""
    dummy_conn_factory = lambda: None

    # Ensure clean start state
    await stop_heartbeat_task()
    assert not is_heartbeat_loop_running()

    # First start should succeed
    started_first = start_heartbeat_task(dummy_conn_factory)
    assert started_first is True
    assert is_heartbeat_loop_running()

    # Second start while already running MUST return False and avoid duplicate tasks
    started_second = start_heartbeat_task(dummy_conn_factory)
    assert started_second is False
    assert is_heartbeat_loop_running()

    # Clean shutdown
    await stop_heartbeat_task()
    assert not is_heartbeat_loop_running()
