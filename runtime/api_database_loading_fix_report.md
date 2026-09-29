# AERIX API Database Loading Fix & Verification Report

**Audit Date**: September 29, 2026  
**System Evaluated**: `apps/api/src/main.py`  
**Database**: Hosted Neon PostgreSQL (`fare_observations`)  
**Overall Status**: **RESOLVED & VERIFIED** (187/187 Tests Passing; 10/10 Live Endpoints Verified)

---

## 1. Executive Summary

An audit of [`apps/api/src/main.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/api/src/main.py) was conducted to investigate why hosted Neon PostgreSQL observations were being discarded in favor of stale local fallback files or returning empty results.

The investigation confirmed that an arbitrary hardcoded threshold (`len(rows) >= 11000`) at line 91 in `load_top60_observations()` was rejecting genuine production database records because the database currently contains **9,197** verified records (which is less than 11,000). Furthermore, the SQL query selected only 13 columns, omitting critical canonical fields needed by downstream matrix and yield curve endpoints, and `/api/v1/quality-metrics` was reading from an obsolete local JSON file rather than the live database.

These issues have been resolved without altering scraper code, econometric index mathematics, production datasets, DGCA data, or frontend contracts.

---

## 2. Root Cause Analysis

### Root Cause 1: Arbitrary Minimum Row-Count Threshold
- **Location**: [`apps/api/src/main.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/api/src/main.py) (former line 91 & line 127)
- **Defect**: The condition `if rows and len(rows) >= 11000:` explicitly discarded query results whenever the hosted Neon database returned fewer than 11,000 records. Because the hosted database contains 9,197 genuine quotes (8,998 Google Flights + 145 EaseMyTrip + 54 Ignav), `9,197 < 11,000`, causing the API to silently drop valid database data.
- **Resolution**: Removed all row-count thresholds. Valid records returned from successful queries are now accepted authoritatively based on query success, valid rows, and required fields.

### Root Cause 2: Incomplete SQL Query & Missing Canonical Fields
- **Location**: `load_top60_observations()` SQL query (former lines 80–87)
- **Defect**: The query only selected 13 columns and restricted `WHERE source = 'google_flights'`. It omitted critical fields including `airline_code`, `cabin`, `fare_family`, `currency`, `quality_status`, `product_stratum_id`, `itinerary_fingerprint`, `offer_fingerprint`, `departure_time_local`, `arrival_time_local`, `requires_self_transfer`, `price_status`, and `passenger_count`.
- **Resolution**: Updated query to select all 27 canonical columns from `fare_observations`. Mapped and derived all 20+ canonical fields with explicit derivations documented.

### Root Cause 3: Status Normalization Disconnect
- **Location**: Filtering in downstream endpoints (`status == "VALID_BASELINE"`)
- **Defect**: Downstream endpoints (such as `/api/v1/matrix`) filtered for `status == 'VALID_BASELINE'`, but raw database rows store `quality_status = 'VALID'`. The old database loading logic never assigned or normalized the `status` field, causing matrix cells to drop records.
- **Resolution**: Normalized status transparently:
  - If `quality_status == 'VALID'`:
    - If `requires_self_transfer` is True $\rightarrow$ `'FOREIGN_TRANSIT'`
    - Else if `fare_family` in ('FLEX', 'PREMIUM', 'BUSINESS') $\rightarrow$ `'HIGHER_FARE_FAMILY'`
    - Else $\rightarrow$ `'VALID_BASELINE'` (standard economy retail quote)
  - If `quality_status == 'DUPLICATE'` $\rightarrow$ `'DUPLICATE'`
  - Otherwise $\rightarrow$ `quality_status` value.

### Root Cause 4: Disconnected Quality Metrics Source
- **Location**: [`get_quality_metrics()`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/api/src/main.py#L688-L718)
- **Defect**: Endpoint called `load_canonical_data()`, which loaded `easemytrip_normalized_data.json` (145 records on 1 route), completely ignoring the 9,197 observations across 58 routes in Neon DB.
- **Resolution**: Updated `get_quality_metrics()` to consume `load_top60_observations()`, dynamically calculating observations, strata, itineraries, and routes from live database data.

### Root Cause 5: Redundant Database Queries in Observations & Real Backtest
- **Location**: `/api/observations` and `/api/v1/backtest?mode=real`
- **Defect**: Both endpoints established a new database connection and ran un-cached queries on every request, violating performance requirements.
- **Resolution**: Unified both endpoints to consume `load_top60_observations()`, reusing `_top60_obs_cache` and eliminating redundant database round-trips.

---

## 3. Files Changed

| File Path | Description of Changes |
| :--- | :--- |
| [`apps/api/src/main.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/api/src/main.py) | • Removed `>= 11000` row thresholds from `load_top60_observations()` and fallback.<br>• Expanded SQL query to select all 27 columns from `fare_observations`.<br>• Implemented canonical mapping for 20+ fields (route, origin, destination, lead_time, status, quality_status, product_stratum_id, etc.).<br>• Implemented safe in-memory caching with distinct DB failure vs. empty table diagnostics.<br>• Updated `get_quality_metrics()` to compute metrics from `load_top60_observations()`.<br>• Updated `get_coverage()` to compute status breakdown dynamically from `obs_all`.<br>• Updated `get_observations()` and `get_backtest_results(mode='real')` to reuse in-memory cache. |

---

## 4. Canonical Observation Mapping Specification

All observations loaded from the hosted Neon database or disk fallback contain the following canonical fields:

| Field Name | Type | Source / Derivation Rule |
| :--- | :--- | :--- |
| `route` | string | Derived: `f"{origin}-{destination}"` (e.g. `"BLR-DEL"`) |
| `origin` | string | Direct from DB column `origin` (3-letter IATA) |
| `destination` | string | Direct from DB column `destination` (3-letter IATA) |
| `travel_date` | string | Flight departure date (YYYY-MM-DD) from DB column `travel_date` |
| `collection_date` | string | Derived from DB timestamp `collected_at` (YYYY-MM-DD) |
| `observation_date`| string | Derived from DB timestamp `collected_at` (YYYY-MM-DD) |
| `collected_at` | string | Full ISO 8601 UTC timestamp from DB column `collected_at` |
| `lead_days` | integer | Advance booking window in days from DB column `lead_days` |
| `lead_time` | string | Derived via `_lead_class(lead_days)`: `T+1`, `T+7`, `T+15`, `T+21`, `T+30`, `T+45` |
| `status` | string | Derived: `'VALID_BASELINE'` for valid standard economy non-self-transfer; `'FOREIGN_TRANSIT'` if self-transfer; `'HIGHER_FARE_FAMILY'` if flex/premium; `'DUPLICATE'` if duplicate |
| `quality_status` | string | Direct from DB column `quality_status` (`'VALID'`) |
| `product_stratum_id` | string | Direct from DB column `product_stratum_id` if present; else canonically derived per §5 as `f"{origin}_{dest}_{carrier}_{cabin}_{lead_time}"` |
| `airline` | string | Operating/marketing airline name from DB column `airline` |
| `airline_code` | string | 2-letter IATA airline designator from DB column `airline_code` |
| `flight_number` | string | Direct from DB column `flight_number` |
| `total_fare` | float | Final payable fare in INR from DB column `total_fare` |
| `base_fare` | float | Base unbundled fare in INR from DB column `base_fare` (0.0 if not split) |
| `taxes` | float | Sovereign and airport taxes in INR from DB column `taxes` (0.0 if not split) |
| `currency` | string | Direct from DB column `currency` (defaults to `'INR'`) |
| `source` | string | Direct from DB column `source` (e.g. `'google_flights'`, `'easemytrip'`) |
| `cabin` | string | Service class from DB column `cabin` (defaults to `'ECONOMY'`) |
| `fare_family` | string | Fare tier from DB column `fare_family` (null if standard) |
| `baggage` | null | Explicitly `None` (baggage allowance is not tracked as a separate column in `fare_observations`) |
| `stops` | integer | Stop count from DB column `stops` (0 if direct) |
| `stop_category` | string | Derived: `'NON_STOP'` if stops == 0 else (`'ONE_STOP'` if stops == 1 else `'MULTI_STOP'`) |
| `passenger_count`| integer | Direct from DB column `passenger_count` (defaults to 1) |
| `passenger_type` | string | Derived: `'ADULT'` (standard single-passenger retail quote) |
| `availability` | string | Direct from DB column `availability` (`'AVAILABLE'`) |
| `itinerary_fingerprint` | string | DB column or derived per §6: `f"{origin}_{dest}_{carrier}_{fl_num}_{travel_date}"` |
| `offer_fingerprint` | string | Direct from DB column `offer_fingerprint` |
| `departure_time_local` | string | ISO timestamp from DB column `departure_time_local` |
| `arrival_time_local` | string | ISO timestamp from DB column `arrival_time_local` |
| `requires_self_transfer` | boolean | Direct from DB column `requires_self_transfer` (False if null) |
| `price_status` | string | Direct from DB column `price_status` (`'OK'`) |

---

## 5. Cache & Fallback Architecture

```
                  Client Request
                        │
                        ▼
            Is _top60_obs_cache populated?
              ├── YES ──► Return cached records (0ms, 0 DB roundtrips)
              └── NO
                    │
                    ▼
          Query Hosted Neon PostgreSQL
              ├── Success & Rows > 0 ──► Map canonical fields
              │                           ├── Set _top60_obs_cache
              │                           ├── Set _top60_obs_source = "HOSTED_NEON_DB"
              │                           └── Return records
              │
              ├── Query Exception / Conn Error ──► Log warning; do NOT overwrite valid cache
              │                                      │
              └── Empty Result (0 rows) ────────────┘
                                                     │
                                                     ▼
                                      Fallback to Local Disk
                                        ├── 1. top60_observation_classification.json
                                        └── 2. top60_fare_observations.json
                                              (Zero row thresholds; maps canonical fields)
```

- **Safe In-Memory Caching**: The first request performs the Neon query, validates, and populates `_top60_obs_cache`. Subsequent requests return immediately in memory.
- **Fail-Safe Invariant**: An empty query result or network timeout does NOT overwrite an existing valid cache.
- **Clear Diagnostic Logging**: The API logs distinct messages for:
  1. Connection failure (`Could not connect to hosted Neon DB`)
  2. Query exception (`Hosted Neon DB query failure: {e}`)
  3. Genuinely empty table (`Hosted Neon DB query returned 0 rows`)

---

## 6. Live Endpoint Verification Results

All endpoints were tested directly against the running server at `http://127.0.0.1:8000`:

| Endpoint | HTTP Status | Response Time | Actual Database-Derived Metrics |
| :--- | :---: | :---: | :--- |
| `GET /health` | **200 OK** | 2.990s | `db_status: CONNECTED`, `fare_observations_count: 9197` |
| `GET /api/v1/matrix` (1st Call) | **200 OK** | 0.039s | **342 populated cells**, **9,197 total observations** |
| `GET /api/v1/matrix` (2nd Call) | **200 OK** | **0.026s** | Cache reused in memory; zero database queries |
| `GET /api/v1/coverage` | **200 OK** | 0.009s | **342 / 360 target cells (95.0% coverage)**, **58 routes covered**, `valid_baseline: 9197` |
| `GET /api/v1/lead-curves?route=DEL-BOM` | **200 OK** | 0.005s | **199 quotes** on DEL-BOM, T+7 median fare: **₹6,843.00** |
| `GET /api/v1/airfare-index` | **200 OK** | 0.002s | Base index: `100.0000`, frequency: `monthly`, methodology: `AERIX v1.0` |
| `GET /api/v1/quality-metrics` | **200 OK** | 0.011s | **9,197 observations**, **58 routes**, **1,059 unique strata**, **3,238 unique itineraries** |
| `GET /api/observations?limit=2` | **200 OK** | 0.002s | Returned 2 records with 33 canonical keys; `collection_mode: Hosted Neon DB` |
| `GET /api/v1/backtest?mode=real` | **200 OK** | 0.025s | `backtest_type: REAL_DATA_VALIDATION`, 3 collection dates evaluated |
| `GET /api/methodology` | **200 OK** | 0.004s | `base_value: 100.0`, standard: `MoSPI CPI 2024 / Eurostat HICP Aligned` |

---

## 7. Actual Database-Derived Counts

| Metric | Value | Derivation Mode |
| :--- | :---: | :--- |
| Total Hosted Neon Observations | **9,197** | Dynamic query from `fare_observations` table |
| Unique Routes with Data | **58** | Dynamically extracted from valid origin-destination pairs |
| Populated Matrix Cells | **342** | Dynamically grouped across 58 routes $\times$ 6 lead times |
| Target Basket Cells | **360** | Top-60 city-pairs $\times$ 6 lead times (DGCA standard) |
| Basket Coverage Ratio | **95.0%** | $342 / 360 \times 100$ |
| Unique Derived Strata | **1,059** | Product strata ($Route \times Carrier \times Cabin \times LeadTime$) |
| Unique Derived Itineraries | **3,238** | Unique flight itineraries ($Sector \times Carrier \times FlightNo \times Date$) |
| Arbitrary Hardcoded Values | **0** | All counts are dynamically computed from live records |

---

## 8. Automated Test Suite Results

The entire backend test suite was run via `pytest tests/ -q`:

```
........................................................................ [ 38%]
........................................................................ [ 77%]
...........................................                              [100%]
187 passed, 98 warnings in 17.89s
```

- **Total Tests Passed**: **187 / 187** (100% Pass Rate)
- **Tests Failed**: **0**
- **Test Categories**:
  - API endpoint status and contracts (`tests/test_api_endpoints.py`)
  - Institutional governance, headers, and disclaimers (`tests/test_api_institutional_governance.py`)
  - MoSPI CY2024 expenditure weighting (`tests/core/test_cpi_2024_airfare_weight.py`)
  - Young-Laspeyres and Jevons econometric compilation (`tests/core/test_phase29_mospi_eurostat_engine.py`)
  - Tri-layer anti-contamination invariants (`tests/core/test_short_chain_jevons_governance.py`)

---

## 9. Non-Modification Confirmation

In accordance with strict safety invariants, we confirm:
- **Scraper code**: NOT modified (0 files changed in `apps/scraper/`).
- **Econometric and index mathematics**: NOT modified (Young-Laspeyres, Jevons geometric mean, and weighting formulas unchanged).
- **Production datasets**: NOT modified (`apix_compiled_index.json`, `easemytrip_normalized_data.json`, `backtest_results.json` unchanged).
- **DGCA volume weights**: NOT modified (`top60_passenger_volumes.json` and `WeightRegistry` untouched).
- **Frontend application**: NOT modified (All endpoint paths, query parameters, and response schemas remain fully backwards-compatible).
- **Database ingestion**: NOT modified (Neon schema, ingestion adapters, and pipeline unchanged).
