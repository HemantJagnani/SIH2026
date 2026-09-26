# APIx Phase 1: Data Quality & Dataset Audit Report

> **Project:** Real-time Indian Airfare Price Index (APIx)  
> **Methodological Standard:** MoSPI CPI 2024 Framework & Eurostat HICP Practical Web Scraping Guidelines  
> **Audit Date:** 2026-09-25  
> **Audited Datasets:**  
> 1. `easemytrip_parsed_data.json` (145 scraped flight records)  
> 2. `tests/fixtures/easemytrip/del_bom_results.html` (9.6 MB raw DOM capture)  
> 3. `apps/scraper/tests/adapters/ignav_raw_fixture.json` (54 flight itineraries)

---

## 1. Executive Summary

This report delivers the complete **Phase 1 Data Quality Audit** mandated by the project methodology. We conducted a deep audit across all available datasets, evaluated column schemas against the 29 canonical product dimensions in Methodology §4.2, quantified null/duplicate rates, analyzed source differences between EaseMyTrip and Ignav, verified lead-time window coverage ($T+1, T+7, T+15, T+30, T+45$), and evaluated the feasibility of integrating the official MoSPI CPI 2024 domestic advance-purchase checkpoint ($T+21$).

### Key Findings
1. **Core Data Quality:** All prices in `easemytrip_parsed_data.json` are valid Indian Rupee (`INR`) amounts ranging between **₹6,529** and **₹25,778** (mean: **₹9,398.79**), capturing genuine market price distribution across 5 major domestic carriers. Zero negative or zero-value fares were found.
2. **Critical Discovery on Flight Timings:** In `easemytrip_parsed_data.json`, `departure_time_local` and `arrival_time_local` were reported as 100% null. Our direct inspection of the underlying raw DOM fixture (`del_bom_results.html`) confirmed that departure times, arrival times, and durations **are 100% present in the HTML** (e.g. `.tm_lc.texrgt h4` and `.tmln_rc`). The existing parser simply missed extracting them. We verified that **145 out of 145 cards (100.0%)** have extractable times.
3. **Component Breakdown (Base vs Tax):** As expected for OTA web scraping, EaseMyTrip exposes only the total payable consumer fare. Explicit splits for `base_fare` and `taxes` are absent. In strict adherence to **Methodology Rule 5 and §6.2**, the pipeline correctly stores `total_fare` and keeps `base_fare = NULL` and `taxes = NULL` rather than manufacturing artificial splits.
4. **Lead-Time Window Support:** The current `easemytrip_parsed_data.json` contains exclusively $T+7$ observations (search date: 2026-09-22, travel date: 2026-09-29). The other lead-time windows ($T+1, T+15, T+30, T+45$) require multi-window collection runs.
5. **Feasibility of $T+21$:** Adding $T+21$ is **fully supported** by the scraper architecture and request models. The scheduler can immediately add $T+21$ as an independent first-class stratum to satisfy MoSPI CPI 2024 alignment.

---

## 2. Column-by-Column Inventory & Null Analysis

Dataset: `easemytrip_parsed_data.json` (Total Rows: 145)

| Field Name | Type | Status | Null Count | Null % | Methodological Role / Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `observation_id` | UUID | Populated | 0 | 0.0% | Unique record identifier (UUIDv4) |
| `collection_run_id` | UUID | Populated | 0 | 0.0% | Batch run grouping identifier |
| `source` | string | Populated | 0 | 0.0% | Source outlet (`easemytrip`) |
| `source_offer_id` | string | Populated | 0 | 0.0% | Formatted as `emt-{flight}-{fare}` |
| `collected_at` | datetime | Populated | 0 | 0.0% | Collection UTC timestamp |
| `search_timestamp` | datetime | Populated | 0 | 0.0% | Search initiation UTC timestamp |
| `travel_date` | string | Populated | 0 | 0.0% | Flight date (`2026-09-29`) |
| `lead_days` | integer | Populated | 0 | 0.0% | Advance purchase window (7 days) |
| `origin` | string | Populated | 0 | 0.0% | IATA origin airport (`DEL`) |
| `destination` | string | Populated | 0 | 0.0% | IATA destination airport (`BOM`) |
| `airline` | string | Populated | 0 | 0.0% | Airline marketing name |
| `flight_number` | string | Populated | 0 | 0.0% | Flight number (e.g. `6E-2054`, `AI-1745`) |
| `trip_type` | string | Populated | 0 | 0.0% | Standardized as `ONE_WAY` |
| `cabin` | string | Populated | 0 | 0.0% | Standardized as `ECONOMY` |
| `passenger_count` | integer | Populated | 0 | 0.0% | Standardized as `1` adult |
| `stops` | integer | Partial | 59 | 40.7% | 86 records have stops (1 stop); 59 null |
| `total_fare` | string | Populated | 0 | 0.0% | Consumer payable fare (₹6,529 to ₹25,778) |
| `currency` | string | Populated | 0 | 0.0% | All `INR` |
| `availability` | string | Populated | 0 | 0.0% | Standardized as `AVAILABLE` |
| `adapter_version` | string | Populated | 0 | 0.0% | Tracking version `1.0.0` |
| `normalizer_version`| string | Populated | 0 | 0.0% | Tracking version `1.0.0` |
| `schema_version` | string | Populated | 0 | 0.0% | Tracking version `1.1.0` |
| `departure_time_local` | datetime | **Missing** | 145 | 100.0% | **Recoverable from raw HTML DOM fixture** |
| `arrival_time_local` | datetime | **Missing** | 145 | 100.0% | **Recoverable from raw HTML DOM fixture** |
| `departure_time_utc` | datetime | Missing | 145 | 100.0% | Can be derived from local + Asia/Kolkata TZ |
| `arrival_time_utc` | datetime | Missing | 145 | 100.0% | Can be derived from local + Asia/Kolkata TZ |
| `airline_code` | string | Missing | 145 | 100.0% | Derivable from flight number prefix (`6E`, `AI`, `IX`) |
| `base_fare` | decimal | Missing | 145 | 100.0% | Not exposed by EaseMyTrip summary card |
| `taxes` | decimal | Missing | 145 | 100.0% | Not exposed by EaseMyTrip summary card |
| `fees` | decimal | Missing | 145 | 100.0% | Not exposed by EaseMyTrip summary card |
| `airport_charges` | decimal | Missing | 145 | 100.0% | Not exposed by EaseMyTrip summary card |
| `convenience_fee` | decimal | Missing | 145 | 100.0% | Omitted until booking checkout screen |
| `discount` | decimal | Missing | 145 | 100.0% | Optional promo coupons |
| `fare_family` | string | Missing | 145 | 100.0% | Exists in modal/sub-tier, not main listing |
| `fare_class` | string | Missing | 145 | 100.0% | Booking code (Y, B, M) not in consumer DOM |
| `requires_self_transfer` | boolean | Missing | 145 | 100.0% | Present in Ignav, null in EMT summary |
| `price_status` | string | Missing | 145 | 100.0% | Verification status |
| `source_itinerary_id` | string | Missing | 145 | 100.0% | Internal aggregator ID |
| `source_url` | string | Missing | 145 | 100.0% | Audit crawl URL |
| `raw_evidence_uri` | string | Missing | 145 | 100.0% | S3/Local snapshot pointer |
| `raw_value_reference`| string | Missing | 145 | 100.0% | Diagnostic pointer |

---

## 3. Duplicate Rate Quantification

We evaluated duplicate rates across two dimensions:

1. **Physical Duplicates (Exact JSON Identity):**
   - Total Records: 145
   - Exact Duplicate Rows: **0 (0.0%)**
   - The parser produces clean, non-replicated physical records.

2. **Offer Replicates (Same Flight, Date, Route, and Price):**
   - Matching key: `(origin, destination, travel_date, airline, flight_number, total_fare)`
   - Unique Flight-Fare Offers: 142
   - Offer Duplicates: **3 (2.07%)**
   - Cause: Certain flights appeared twice in the search results with different connection/sub-tier tags on the website. In Phase 2, the `ItineraryFingerprint` and `OfferFingerprint` engines will formally tag these with `duplicate_group_id` without destructive data loss.

---

## 4. Source-Specific Differences: EaseMyTrip vs. Ignav

| Dimension | EaseMyTrip (Live Web Scraper) | Ignav API (Direct Data Feed) | Methodological Impact |
| :--- | :--- | :--- | :--- |
| **Collection Method** | Playwright Headless Browser / DOM Scraping | Structured REST API JSON | Web scraping captures actual consumer-facing OTA display; API captures GDS/aggregator feed. |
| **Price Breakdown** | Single all-inclusive `total_fare` only | Structured fare with `amount`, `currency`, `status` | Base vs tax breakdown not available on OTA list page; total fare is the required CPI price. |
| **Flight Timings** | Present in DOM (`.tm_lc h4`), omitted by current parser | Formatted ISO UTC & Local timestamps in `segments` | EaseMyTrip parser must be updated in Phase 2 to capture DOM departure/arrival times. |
| **Stops & Segments** | Summary stop count (`Non Stop`, `1 Stop`) | Detailed segments with operating carrier & flight number | Ignav provides multi-segment visibility; EMT summary gives total flight duration and stop count. |
| **Airline Coverage** | IndiGo (70), Air India (45), AI Express (18), Akasa Air (10), SpiceJet (2) | Air India (20), IndiGo (21), Akasa Air (9), SpiceJet (2), AI Express (2) | High carrier diversity across all major domestic airlines in both sources. |
| **Price Level (DEL→BOM, T+7)** | Min: ₹6,529, Max: ₹25,778, Mean: ₹9,398.79 | Min: ₹6,314, Max: ₹10,868, Mean: ₹6,826.61 | EaseMyTrip includes high-fare connecting flights and peak slots; Ignav fixture contains nonstop verified baseline fares. |

---

## 5. Lead-Time Window Verification ($T+1, T+7, T+15, T+30, T+45$)

The project methodology requires tracking advance-purchase price dynamics across 5 standard lead-time windows:

$$\text{LeadDays} = \text{TravelDate} - \text{SearchDate}$$

| Lead Time | Required by Methodology | Present in `easemytrip_parsed_data.json` | Status & Recovery Action |
| :---: | :---: | :---: | :--- |
| **$T+1$** | Yes (1 day advance) | ❌ Absent | Must be collected via scheduler: $\text{TravelDate} = \text{SearchDate} + 1$ |
| **$T+7$** | Yes (7 days advance) | ✅ **145 records (100%)** | Fully populated (Search: 2026-09-22, Travel: 2026-09-29) |
| **$T+15$** | Yes (15 days advance) | ❌ Absent | Must be collected via scheduler: $\text{TravelDate} = \text{SearchDate} + 15$ |
| **$T+30$** | Yes (30 days advance) | ❌ Absent | Must be collected via scheduler: $\text{TravelDate} = \text{SearchDate} + 30$ |
| **$T+45$** | Yes (45 days advance) | ❌ Absent | Must be collected via scheduler: $\text{TravelDate} = \text{SearchDate} + 45$ |

> [!NOTE]
> Historical booking prices cannot be scraped backwards in time from live airline websites because past travel dates are removed from booking engines once flown. For backtesting, we utilize the real scraped $T+7$ price distributions anchored to real data points, combined with forward daily scheduled collections.

---

## 6. Feasibility of Adding Official MoSPI Checkpoint ($T+21$)

### Context
Under MoSPI's official **CPI 2024 Expert Group** methodology for the modern Consumer Price Index revision, domestic airfare collection is explicitly indexed to a **21-day advance purchase window** ($T+21$).

### Feasibility Assessment: **100% FEASIBLE**
1. **Architectural Readiness:** The scraper's `FareSearchRequest` model in `apps/scraper/src/models/request.py` accepts an arbitrary `lead_days: int` argument.
2. **Implementation Path:**
   - Add `21` to the standard collection matrix: `LEAD_TIMES = [1, 7, 15, 21, 30, 45]`.
   - Store $T+21$ as an independent, first-class stratum throughout:
     * Database schema (`lead_days = 21`).
     * `ProductStratum` composite key.
     * Lead-time weighting tables.
3. **Methodological Isolation:** As required by Methodology §10A, $T+21$ will be retained as an independent reportable series and will **not** be blended into $T+15$ or $T+30$.

---

## 7. Actionable Recommendations for Phase 2

1. **Upgrade EaseMyTrip Parser:** Update `apps/scraper/src/sources/easemytrip/parser.py` to extract `departure_time_local`, `arrival_time_local`, and `duration_minutes` directly from `.tm_lc h4` and `.tmln_rc`, eliminating the current 100% null rate for timings.
2. **Implement Canonical Models:**
   - `RawFareObservation`: Capture verbatim responses with snapshot references.
   - `NormalizedFareObservation`: Enforce `Decimal` monetary fields, strict INR validation, and `quality_status` tagging.
3. **Activate Fingerprints:** Implement `ItineraryFingerprint` and `OfferFingerprint` to flag the 2.07% replicate offers without deleting raw evidence.
4. **Deploy Lead-Time Sampling Frame:** Configure the orchestrator for all 6 target windows: $T+1, T+7, T+15, T+21, T+30, T+45$.
