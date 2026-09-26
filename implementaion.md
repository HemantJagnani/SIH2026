# APIx: Indian Airfare Price Index — Implementation Plan

> **Methodological Standard:** MoSPI CPI 2024 Framework (COICOP 2018, Jevons Short-Chain Elementary Index, Young/Modified Laspeyres Higher-Level Aggregation) & Eurostat HICP Practical Web Scraping Guidelines.  
> **Reference Document:** [`APIx_Final_Index_Methodology_and_Antigravity_Implementation.md`](file:///c:/sih%202026/apix/APIx_Final_Index_Methodology_and_Antigravity_Implementation.md)  
> **Status:** Roadmap Frozen — Phased Execution on Demand.

---

## 🏛️ Executive Architecture & Calculation Hierarchy

The production engine does **not** average raw scraped ticket prices. It enforces the following statistical hierarchy:

```text
Scraped Raw Observations (EaseMyTrip / Ignav / Direct Airlines)
            ↓
Phase 1: Legal/Source Validation & Data Quality Gating
            ↓
Phase 2: Canonical Normalization & Product Fingerprinting (Itinerary + Offer)
            ↓
Phase 3: Stratification into Homogeneous Products
            ↓
         Within-Month Geometric Product Prices: P̄_(i,t) = exp(mean(ln P))
            ↓
         Matched Product Pairs across adjacent months: M_(s,t)
            ↓
         Short-Chain Jevons Elementary Indices: J_(s,t) = exp(mean(ln P_t - ln P_(t-1)))
            ↓
         Chained Elementary Indices: I_(s,t) = I_(s,t-1) × J_(s,t)
            ↓
         Lead-Time Weighted Aggregation (T+1, T+7, T+15, T+21, T+30, T+45)
            ↓
         Route-Weighted Aggregation (DGCA Passenger Shares / Route Expenditure)
            ↓
         All-India Airfare Price Index (APIx)
            ↓
Phase 4: API, Dashboard, 30-Day Backtest, Sensitivity Analysis & Test Suite
```

---

## 📋 Phase 1: Current Scraped Dataset Audit & Data Quality Assessment

### Objectives
Inspect the existing scraped datasets (`easemytrip_parsed_data.json`, `data/apix.db`, Ignav captures), audit every column, evaluate data completeness, detect anomalies, check lead-time coverage, and assess the feasibility of integrating the $T+21$ official MoSPI alignment checkpoint.

### Detailed Scope & Tasks
1. **Column & Schema Inspection:**
   - Enumerate and inspect every column across all source captures (EaseMyTrip JSON captures, database tables, raw payloads).
   - Verify presence of the 29 required product dimensions specified in Methodology §4.2:
     * Spatial/Temporal: `origin`, `destination`, `travel_date`, `day_of_week`, `search_timestamp_utc`, `lead_days`.
     * Flight/Itinerary: `airline`, `flight_number`, `departure_time`, `arrival_time`, `duration_minutes`, `stops`, `stopover_airports`, `requires_self_transfer`.
     * Fare Family & Cabin: `cabin_class`, `fare_family`, `fare_class`, `baggage_allowance`, `refundability`, `changeability`, `meal_included`.
     * Pricing: `base_fare`, `mandatory_taxes`, `airport_charges`, `mandatory_fees`, `total_fare`, `currency`.
     * Metadata/Provenance: `source`, `source_url`, `availability_status`, `source_itinerary_id`, `raw_evidence_uri`.
2. **Missing Field & Data Completeness Analysis:**
   - Identify missing fields in current scrapers (e.g. explicit tax breakdown vs total fare, baggage weights, refundability flags).
   - Document explicit fallback rules: if base/tax split is not exposed by the source, store `total_fare` and mark components as `NULL` (never manufacture artificial splits).
3. **Null & Duplicate Rate Quantification:**
   - Calculate percentage of nulls/missing values per column.
   - Detect duplicate records:
     * Physical duplicates (identical rows).
     * Exact offer duplicates (same flight, same fare, scraped across different runs or sources).
     * Cross-source replicates (same flight on direct airline vs OTA).
4. **Source-Specific Discrepancy Analysis:**
   - Compare schema and data behavior between EaseMyTrip vs Ignav vs Direct feeds.
   - Document timestamp timezone handling (UTC vs IST `departure_time_local`).
5. **Lead-Time Window Support Verification:**
   - Calculate empirical lead days: $\text{LeadDays} = \text{TravelDate} - \text{SearchDate}$.
   - Check data presence for standard lead-time windows:
     * $T+1$ (1 day advance)
     * $T+7$ (7 days advance)
     * $T+15$ (15 days advance)
     * $T+30$ (30 days advance)
     * $T+45$ (45 days advance)
6. **Feasibility of Adding $T+21$ Checkpoint:**
   - Assess whether current scrape schedules or existing historical captures support $T+21$ (the official MoSPI CPI 2024 domestic advance-purchase checkpoint).
   - Outline search scheduler parameters needed to collect $T+21$ as a distinct first-class stratum.
7. **Deliverable:**
   - Generate `DATA_QUALITY_REPORT.md` with summary statistics, completeness matrices, distribution plots, and actionable ingestion recommendations.

---

## 🏛️ Phase 2: Canonical Data Models & Fingerprinting Engine

### Objectives
Implement the formal data layer ensuring immutable audit trails, high-precision monetary storage (`Decimal`), standardized product stratification, and deterministic deduplication fingerprints.

### Detailed Scope & Tasks
1. **Canonical Model Implementations:**
   - `RawFareObservation`:
     * Immutable storage of verbatim raw scraped JSON/HTML payloads.
     * Contains `observation_id` (UUID), `collection_run_id`, `source`, `source_url`, `search_timestamp_utc`, `search_timestamp_local`, and `raw_evidence_uri`.
   - `NormalizedFareObservation`:
     * Cleaned canonical entity.
     * Uses `Decimal` (`NUMERIC(10,2)`) for `base_fare`, `taxes`, `airport_charges`, `mandatory_fees`, and `total_fare`.
     * Strict validation: `currency == 'INR'`, `total_fare > 0`.
     * Normalizes categorical fields: `cabin_class` (ECONOMY, PREMIUM_ECONOMY, BUSINESS), `stops` (0, 1, 2+), `departure_time_band` (EARLY_MORNING, MORNING, AFTERNOON, EVENING, NIGHT).
     * Assigns `quality_status`: `VALID`, `SOLD_OUT`, `INVALID_PRICE`, `DUPLICATE`, `OUTLIER_REVIEW`, `QUARANTINED`.
2. **Product Stratification Engine (`ProductStratum`):**
   - Implements homogeneous comparable product identity:
     $$\text{Stratum ID} = \text{hash}(\text{origin}, \text{destination}, \text{travel\_day\_type}, \text{departure\_time\_band}, \text{cabin}, \text{fare\_family\_group}, \text{baggage\_group}, \text{stop\_category}, \text{passenger\_type}, \text{lead\_time\_class})$$
   - Prevents flight number instability from corrupting long-term product comparability.
3. **Deduplication & Fingerprint Engines:**
   - `ItineraryFingerprint`:
     $$F_{\text{itinerary}} = \text{hash}(\text{origin}, \text{destination}, \text{travel\_date}, \text{airline}, \text{flight\_number}, \text{departure\_time\_local}, \text{arrival\_time\_local}, \text{stops})$$
   - `OfferFingerprint`:
     $$F_{\text{offer}} = \text{hash}(F_{\text{itinerary}}, \text{fare\_family}, \text{cabin}, \text{baggage\_allowance}, \text{refundability}, \text{changeability})$$
   - Non-destructive deduplication: assigns `duplicate_group_id` without deleting underlying raw evidence.
4. **Outlier Quarantine Rules:**
   - Statistical outlier flagging via robust Median Absolute Deviation (MAD):
     $$z_i = \frac{\ln P_i - \text{median}(\ln P)}{1.4826 \times \text{MAD}(\ln P)}$$
   - Flags $|z_i| > 3.5$ for manual/quality review while preserving valid festival/peak surges.
5. **Deliverables:**
   - Python domain classes & SQLAlchemy models in `apps/scraper/src/models/` and `storage/`.
   - Alembic database migration scripts.
   - Comprehensive unit test suite for normalization and fingerprint generation.

---

## 🧮 Phase 3: Statistical Index Compilation Engine

### Objectives
Build the complete MoSPI CPI 2024 / Eurostat HICP compliant index compilation engine, featuring monthly geometric product pricing, matched-pair short-chain Jevons elementary indexing, and multi-tier weighted aggregations.

### Detailed Scope & Tasks
1. **Monthly Product Pricing (`monthly_product_prices`):**
   - For each homogeneous product $i$ in month $t$, calculate the geometric mean of valid daily observations:
     $$\bar{P}_{i,t} = \exp\left( \frac{1}{D_{i,t}} \sum_{d=1}^{D_{i,t}} \ln P_{i,t,d} \right)$$
   - Log formulation ensures numerical stability and zero floating-point accumulation drift.
   - Stores `product_id`, `month`, `geometric_price`, `observation_count`, `active_days`, and `quality_status`.
2. **Product Matching Engine (`matching engine`):**
   - Identifies the matched set $M_{s,t}$ of products existing in both period $t-1$ and period $t$ with strictly comparable specifications.
   - Quality control threshold enforcement:
     * Minimum matched products per stratum: $N_{s,t} \ge 5$.
     * Minimum coverage ratio: $\text{Coverage}_{s,t} = \frac{N_{\text{matched},s,t}}{N_{\text{eligible},s,t-1}} \ge 50\%$.
   - Replacement protocol: If an offer disappears, match against an equivalent offer in the identical stratum, logging the replacement.
3. **Elementary Index Engine (`Jevons engine`):**
   - Computes the unweighted geometric price relative link:
     $$J_{s,t} = \exp\left( \frac{1}{N_{s,t}} \sum_{i \in M_{s,t}} [\ln \bar{P}_{i,t} - \ln \bar{P}_{i,t-1}] \right)$$
   - Short-chain recursive multiplication:
     $$I_{s,t} = I_{s,t-1} \times J_{s,t} \quad \text{with} \quad I_{s,0} = 100$$
4. **Lead-Time Aggregation:**
   - Aggregates elementary indices across lead-time classes $l \in \{1, 7, 15, 21, 30, 45\}$ using booking-distribution weights $W_l$:
     $$I_{r,t} = \sum_{l} W_l \cdot I_{r,l,t} \quad \text{subject to} \quad \sum_{l} W_l = 1$$
   - $T+21$ is tracked as an independent alignment series.
5. **Route Aggregation:**
   - Aggregates route-level indices across India's domestic network using DGCA passenger traffic shares $W_r$:
     $$\text{APIx}_t = \sum_{r} W_r \cdot I_{r,t} \quad \text{subject to} \quad \sum_{r} W_r = 1$$
   - Secondary expenditure weighting variant: $E_r = \text{Passengers}_r \times \bar{P}_r$.
6. **Multi-Frequency Output Series:**
   - **Monthly CPI-Compatible APIx:** Primary series aligned with official MoSPI monthly release cycles.
   - **Daily & Weekly Market Indicators:** High-frequency rolling Jevons indicators for market monitoring.
   - **Inflation Metrics:** Month-on-Month ($\text{MoM}_t = (\frac{I_t}{I_{t-1}} - 1) \times 100$) and Year-on-Year ($\text{YoY}_t$).
7. **Deliverables:**
   - Core index compilation module in `src/apix/index_math/` and `apps/scraper/src/index/`.
   - Comprehensive test fixtures verifying mathematical identity properties.

---

## 🚀 Phase 4: Production Integration, API, Dashboard & Validation

### Objectives
Expose index series via high-performance REST APIs, build modern dashboard visualizations, execute a 30-day historical backtest, run multi-variant sensitivity analyses, and automate acceptance testing.

### Detailed Scope & Tasks
1. **FastAPI Endpoints (`apps/api/src/`):**
   - `GET /api/v1/airfare-index`:
     * Parameters: `from_date`, `to_date`, `frequency` (monthly, weekly, daily), `route`, `lead_time`.
     * Response payload includes: `index_name`, `reference_period`, `period`, `index_value`, `mom_percent`, `yoy_percent`, `methodology_version` (`APIx v1.0`), `weight_version`.
   - `GET /api/v1/quality-metrics`:
     * Returns null rates, duplicate counts, matched product counts, and coverage ratios.
2. **Dashboard Modernization (`web/`):**
   - **KPI Executive Cards:** Current APIx level, MoM inflation %, YoY inflation %, active route count.
   - **Lead-Time Yield Curves:** Interactive Chart.js visualization of fare curves across $T+1, T+7, T+15, T+21, T+30, T+45$.
   - **Route Heatmap:** Matrix of Origin vs Destination showing latest index and monthly price changes.
   - **Diagnostic & Source Quality View:** Real-time visibility into scraper health, capture volumes, and matched sample percentages.
3. **30-Day Historical Backtest:**
   - Execute the end-to-end pipeline across a 30-day historical window.
   - Compare APIx trajectory against benchmark market indicators.
   - Measure Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE).
4. **Sensitivity & Robustness Analysis:**
   - Compute and report 4 parallel weighting variants:
     * **Variant A:** DGCA passenger-share route weights ($W_r^{\text{DGCA}}$).
     * **Variant B:** Fare-adjusted route expenditure weights ($W_r^{\text{Fare}}$).
     * **Variant C:** Equal route weights ($W_r = 1/R$).
     * **Variant D:** Equal lead-time weights ($W_l = 1/L$).
   - Document index divergence across variants to quantify weight sensitivity.
5. **Antigravity Mandatory Acceptance Tests Suite:**
   - [x] **Test 1 (Price Invariance):** All matched prices unchanged $\implies J_{s,t} = 1.0000$.
   - [x] **Test 2 (Scale Invariance / Inflation):** All prices increase by 10% $\implies J_{s,t} = 1.1000$.
   - [x] **Test 3 (Chain Consistency):** $I_{s,t} = I_{s,t-1} \times J_{s,t}$ exactly holds.
   - [x] **Test 4 (Weight Unity):** $\sum W_r = 1.0$ and $\sum W_l = 1.0$ across all aggregation levels.
   - [x] **Test 5 (Duplicate Invariance):** Ingesting duplicate scraped rows produces zero change in index value.
   - [x] **Test 6 (T+21 Isolation):** $T+21$ is scheduled, stored, and aggregated as an independent stratum.
   - [x] **Test 7 (Zero-Price Handling):** Missing/sold-out flights never enter logs as zero.
   - [x] **Test 8 (Audit Metadata):** Every published index record records `data_version`, `weight_version`, and `methodology_version`.
6. **Deliverables:**
   - Production FastAPI endpoints with full OpenAPI documentation.
   - Responsive web dashboard with Chart.js charts.
   - Backtest & Sensitivity report (`BACKTEST_REPORT.md`).
   - Automated Pytest test suite enforcing all acceptance gates.

---

## 🔒 Non-Negotiable Methodological Rules

1. **Never average raw scraped rows directly.**
2. **Never use scraper row count as a market weight.**
3. **Never treat sold-out or missing flights as ₹0.**
4. **Never manufacture artificial base-fare vs tax splits.**
5. **Never use flight number alone as product identity.**
6. **Never discard genuine market price surges during peak/festival events.**
7. **Always store raw verbatim payloads for auditability.**
8. **Always use high-precision Decimal math for monetary computations.**
9. **Always version weights and methodology explicitly.**
10. **Maintain $T+21$ as an independent MoSPI CPI 2024 alignment stratum alongside $T+1, T+7, T+15, T+30, T+45$.**
