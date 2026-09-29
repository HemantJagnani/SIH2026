# AERIX Scraper Audit: GitHub Actions Scheduled Execution Readiness

**Date:** 2026-09-30  
**Target Environment:** GitHub Actions (Linux `ubuntu-latest` Runner)  
**Execution Trigger:** Scheduled Cron (`schedule: - cron: '30 23 * * *'`) & Manual (`workflow_dispatch`)  
**Status:** **AUDIT COMPLETED (Code Unchanged)**

---

## 1. Executive Summary & Suitability Assessment

| Criterion | Evaluation | Verdict |
| :--- | :--- | :---: |
| **Execution Environment** | Linux `ubuntu-latest` with Python 3.12 & Playwright Chromium | **SUITABLE** |
| **Code Modifications Required** | Can the scraper run unchanged? | **YES (Runs Unchanged)** |
| **Database Direct Write** | Does `run_production_matrix_top60.py` write to Neon PostgreSQL? | **NO (Writes to Local Files)** |
| **Headless Capability** | Headless Chromium execution supported via `SCRAPER_HEADLESS=true` | **SUITABLE** |
| **Evidence & Report Generation** | Generates JSON, Markdown, and `.tar.gz` evidence archives | **SUITABLE** |
| **Bot Detection & Safe-Stop** | Strict compliance: detects CAPTCHA/403/429 and halts cleanly | **SUITABLE** |
| **Free Tier Quota Fit** | Full 360-cell sweep takes ~45–80 min ($30 \times 75\text{ min} = 2,250\text{ min/mo}$) | **POTENTIAL QUOTA RISK** (Private Repos: 2,000 min/mo; Public Repos: Unlimited) |
| **IP Reputation / Cloud Blocks** | GitHub Actions Microsoft Azure IPs are frequently rate-limited by OTAs | **MAJOR TECHNICAL LIMITATION** |

---

## 2. Technical Audit Questions & Findings

### 1. Exact Scraper Entrypoint Command
The primary production runner for the complete 60-route $\times$ 6 lead-time matrix (360 cells) is:
```bash
python apps/scraper/src/scripts/run_production_matrix_top60.py
```
*(Secondary smaller test runners exist: `apps/scraper/src/scripts/run_production_matrix_top10.py` for 60 cells, and `apps/scraper/src/scripts/run_controlled_live_test.py` for single-route validation).*

### 2. Python Version Required
- Pinned in `pyproject.toml`: **`>=3.12`**.
- Recommended GitHub Actions configuration: **`python-version: '3.12'`**.

### 3. All Python Dependencies
The scraper requires dependencies listed in `requirements.txt`:
```
crawlee>=0.4.0
playwright>=1.46.0
httpx>=0.27.0
pydantic>=2.8.0
lxml>=5.3.0
parsel>=1.9.0
SQLAlchemy>=2.0.0
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
redis>=5.0.0
alembic>=1.13.0
python-dotenv>=1.0.0
pytz>=2024.1
```

### 4. Whether Playwright/Chromium is Required
**YES.**  
The scraper's `CollectionOrchestrator` uses `GoogleFlightsAdapter`, which instantiates Crawlee's `PlaywrightCrawler` with `browser_type="chromium"`.

### 5. Required System & Browser Dependencies
On GitHub Actions' Ubuntu runner, the Chromium browser binary and all necessary Linux shared libraries (e.g., `libnss3`, `libasound2`, `libgbm1`) must be installed before running:
```bash
playwright install --with-deps chromium
```

### 6. Required Environment Variables
To run cleanly in GitHub Actions, the following environment variables must be declared in the workflow:
- `PYTHONPATH=.` (enables resolution of `apps/scraper/src` and `models`)
- `SCRAPER_HEADLESS=true` (forces headless browser execution)
- `SCRAPER_BROWSER_TYPE=chromium`
- `GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }}` (for automated evidence release creation)

### 7. Whether DATABASE_URL Can Be Supplied Through GitHub Secrets
**YES.**  
GitHub Actions supports encrypted repository secrets:
- `${{ secrets.DATABASE_URL }}` (asyncpg URI for async storage)
- `${{ secrets.DATABASE_URL_SYNC }}` (psycopg2 URI for sync storage)
These values are masked automatically (`***`) in runner logs.

### 8. Whether the Scraper Writes Directly to Neon PostgreSQL
**NO.** *(Critical Architectural Finding)*  
The scraper script `apps/scraper/src/scripts/run_production_matrix_top60.py` writes its results exclusively to **local disk files**:
1. `runtime/top60_fare_observations.json`
2. `runtime/top60_observation_classification.json`
3. `APIx_All60_Production_Coverage_Report.json`
4. `APIx_All60_Production_Coverage_Report.md`
5. `runtime/evidence/` (DOM snapshots and raw search HTML)

It calls `auto_archive_and_sync()` to create a `.tar.gz` evidence archive, but **does not issue SQL `INSERT` commands to Neon PostgreSQL**.  
*(Historical database ingestion was performed by `scripts/migrate_to_neon.py` or `apps/scraper/src/storage/postgres.py`).*

> **Impact in GitHub Actions**: Because GitHub Actions runners use ephemeral virtual machines, all local files are destroyed when the job completes. To preserve the data, the workflow must:
> - Upload the reports and JSON files using `actions/upload-artifact@v4`, AND/OR
> - Execute a post-scrape database ingestion script to commit rows into Neon PostgreSQL.

### 9. Expected Runtime for One Production Collection
- Total Scope: **360 cells** (60 routes $\times$ 6 lead-time horizons).
- Rate Limiting: Human-like interaction pauses (2–5 seconds per page) + DOM extraction duration (~8–12 seconds per cell).
- Runtime estimate:
  - Top-60 Full Matrix: **~45 to 80 minutes**.
  - Top-10 Reduced Matrix: **~12 to 18 minutes**.
- Free Tier Limits:
  - Maximum job execution timeout on GitHub Actions: **360 minutes (6 hours)** $\to$ *Execution time fits within the single-job limit.*
  - Monthly allowance for private repositories: **2,000 minutes/month**.  
    *(Daily 75-minute runs = 2,250 min/month, slightly exceeding the private quota. Running on a public repository is 100% free with unlimited minutes).*

### 10. Technical Suitability of GitHub Actions
GitHub Actions is **technically suitable**, with one major caveat:
- **Suitability**: Excellent for running Playwright, Python, cron scheduling, and artifact archiving.
- **Risk**: **Cloud IP Rate Limiting**. Google Flights and major OTAs actively monitor and throttle datacenter IP blocks (Microsoft Azure IP ranges assigned to GitHub Actions). A high probability of HTTP 429 / CAPTCHA challenge exists when hitting 360 cells consecutively from a cloud runner IP.

### 11. Existing Local Filesystem Dependencies
1. `config/dgca_cy2024_top60.json`: Confirmed tracked in Git repository $\to$ *Available on runner.*
2. `runtime/` directory: Contains tracked files (`.json`, `.md`) $\to$ *Directory structure exists on runner.*
3. Missing prior classification: If `runtime/top60_observation_classification.json` is missing (gitignored), the script gracefully scrapes fresh cells without crashing.

### 12. Evidence Files Handling
- **Generation**: Captured by `core/evidence.py` into `runtime/evidence/<run_id>/<job_id>/` (DOM HTML + screenshots).
- **Archiving**: `scripts/archive_and_sync_evidence.py` packages evidence into `apix_evidence_<date>.tar.gz` and attempts to upload it to a GitHub release tag (`v1.0-evidence`).
- **Post-Run Storage**: Required for regulatory auditability. Can be preserved as a GitHub Actions Artifact for 90 days.

### 13. Safe-Stop Behavior for CAPTCHA/Blocking
**CONFIRMED AND VERIFIED.**  
`apps/scraper/src/core/anti_bot_detector.py` and `crawler.py` strictly adhere to Phase 9 compliance:
- `retry_on_blocked=False`: Never attempts automated bypass.
- `max_session_rotations=0`: Never attempts session rotation or proxy hopping.
- `respect_robots_txt_file=True`: Enforces robots.txt policy.
- On HTTP 403 / 429 / CAPTCHA: Captures evidence snapshot, marks `AvailabilityStatus.CAPTCHA_BLOCKED` or `RATE_LIMITED`, and terminates the job cleanly.

---

## 3. Recommended GitHub Actions Workflow Design

*(For future implementation when authorized)*

### Required Workflow Steps
1. `actions/checkout@v4` (Fetch repository code)
2. `actions/setup-python@v5` with `python-version: '3.12'` and pip caching enabled
3. `pip install -r requirements.txt` (Install application dependencies)
4. `playwright install --with-deps chromium` (Install headless Chromium and system libraries)
5. Execute Scraper: `python apps/scraper/src/scripts/run_production_matrix_top60.py`
6. Post-Scrape Ingestion (Optional step to write observations into Neon PostgreSQL)
7. `actions/upload-artifact@v4` (Upload coverage report, classification JSON, and evidence tarball)

### Required GitHub Secrets
- `DATABASE_URL_SYNC`: Connection string to Neon PostgreSQL
- `DATABASE_URL`: Asynchronous connection string to Neon PostgreSQL
- `GITHUB_TOKEN`: Standard repository token with `contents: write` permissions (for release uploads)

---

## 4. Final Audit Verdict

- **Can the existing scraper run unchanged in GitHub Actions?**  
  **YES.** The Python code and CLI entrypoint require zero modifications to execute on `ubuntu-latest`.
- **Primary Operational Consideration:**  
  Because the script writes to local JSON files rather than directly issuing SQL inserts to Neon, a post-scrape database ingestion step or artifact upload is needed to make the data permanently available to the Render backend API.
