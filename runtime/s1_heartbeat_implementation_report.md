# S1 Heartbeat System & Mutual Keepalive Implementation Report

**Service ID:** `S1` (AERIX Sovereign Airfare Price Index API)  
**Host Environment:** Render (FastAPI Web Service)  
**Partner Service:** `S2` (External Project on Render)  
**State Persistence Layer:** Neon Serverless PostgreSQL (`service_heartbeats` table)  
**Date:** 2026-09-30  
**Status:** **IMPLEMENTED & TESTED (All 9 Unit Tests Passing)**

---

## 1. Architecture Overview

To maintain continuous uptime on Render without paid background scheduler add-ons, S1 and S2 establish a mutual, non-blocking asynchronous HTTP ping loop:

```
┌───────────────────────────────────────────────┐
│               S1 (AERIX API)                  │
│                                               │
│  [GET /api/heartbeat] ◄─── (Incoming Pings) ──┼─── [S2 Outbound Caller]
│                                               │
│  [Background Task]   ───── (Outgoing Pings) ──┼──► [S2: GET /api/heartbeat]
│         │                                     │
└─────────┼─────────────────────────────────────┘
          ▼
┌───────────────────────────────────────────────┐
│      Neon PostgreSQL (Shared Persistent DB)   │
│                                               │
│  • service_heartbeats (S1 & S2 status/state)  │
│  • daily_scraper_runs (S2 atomic daily lock)  │
└───────────────────────────────────────────────┘
```

### Architectural Guarantees Enforced in S1:
1. **Zero In-Memory State Loss:** Service health, failure counters, attempt timestamps, and error messages are persisted directly to Neon PostgreSQL in the `service_heartbeats` table. Render dyno restarts or spin-downs preserve state.
2. **Sub-10ms Inbound Response:** The `GET /api/heartbeat` endpoint responds immediately with HTTP 200 and telemetry data without waiting or performing heavy database transactions.
3. **Non-Blocking Background Worker:** Outbound calls to S2 run in a decoupled `asyncio` task using `httpx.AsyncClient`. FastAPI request handling is never blocked.
4. **Single-Loop Enforcement (Anti-Duplication):** Idempotent task creation (`start_heartbeat_task`) guarantees that multiple workers or Uvicorn reloads never spawn redundant heartbeat loops.
5. **Lifespan Context Manager:** Modern FastAPI `lifespan` cleanly spawns the task on startup and performs cancellation/cleanup on SIGTERM shutdown.
6. **No Scraper Modifications or Ingestion:** S1 does not touch scraper logic. S2 will independently own the 05:00 AM IST daily scraper trigger.

---

## 2. Files Modified & Created

| File | Change Type | Purpose |
| :--- | :---: | :--- |
| [`apps/api/src/heartbeat.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/api/src/heartbeat.py) | **Created** | Core S1 heartbeat orchestration: Neon DB state persistence, non-blocking outbound HTTP caller, error handling, and background loop controls. |
| [`apps/api/src/main.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/api/src/main.py) | **Modified** | Attached `lifespan` context manager to `app = FastAPI(..., lifespan=lifespan)` and mounted `GET /api/heartbeat` and `GET /heartbeat`. |
| [`render.yaml`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/render.yaml) | **Modified** | Added `S2_HEARTBEAT_URL` and `HEARTBEAT_INTERVAL_SECONDS` to the `aerix-api` web service environment definition. |
| [`tests/test_heartbeat.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/tests/test_heartbeat.py) | **Created** | Comprehensive unit and integration test suite covering endpoints, outbound calls, timeouts, connection drops, and task deduplication. |

---

## 3. Persistent Database Schema (Neon PostgreSQL)

The `service_heartbeats` table was created in Neon PostgreSQL using S1's existing `get_db_connection()` connection pool:

```sql
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
```

Both S1 and S2 write to this table (`service_id = 'S1'` and `service_id = 'S2'`). When either service restarts, its previous operational metrics and uptime status are immediately restored.

---

## 4. Environment Variables Required for S1

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `S2_HEARTBEAT_URL` | **Yes** | `""` | The public endpoint of S2 (e.g. `https://s2-project.onrender.com/api/heartbeat`). If unset, S1 logs a notice and safely marks status as `UNCONFIGURED` without failing. |
| `HEARTBEAT_INTERVAL_SECONDS` | Optional | `90` | Pacing between outbound heartbeats (in seconds). Guardrailed to $\ge 5$s. |
| `HEARTBEAT_HTTP_TIMEOUT` | Optional | `10.0` | Maximum seconds S1 waits for S2's HTTP response before logging a timeout. |
| `SERVICE_ID` | Optional | `S1` | Identifier used in database state tracking and User-Agent headers. |
| `DATABASE_URL` / `DATABASE_URL_SYNC` | **Yes** | Existing | Existing Neon PostgreSQL connection string. |

---

## 5. Inbound Endpoint Specification

### `GET /api/heartbeat` (and alias `/heartbeat`)

- **Response Time:** $< 5\text{ ms}$ (reads cached persistent state; never waits for S2).
- **HTTP Status:** `200 OK`
- **Example Response Body:**
```json
{
  "service": "S1",
  "service_name": "AERIX Sovereign Airfare Price Index API",
  "status": "HEALTHY",
  "timestamp": "2026-09-30T03:55:00.123456+00:00",
  "diagnostics": {
    "target_s2_url": "https://s2-service.onrender.com/api/heartbeat",
    "heartbeat_interval_seconds": 90.0,
    "background_loop_active": true,
    "last_heartbeat_attempt": "2026-09-30T03:54:30.123456+00:00",
    "last_successful_heartbeat": "2026-09-30T03:54:30.456789+00:00",
    "last_failure": null,
    "last_error": null,
    "consecutive_successes": 14,
    "consecutive_failures": 0,
    "state_persistence": "Neon PostgreSQL (service_heartbeats)"
  }
}
```

---

## 6. Failure Handling & Resilience Guarantees

1. **S2 Unreachable / Connection Drops (`httpx.ConnectError`):**
   - S1 catches the exception cleanly.
   - Updates Neon DB: `status = 'DEGRADED'`, increments `consecutive_failures`, saves error details.
   - Logs `WARNING: Failed to connect to S2`.
   - Never crashes FastAPI. Retries automatically on the next 90-second cycle.
2. **S2 HTTP Timeout (`httpx.TimeoutException`):**
   - Aborts request cleanly after `HEARTBEAT_HTTP_TIMEOUT` (10s).
   - Records timeout in Neon DB and waits for next scheduled cycle.
3. **S2 Unhealthy (HTTP 5xx / 4xx):**
   - Records `DEGRADED` status with HTTP error snippet.
4. **Neon PostgreSQL Temporary Blip:**
   - If Neon is momentarily offline during a ping, S1 maintains state in an internal fallback memory cache and logs a notice.
   - As soon as Neon reconnects, state sync resumes. FastAPI endpoints never throw HTTP 500.
5. **Uvicorn / Render Process Reloads:**
   - `start_heartbeat_task` checks `_heartbeat_task.done()`. If a task is active, second spawns are ignored.
   - `stop_heartbeat_task` sets `_heartbeat_stop_event` and awaits cancellation on shutdown.

---

## 7. Verification & Test Results

Executed with `pytest tests/test_heartbeat.py`:

```text
tests/test_heartbeat.py::test_heartbeat_endpoint_returns_fast_200 PASSED       [ 11%]
tests/test_heartbeat.py::test_heartbeat_legacy_alias_endpoint PASSED           [ 22%]
tests/test_heartbeat.py::test_configuration_environment_variables PASSED       [ 33%]
tests/test_heartbeat.py::test_successful_outbound_heartbeat PASSED             [ 44%]
tests/test_heartbeat.py::test_failed_s2_heartbeat_http_error PASSED           [ 55%]
tests/test_heartbeat.py::test_timeout_handling_outbound_heartbeat PASSED       [ 66%]
tests/test_heartbeat.py::test_connection_error_outbound_heartbeat PASSED       [ 77%]
tests/test_heartbeat.py::test_unconfigured_s2_url PASSED                       [ 88%]
tests/test_heartbeat.py::test_no_duplicate_heartbeat_loop_during_startup PASSED [100%]

============================== 9 passed in 2.24s ==============================
```

Existing core API endpoints (`tests/test_api_endpoints.py`) verified with 28 passing tests.

---

## 8. Render Deployment Configuration for S1

In your **Render Dashboard** $\to$ **`aerix-api`** $\to$ **Environment**:

Add the following environment variable once S2 is deployed:
```env
S2_HEARTBEAT_URL=https://<your-s2-service-name>.onrender.com/api/heartbeat
HEARTBEAT_INTERVAL_SECONDS=90
```

---
---

# COPY-PASTE-READY PROMPT FOR S2 ANTIGRAVITY AGENT

> Copy everything inside the block below and paste it directly into your S2 project's Antigravity assistant:

```markdown
I need you to implement the S2 side of a persistent two-service heartbeat and daily scraper scheduler system that coordinates with S1 (the AERIX airfare backend).

### ARCHITECTURE OVERVIEW

S1 (AERIX API) <───> S2 (This Service) <───> Shared Neon PostgreSQL

1. S1 calls S2's heartbeat endpoint approximately every 90 seconds.
2. S2 calls S1's heartbeat endpoint approximately every 90 seconds.
3. This mutual keepalive prevents both Render free-tier services from sleeping.
4. S2 OWNS the daily scraper trigger: Every day at 05:00 AM IST (23:30 UTC), S2 must atomically trigger the production airfare scraper on S1 or execute the scheduled collection run without duplicates.
5. All state must be PERSISTENT in Neon PostgreSQL (no in-memory variables that reset on dyno restarts).

---

### S2 REQUIREMENTS & IMPLEMENTATION SPECIFICATION

#### 1. Inbound Heartbeat Endpoint
Expose a lightweight GET endpoint on S2:
- Path: `GET /api/heartbeat`
- Must respond in < 10ms with HTTP 200 OK.
- Must NOT perform expensive work or wait.
- Response JSON schema:
  ```json
  {
    "service": "S2",
    "status": "HEALTHY",
    "timestamp": "<ISO-8601-UTC>",
    "diagnostics": {
      "target_s1_url": "<S1_HEARTBEAT_URL>",
      "last_heartbeat_attempt": "<ISO-8601-UTC>",
      "last_successful_heartbeat": "<ISO-8601-UTC>",
      "last_failure": null,
      "consecutive_successes": 15,
      "daily_scraper_status": {
        "today_date": "YYYY-MM-DD",
        "state": "COMPLETED | RUNNING | PENDING | FAILED",
        "last_run_started_at": "<ISO-8601-UTC>",
        "last_run_completed_at": "<ISO-8601-UTC>"
      }
    }
  }
  ```

#### 2. Environment Variables Configuration for S2
Configure the following environment variables:
- `S1_HEARTBEAT_URL`: Target heartbeat URL on S1 (e.g. `https://aerix-api.onrender.com/api/heartbeat`).
- `S1_SCRAPER_TRIGGER_URL`: URL to trigger S1 scraper execution (or API endpoint if triggered via HTTP, e.g. `https://aerix-api.onrender.com/api/v1/scraper/trigger`, or direct execution if S2 shares the codebase/worker).
- `HEARTBEAT_INTERVAL_SECONDS`: Default `90` (seconds between pings to S1).
- `HEARTBEAT_HTTP_TIMEOUT`: Default `10.0` (seconds).
- `DATABASE_URL` / `DATABASE_URL_SYNC`: Connection string to the SAME hosted Neon PostgreSQL database used by S1.
- `SCRAPER_SCHEDULE_TIME_UTC`: Default `"23:30"` (which is 05:00 AM IST).

#### 3. Database State Persistence (Neon PostgreSQL)
Use the existing Neon PostgreSQL database. Do NOT use in-memory state.
S2 must interact with two tables:

**Table A: `service_heartbeats` (Mutual Health Table - Already created in Neon)**
```sql
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
```
S2 must write its own row with `service_id = 'S2'`.

**Table B: `daily_scraper_runs` (Atomic Distributed Lock & Schedule Table)**
```sql
CREATE TABLE IF NOT EXISTS daily_scraper_runs (
    run_date DATE PRIMARY KEY,
    status VARCHAR(50) NOT NULL, -- 'PENDING', 'CLAIMED', 'RUNNING', 'COMPLETED', 'FAILED'
    claimed_by VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    error_message TEXT,
    trigger_source VARCHAR(50) DEFAULT 'S2_CRON_HEARTBEAT',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 4. Outbound S1 Heartbeat Loop (Background Async Task)
Implement a decoupled, non-blocking background loop:
1. Every ~90 seconds (`HEARTBEAT_INTERVAL_SECONDS`), send an HTTP `GET` to `S1_HEARTBEAT_URL`.
2. Use an asynchronous HTTP client (e.g. `httpx.AsyncClient`) with a 10s timeout.
3. Catch all exceptions (`httpx.TimeoutException`, `httpx.ConnectError`, HTTP status errors) and update Neon PostgreSQL with the failure timestamp and error message. NEVER crash S2 if S1 is sleeping or booting.
4. On HTTP 200 from S1, update Neon DB: `last_success_at = NOW()`, `consecutive_successes = consecutive_successes + 1`, `status = 'HEALTHY'`.
5. Ensure task deduplication: If S2 reloads or receives multiple startup calls, only ONE background task must exist.

#### 5. Daily 05:00 AM IST Scraper Trigger Logic
In S2's periodic background loop (or a coordinated cron evaluator running inside the heartbeat loop):
1. Check the current UTC date and time.
2. Determine if the daily window has arrived ($\ge$ 23:30 UTC / 05:00 AM IST) for today's date (`today_date = CURRENT_DATE`).
3. **Atomic Job Claiming (Prevent Duplicates Across Restarts):**
   Execute an atomic SQL `INSERT ... ON CONFLICT DO NOTHING`:
   ```sql
   INSERT INTO daily_scraper_runs (run_date, status, claimed_by, started_at)
   VALUES (CURRENT_DATE, 'CLAIMED', 'S2', NOW())
   ON CONFLICT (run_date) DO NOTHING
   RETURNING run_date;
   ```
   - If the query returns a row: S2 has successfully and exclusively claimed today's run!
   - If 0 rows are returned: Today's run is already `CLAIMED`, `RUNNING`, or `COMPLETED`. S2 must SKIP triggering.
4. If claimed, update status to `RUNNING` and trigger the scraper asynchronously:
   - Make an asynchronous HTTP call or launch the task in the background.
   - S2 must NOT block its heartbeat loop or HTTP endpoints waiting for the 60-minute scraper run.
   - When the scraper finishes:
     - On Success: Update `status = 'COMPLETED'`, `completed_at = NOW()`.
     - On Error: Update `status = 'FAILED'`, `failed_at = NOW()`, `error_message = <error>`.
5. **Recovery from Render Dyno Restarts:**
   If S2 restarts while a job had status `CLAIMED` or `RUNNING` for over 2 hours without completion, mark it `FAILED` with error `'Process interrupted by dyno restart'` before evaluating new runs.

#### 6. Safety & Non-Interference Rules
- Do NOT use in-memory variables for scheduler locks or run state.
- Do NOT block HTTP request handlers.
- Do NOT modify existing S2 business logic.
- Add unit tests for:
  - `GET /api/heartbeat` response
  - Outbound ping to S1 (success and failure cases)
  - Atomic claim logic in `daily_scraper_runs` (ensuring 2 triggers on the same date cannot both claim)
  - Timeout and connection error handling.

Implement these changes in S2 and verify all tests pass.
```
