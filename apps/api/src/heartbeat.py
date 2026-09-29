"""
heartbeat.py - S1 Heartbeat Orchestration & Persistent State Management.

Part of the persistent two-service heartbeat architecture (S1 <-> S2).
S1 periodically calls S2's heartbeat endpoint (~every 90s) to keep both services active on Render
and maintain mutual health monitoring without in-memory state loss.

Key Guarantees:
1. Persistent State in Neon PostgreSQL (service_heartbeats table) - survives Render dyno restarts.
2. Async & Non-blocking: Uses httpx.AsyncClient and asyncio background task. Never blocks request handlers.
3. Resilient: Handles timeouts, DNS/connection drops, 4xx/5xx responses; retries on next cycle. Never crashes FastAPI.
4. Single-Loop Enforcement: Idempotent task creation prevents multiple loops across FastAPI reloads/workers.
5. Inbound Heartbeat: GET /api/heartbeat responds immediately (sub-10ms) with service health and diagnostic telemetry.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import httpx

logger = logging.getLogger("aerix.heartbeat")

# -----------------------------------------------------------------------------
# Configuration from Environment Variables
# -----------------------------------------------------------------------------
def get_service_id() -> str:
    return os.environ.get("SERVICE_ID", "S1").strip()


def get_s2_heartbeat_url() -> str:
    return os.environ.get("S2_HEARTBEAT_URL", "").strip()


def get_heartbeat_interval_seconds() -> float:
    try:
        val = float(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "90"))
        return max(5.0, val)  # minimum 5s guardrail
    except ValueError:
        return 90.0


def get_heartbeat_timeout_seconds() -> float:
    try:
        val = float(os.environ.get("HEARTBEAT_HTTP_TIMEOUT", "10.0"))
        return max(1.0, val)
    except ValueError:
        return 10.0


# -----------------------------------------------------------------------------
# Background Task Singleton Controls
# -----------------------------------------------------------------------------
_heartbeat_task: Optional[asyncio.Task] = None
_heartbeat_stop_event: Optional[asyncio.Event] = None
_task_lock = asyncio.Lock()

# In-memory fallback cache in case Neon is temporarily unreachable during a cycle
_in_memory_state: Dict[str, Any] = {
    "service_id": "S1",
    "target_url": "",
    "last_attempt_at": None,
    "last_success_at": None,
    "last_failure_at": None,
    "last_error": None,
    "consecutive_failures": 0,
    "consecutive_successes": 0,
    "status": "INITIALIZING",
    "updated_at": None,
}


# -----------------------------------------------------------------------------
# Database Persistence (Neon PostgreSQL)
# -----------------------------------------------------------------------------
def init_heartbeat_table(db_conn_factory: Callable[[], Any]) -> bool:
    """Ensures service_heartbeats table exists in Neon PostgreSQL."""
    conn = db_conn_factory()
    if not conn:
        logger.warning("Neon DB connection unavailable for heartbeat table initialization.")
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS service_heartbeats (
                service_id VARCHAR(50) PRIMARY KEY,
                target_url VARCHAR(500),
                last_attempt_at TIMESTAMPTZ,
                last_success_at TIMESTAMPTZ,
                last_failure_at TIMESTAMPTZ,
                last_error TEXT,
                consecutive_failures INTEGER DEFAULT 0,
                consecutive_successes INTEGER DEFAULT 0,
                status VARCHAR(50) DEFAULT 'INITIALIZING',
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as exc:
        logger.error(f"Failed to initialize service_heartbeats table: {exc}")
        try:
            conn.close()
        except Exception:
            pass
        return False


def load_persistent_heartbeat_state(db_conn_factory: Callable[[], Any], service_id: str = "S1") -> Dict[str, Any]:
    """Reads persistent state from Neon PostgreSQL; falls back to in-memory cache if unavailable."""
    global _in_memory_state
    conn = db_conn_factory()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT service_id, target_url, last_attempt_at, last_success_at,
                       last_failure_at, last_error, consecutive_failures,
                       consecutive_successes, status, updated_at
                FROM service_heartbeats
                WHERE service_id = %s;
            """, (service_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()

            if row:
                state = {
                    "service_id": row[0],
                    "target_url": row[1] or "",
                    "last_attempt_at": row[2].isoformat() if row[2] else None,
                    "last_success_at": row[3].isoformat() if row[3] else None,
                    "last_failure_at": row[4].isoformat() if row[4] else None,
                    "last_error": row[5],
                    "consecutive_failures": row[6] or 0,
                    "consecutive_successes": row[7] or 0,
                    "status": row[8] or "INITIALIZING",
                    "updated_at": row[9].isoformat() if row[9] else None,
                }
                _in_memory_state.update(state)
                return state
        except Exception as exc:
            logger.warning(f"Error querying service_heartbeats from Neon: {exc}")
            try:
                conn.close()
            except Exception:
                pass

    return dict(_in_memory_state)


def save_heartbeat_state(
    db_conn_factory: Callable[[], Any],
    service_id: str,
    target_url: str,
    attempt_at: Optional[datetime] = None,
    success: bool = False,
    error_msg: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Atomically updates persistent heartbeat state in Neon PostgreSQL using UPSERT.
    Also synchronizes in-memory fallback state.
    """
    global _in_memory_state
    now = datetime.now(timezone.utc)

    # Calculate status & counters
    current_status = "HEALTHY" if success else ("UNCONFIGURED" if not target_url else "DEGRADED")
    prev_failures = _in_memory_state.get("consecutive_failures", 0)
    prev_successes = _in_memory_state.get("consecutive_successes", 0)

    new_failures = 0 if success else (prev_failures + 1)
    new_successes = (prev_successes + 1) if success else 0
    last_success = now if success else _in_memory_state.get("last_success_at")
    last_failure = None if success else now

    _in_memory_state.update({
        "service_id": service_id,
        "target_url": target_url,
        "last_attempt_at": now.isoformat(),
        "last_success_at": last_success.isoformat() if isinstance(last_success, datetime) else last_success,
        "last_failure_at": last_failure.isoformat() if isinstance(last_failure, datetime) else last_failure,
        "last_error": error_msg,
        "consecutive_failures": new_failures,
        "consecutive_successes": new_successes,
        "status": current_status,
        "updated_at": now.isoformat(),
    })

    conn = db_conn_factory()
    if conn:
        try:
            cur = conn.cursor()
            if success:
                cur.execute("""
                    INSERT INTO service_heartbeats (
                        service_id, target_url, last_attempt_at, last_success_at,
                        last_error, consecutive_failures, consecutive_successes,
                        status, updated_at
                    ) VALUES (%s, %s, %s, %s, NULL, 0, 1, %s, %s)
                    ON CONFLICT (service_id) DO UPDATE SET
                        target_url = EXCLUDED.target_url,
                        last_attempt_at = EXCLUDED.last_attempt_at,
                        last_success_at = EXCLUDED.last_success_at,
                        last_error = NULL,
                        consecutive_failures = 0,
                        consecutive_successes = service_heartbeats.consecutive_successes + 1,
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at;
                """, (service_id, target_url, now, now, current_status, now))
            else:
                cur.execute("""
                    INSERT INTO service_heartbeats (
                        service_id, target_url, last_attempt_at, last_failure_at,
                        last_error, consecutive_failures, consecutive_successes,
                        status, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, 1, 0, %s, %s)
                    ON CONFLICT (service_id) DO UPDATE SET
                        target_url = EXCLUDED.target_url,
                        last_attempt_at = EXCLUDED.last_attempt_at,
                        last_failure_at = EXCLUDED.last_failure_at,
                        last_error = EXCLUDED.last_error,
                        consecutive_failures = service_heartbeats.consecutive_failures + 1,
                        consecutive_successes = 0,
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at;
                """, (service_id, target_url, now, now, error_msg, current_status, now))

            conn.commit()
            cur.close()
            conn.close()
        except Exception as exc:
            logger.warning(f"Failed to persist heartbeat state to Neon: {exc}")
            try:
                conn.close()
            except Exception:
                pass

    return dict(_in_memory_state)


# -----------------------------------------------------------------------------
# Outbound Heartbeat Request to S2
# -----------------------------------------------------------------------------
async def execute_outbound_heartbeat(
    db_conn_factory: Callable[[], Any],
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """
    Performs a single HTTP GET heartbeat request to S2.
    Handles timeouts, connection drops, and HTTP error codes gracefully.
    Never raises an uncaught exception.
    """
    service_id = get_service_id()
    target_url = get_s2_heartbeat_url()
    timeout_sec = get_heartbeat_timeout_seconds()

    if not target_url:
        logger.info("[Heartbeat S1 -> S2] S2_HEARTBEAT_URL is not configured. Waiting for configuration.")
        return save_heartbeat_state(
            db_conn_factory=db_conn_factory,
            service_id=service_id,
            target_url="",
            success=False,
            error_msg="S2_HEARTBEAT_URL not configured",
        )

    headers = {
        "User-Agent": f"AERIX-Heartbeat-S1/2.0 ({service_id})",
        "Accept": "application/json, text/plain",
    }

    should_close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True)
        should_close_client = True

    try:
        logger.debug(f"[Heartbeat S1 -> S2] Sending ping to {target_url} (timeout={timeout_sec}s)...")
        resp = await client.get(target_url, headers=headers)

        if 200 <= resp.status_code < 300:
            logger.info(f"[Heartbeat S1 -> S2] Success! S2 returned HTTP {resp.status_code}")
            return save_heartbeat_state(
                db_conn_factory=db_conn_factory,
                service_id=service_id,
                target_url=target_url,
                success=True,
            )
        else:
            err = f"S2 returned unexpected HTTP {resp.status_code}: {resp.text[:120]}"
            logger.warning(f"[Heartbeat S1 -> S2] Failed: {err}")
            return save_heartbeat_state(
                db_conn_factory=db_conn_factory,
                service_id=service_id,
                target_url=target_url,
                success=False,
                error_msg=err,
            )

    except httpx.TimeoutException:
        err = f"Connection to S2 timed out after {timeout_sec} seconds"
        logger.warning(f"[Heartbeat S1 -> S2] Timeout: {err}")
        return save_heartbeat_state(
            db_conn_factory=db_conn_factory,
            service_id=service_id,
            target_url=target_url,
            success=False,
            error_msg=err,
        )

    except httpx.ConnectError as exc:
        err = f"Failed to connect to S2: {exc}"
        logger.warning(f"[Heartbeat S1 -> S2] Connection Error: {err}")
        return save_heartbeat_state(
            db_conn_factory=db_conn_factory,
            service_id=service_id,
            target_url=target_url,
            success=False,
            error_msg=err,
        )

    except Exception as exc:
        err = f"Unexpected error pinging S2: {type(exc).__name__}: {exc}"
        logger.error(f"[Heartbeat S1 -> S2] Exception: {err}")
        return save_heartbeat_state(
            db_conn_factory=db_conn_factory,
            service_id=service_id,
            target_url=target_url,
            success=False,
            error_msg=err,
        )

    finally:
        if should_close_client:
            await client.aclose()


# -----------------------------------------------------------------------------
# Background Loop Engine
# -----------------------------------------------------------------------------
async def heartbeat_background_loop(db_conn_factory: Callable[[], Any]):
    """
    Continuous background loop that pings S2 every ~HEARTBEAT_INTERVAL_SECONDS.
    Runs asynchronously and cleanly pauses between cycles.
    """
    global _heartbeat_stop_event
    logger.info("[Heartbeat S1] Background heartbeat loop started.")

    # Initialize table on startup
    init_heartbeat_table(db_conn_factory)
    load_persistent_heartbeat_state(db_conn_factory, get_service_id())

    while _heartbeat_stop_event and not _heartbeat_stop_event.is_set():
        try:
            await execute_outbound_heartbeat(db_conn_factory)
        except Exception as exc:
            logger.error(f"[Heartbeat S1] Unhandled loop iteration exception: {exc}", exc_info=True)

        interval = get_heartbeat_interval_seconds()
        logger.debug(f"[Heartbeat S1] Sleeping {interval}s until next S2 heartbeat cycle...")

        # Responsive sleep that terminates immediately if stop_event is signaled
        try:
            await asyncio.wait_for(_heartbeat_stop_event.wait(), timeout=interval)
            break  # stop_event was triggered
        except asyncio.TimeoutError:
            # Interval elapsed naturally, proceed to next ping
            continue

    logger.info("[Heartbeat S1] Background heartbeat loop exited cleanly.")


def start_heartbeat_task(db_conn_factory: Callable[[], Any]) -> bool:
    """
    Idempotently starts the S1 background heartbeat task.
    Prevents duplicate loops from spawning on multiple worker calls or reloads.
    """
    global _heartbeat_task, _heartbeat_stop_event

    if _heartbeat_task is not None and not _heartbeat_task.done():
        logger.info("[Heartbeat S1] Heartbeat task is already active. Duplicate start ignored.")
        return False

    _heartbeat_stop_event = asyncio.Event()
    loop = asyncio.get_event_loop()
    _heartbeat_task = loop.create_task(
        heartbeat_background_loop(db_conn_factory),
        name="s1-heartbeat-background-task",
    )
    logger.info("[Heartbeat S1] Heartbeat background task spawned.")
    return True


async def stop_heartbeat_task():
    """Signals stop and awaits task termination cleanly for graceful FastAPI shutdown."""
    global _heartbeat_task, _heartbeat_stop_event
    if _heartbeat_stop_event:
        _heartbeat_stop_event.set()

    if _heartbeat_task and not _heartbeat_task.done():
        logger.info("[Heartbeat S1] Stopping heartbeat background task...")
        _heartbeat_task.cancel()
        try:
            await _heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info("[Heartbeat S1] Heartbeat background task stopped.")

    _heartbeat_task = None
    _heartbeat_stop_event = None


def is_heartbeat_loop_running() -> bool:
    """Returns True if the background task is currently active."""
    return _heartbeat_task is not None and not _heartbeat_task.done()
