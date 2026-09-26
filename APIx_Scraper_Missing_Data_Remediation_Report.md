# APIx Scraper Missing-Data Remediation Report

## Purpose

This report converts the current Phase 1 data-quality findings into an implementation plan for closing the missing-data links in the airfare scraper. The objective is **not to manufacture the missing fields**, but to modify the scraper so that fields genuinely exposed by the source are captured, fields that are deterministically derivable are calculated transparently, and fields that are not exposed remain explicitly `NULL/UNKNOWN`. The remediation preserves the APIx methodology: total consumer-payable price is the primary price concept, product comparability must be maintained, and raw observations must remain auditable.

## 1. Current Situation

The current scraper has 29 product dimensions defined by the APIx methodology. The Phase 1 audit reports:

- **14/29 fully extracted**
- **6/29 defaulted or inferred**
- **9/29 currently missing/absent**

The current live DOM validation is based on EaseMyTrip's DEL-BOM results. The existing capture successfully extracts core flight-card fields such as route, travel date, search timestamp, airline, flight number, departure/arrival, duration, stops, total displayed fare, currency and availability.

The main gaps are caused by information being hidden behind interactive flight-detail panels, fare-family controls, fare-rule modals, fare-breakup tooltips and later booking/review stages. The live collection is also incomplete because the validated raw DOM scrape is currently only **DEL-BOM at T+7**, even though the database and index engine support the required lead times and routes.

## 2. Critical Correction: Remove Unsafe Defaults

Before adding extraction logic, remove defaults that can create false product specifications:

| Field | Current behavior | Required behavior |
|---|---|---|
| Cabin | `ECONOMY` default | Use request/specification as a sampling condition; otherwise source value or `UNKNOWN` |
| Passenger type | `ADULT` default | Use request/specification; record as collection condition |
| Travel-day type | inferred | Keep deterministic derivation from travel date/calendar |
| Departure band | inferred | Keep deterministic derivation from departure time |
| Fare family | `STANDARD` default | **Do not default**; actual family or `UNKNOWN` |
| Baggage | `STANDARD` default | **Do not default**; actual entitlement or `UNKNOWN` |
| Refundability | `UNKNOWN` | Keep unknown until source evidence exists |
| Base/tax split | null | Keep null unless explicitly extracted |
| Convenience fee | zero/omitted | `NULL` when not observable; never silently zero |

A deterministic value such as `WEEKDAY` is not equivalent to an assumption such as “15 kg baggage”. Assumed product characteristics can contaminate product matching and quality adjustment.

## 3. Remediation Priority

### Priority 0 — Statistical safety and auditability

1. Replace unsafe defaults with explicit `UNKNOWN`/`NULL`.
2. Add source evidence capture for every successful collection run.
3. Preserve raw price text and price-status classification.
4. Store parser/navigation version with every observation.
5. Add field-level extraction diagnostics and missingness rates.
6. Add collection-run completeness checks for route × lead-time × date combinations.

### Priority 1 — High-value product specification

1. Baggage entitlement.
2. Fare family / fare bundle.
3. Refundability and changeability.
4. Segment-level itinerary details.
5. Mandatory final payable price / checkout fee reconciliation.

### Priority 2 — Analytical enrichment

1. Fare breakup components.
2. Seat-inventory/scarcity indicators.
3. Fare basis / booking class when technically and legally exposed.

These enrich the dataset but are not all required for the core APIx index.

### Priority 3 — Coverage expansion

**Lead times:** T+1, T+7, T+15, T+21, T+30, T+45.

**Routes:** DEL-BOM, DEL-BLR, BOM-BLR, DEL-CCU, BLR-HYD, DEL-HYD, BOM-GOI, DEL-MAA, BOM-CCU, BLR-CCU.

The existing DEL-BOM/T+7 result should be treated as a validated scraper fixture, not the completed production sampling frame.

## 4. Field-by-Field Fix Plan

### 4.1 Baggage entitlement

**Gap:** kg allowance is hidden behind the flight-details interaction.

**Fix:** For each selected flight card, locate the flight-details control using semantic/structural selectors; open it; extract cabin baggage kg, check-in baggage kg, explicit no-baggage conditions and raw text; normalize to `cabin_baggage_kg`, `checkin_baggage_kg`, `baggage_group`, and `baggage_raw_text`; close the panel before the next card; use bounded timeout/retry handling.

**Rule:** Never assign 15 kg/7 kg unless the source explicitly reports it for that offer.

**Acceptance test:** A fixture with a known baggage panel must reproduce the displayed entitlement exactly.

### 4.2 Fare family / fare bundle

**Gap:** The primary card price is captured, but the complete fare ladder is not.

**Fix:** Detect the card-specific “View Fares”/fare-family control; open the modal; extract each displayed fare option, including family name, price, baggage, seat, meal, refundability and changeability where shown; assign an `offer_id` to each option; do not collapse distinct fare families into one observation.

**Statistical rule:** Fare-family variants are different product offers unless the methodology explicitly defines them as one homogeneous product. Do not silently average them.

### 4.3 Refundability and changeability

**Gap:** Currently `UNKNOWN`; rules are reportedly exposed through fare-rule interactions.

**Fix:** Open the fare-rule control associated with the selected offer and capture refund status, cancellation fee, change fee, restrictions, no-show conditions and raw fare-rule text. Normalize status to `NON_REFUNDABLE`, `REFUNDABLE_WITH_FEE`, `REFUNDABLE`, or `UNKNOWN`. Do not infer status from fare-family names.

### 4.4 Base fare, taxes and airport charges

**Gap:** Total fare is captured but components are not.

**Fix:** Capture fare-breakup UI only when explicitly available; extract base fare, taxes, GST/K3, UDF/ADF, security fee and other mandatory charges; validate that components reconcile to displayed total within documented rounding tolerance; create a `FARE_BREAKUP_MISMATCH` quality event if they do not reconcile. If only total is shown, leave components null.

**Index rule:** The APIx index uses the correctly defined consumer-payable total. Never synthetically allocate taxes or fees.

### 4.5 Convenience / payment gateway fee

**Gap:** Mandatory OTA fees may appear only later in the booking flow.

**Fix:** Determine whether the fee is mandatory for the representative consumer transaction, payment-method specific, optional, or not observable. Capture a fee only when it is clearly required under the defined collection conditions. Store `convenience_fee`, `fee_status`, `fee_payment_method`, and `fee_raw_text`. Do not add a commonly observed fee and do not convert missing to zero.

### 4.6 Intermediate stopover and segment details

**Gap:** Main cards expose stop count and total duration but not all legs.

**Fix:** Open the itinerary/details panel and extract an ordered segment array: segment number, origin, destination, flight number, operating carrier, departure, arrival and duration. Derive `stops = number_of_segments - 1`. Store connecting segments in a child `flight_segments` table rather than adding unlimited stopover columns.

Recommended model:

```text
fare_observations = one offer-level record
flight_segments   = one-to-many segment records linked by observation_id
```

### 4.7 Seat inventory / scarcity

**Gap:** Explicit scarcity badges are ignored.

**Fix:** Detect text such as “X seats left”; store `seats_remaining_displayed`, `inventory_status`, and `inventory_raw_text`. Absence of a badge does not mean high availability. Inventory must not become an APIx weight.

### 4.8 Fare basis / booking class

**Gap:** Usually not exposed on public OTA cards.

**Fix:** Inspect permitted page/network responses for an explicit booking-class/fare-basis field. If openly available and permitted, capture it. Otherwise leave null. Do not bypass protected interfaces to obtain internal CRS/GDS data; this is low-priority enrichment.

### 4.9 Raw evidence snapshot

**Gap:** `raw_evidence_uri` is absent.

**Fix:** For every production collection, save rendered HTML, results screenshot, screenshots/HTML of opened detail modals when used, raw price text, source URL, timestamp, parser version, navigation version and adapter version.

Suggested structure:

```text
evidence/
  YYYY-MM-DD/
    run_<run_id>/
      <source>/
        <route>/
          T+<lead>/
            results.html
            results.png
            card_<id>/
              details.html
              details.png
              fare_breakup.html
              fare_rules.html
```

Never overwrite previous evidence.

## 5. Scraper Architecture Change

Do not turn the scraper into one large click sequence. Use a reusable workflow:

```text
Search request
  ↓
Results page
  ↓
Extract core flight card
  ↓
Identify canonical flight/offer
  ↓
Optional detail expansion
  ├── baggage
  ├── segments
  ├── fare family
  ├── fare rules
  ├── fare breakup
  └── inventory
  ↓
RawFareObservation + child segment/offer records
  ↓
Common validation → normalization → quality → fingerprints/dedupe
  ↓
Product classification → APIx
```

Each optional expansion must have a timeout, retry limit, success/failure state, evidence capture and diagnostics so a failed modal does not stop the entire run.

## 6. Extraction Modes

Use configurable policies:

```text
CORE_ONLY
CORE + DETAILS
CORE + DETAILS + FARE_RULES
FULL_AUDIT
```

Production APIx collection should use the minimum extraction needed to define the representative product consistently. Periodic `FULL_AUDIT` runs can measure missingness and verify conditions without clicking every modal on every flight on every run.

## 7. Multi-Lead-Time and Multi-Route Collection

The current live data is only DEL-BOM at T+7. Implement a route × lead-time collection matrix:

```text
10 routes × 6 lead times = 60 search combinations per collection cycle
```

For each combination store:

```text
collection_run_id
route
origin
destination
travel_date
lead_days
search_timestamp
requested
started
completed
results_count
valid_observations
sold_out_count
captcha_count
blocked_count
parser_error_count
```

A run is not complete merely because a browser returned a page. Completeness must be checked against the expected matrix.

## 8. Quality Gates

### Core completeness

Required: origin, destination, travel date, search timestamp, airline, flight identity, departure, arrival, stops, total fare, INR currency and availability.

### Product-definition completeness

For the selected representative product, fare family must not be silently defaulted; baggage must be known or explicitly unknown; cabin and passenger type must come from the request/specification or source; stop category and lead time must be known.

### Monetary consistency

Total fare must be positive; currency valid; no negative component; if components exist, they must reconcile to total within tolerance; optional fees must not be accidentally included.

### Comparability

Product matching must use the agreed specification: route, travel-day type, departure-time band, cabin, fare family, baggage, stop category, passenger type and lead-time class. Do not match products merely because airline and flight number are identical.

### Evidence

Every production observation must be traceable to source URL, collection timestamp, raw evidence and parser version.

## 9. Diagnostics Dashboard

Calculate field coverage as:

```text
field_coverage_rate = non_null_valid_values / total_observations
```

Report by source, route, lead-time, airline and collection run. The report should show actual live values for baggage, fare family, refundability, fare breakup, stopover, scarcity, fare basis and evidence. Example percentages must never be hard-coded.

## 10. Definition of Done

1. No unsafe product-field defaults remain.
2. Baggage is extracted where exposed and otherwise explicitly unknown.
3. Fare families are represented as distinct offers where exposed.
4. Refundability/changeability are captured where exposed.
5. Fare breakup is captured where exposed without synthetic allocation.
6. Mandatory final consumer price is clearly defined and captured.
7. Segment details are available for connecting flights where exposed.
8. Scarcity information is captured when explicitly displayed.
9. Fare basis is captured only if openly available/permitted; otherwise null.
10. Raw evidence is stored for every production observation.
11. All six lead times are actually crawled.
12. All ten target routes are actually crawled.
13. Collection completeness is measured by route × lead-time matrix.
14. Parser diagnostics are stored.
15. Fixtures and regression tests cover all new modal/tooltip states.
16. APIx consumes only observations passing the common validation/quality pipeline.
17. No CAPTCHA, access-control or anti-bot bypass is introduced.

## 11. Recommended Antigravity Implementation Order

**Phase A — Safety correction:** remove unsafe defaults; add explicit `UNKNOWN/NULL`; add evidence/version fields; add diagnostics.

**Phase B — Detail extraction:** implement details panel; baggage; segments; fare family; fare rules; fare breakup; scarcity.

**Phase C — Coverage:** parameterize six lead times; parameterize ten routes; build route × lead-time orchestration; add completeness checks.

**Phase D — Validation:** add fixtures; run integration tests on DEL-BOM; execute one controlled full-audit collection; compare field coverage before/after; only then enable recurring broader collection.

## 12. Antigravity Instruction

Before modifying code, inspect the existing EaseMyTrip adapter, canonical `FareSearchRequest`/`RawFareObservation` schema, database models, collection orchestrator, evidence system, parser utilities and tests. Reuse the existing architecture rather than creating parallel schemas. Implement missing fields incrementally, beginning with removal of unsafe defaults and evidence capture, then details/modals, then coverage orchestration. Use Playwright for permitted rendered-page interactions, but do not implement CAPTCHA bypass, anti-bot evasion, fingerprint spoofing for evasion, or proxy rotation intended to circumvent blocks. When a protection challenge or access block appears, record the state and evidence and stop or follow the repository's safe retry policy. Do not fabricate any missing field. Do not change the APIx index formula, route-weight methodology or lead-time methodology while fixing scraper completeness. After each phase, run the existing test suite and add regression fixtures before proceeding.

## Final Outcome

The target is **not “29/29 fields populated at any cost.”** The target is **29/29 dimensions handled correctly**: scraped when the source exposes them, derived when derivation is deterministic, specified by the collection request when they are sampling conditions, explicitly unknown when unavailable, and never fabricated. The final result should provide both a richer airfare observation dataset and a defensible audit trail showing exactly which fields were observed, derived or unavailable and how each observation entered the APIx pipeline.
