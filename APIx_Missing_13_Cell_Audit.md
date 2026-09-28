# AERIX Production Matrix: Audit of the 13 Missing (Route × Lead Time) Cells

**Audit Date**: September 28, 2026  
**Auditor**: Antigravity Autonomous Reconciliation & Governance Auditor  
**Dataset Reference**: `runtime/top60_observation_classification.json` (11,430 observations)  
**Configuration Reference**: `config/dgca_cy2024_top60.json` (60 routes × 6 lead times = 360 cells)  
**Evidence Source**: `AERIX_All60_Production_Coverage_Report.json` & `runtime/evidence/2026-09-27/source=google_flights/`  

---

## 1. Executive Summary & Verification of Invariants

An exhaustive forensic audit was conducted on the finalized 60-route × 6-lead-time AERIX production matrix to investigate the exact cause of all 13 unpopulated cells.

### Production Baseline Verification
| Metric | Final Audited Value | Invariant Status |
| :--- | :---: | :---: |
| **Total Target Matrix Cells** | 360 (60 routes × 6 lead times) | Verified |
| **Populated Cells** | **347** (96.3889%) | **MATCH / UNCHANGED** |
| **Missing Cells** | **13** (3.6111%) | **MATCH / UNCHANGED** |
| **DGCA-Weighted Coverage** | **97.5232%** | **MATCH / UNCHANGED** |
| **Total Raw Observations** | 11,430 | Unmodified |
| **Valid AERIX Baseline Observations** | 5,834 | Unmodified |
| **Duplicate Observations** | 4,772 | Unmodified |
| **Higher Fare Family Exclusions** | 666 | Unmodified |
| **Foreign Transit Exclusions** | 158 | Unmodified |

**Core Conclusion**:  
None of the 13 missing cells are caused by overly aggressive deduplication, pipeline filtering bugs, or product-definition exclusions. Every one of the 13 missing cells has `raw_count = 0` in the production dataset. No raw data exists in the production snapshot for these cells; they are **genuinely unavailable** in the production snapshot due to source collection failures at scrape time.

---

## 2. Root Cause Analysis by Failure Category

The 13 missing cells decompose into two distinct root causes:

### Category A: Destination IATA Resolution Failure on Google Flights (12 Cells)
* **Affected Strata**:
  - `DEL-GAU` across all 6 lead times ($T+1, T+7, T+15, T+21, T+30, T+45$) — Rank 19 (DGCA weight: 0.016652)
  - `BLR-GAU` across all 6 lead times ($T+1, T+7, T+15, T+21, T+30, T+45$) — Rank 53 (DGCA weight: 0.008116)
* **Diagnosis**:
  - In `apps/scraper/src/sources/googleflights/url_builder.py`, the URL was constructed using the natural-language query parameter:
    `q=Flights to GAU from DEL on {travel_date} oneway` (and similarly for `BLR`).
  - Google Flights' natural language parser did not recognize `GAU` as a destination airport entity in the URL query string. Consequently, the destination field was left empty, and Google Flights routed the browser to its general explore page:
    *Title*: `"Find Cheap Flights Worldwide & Book Your Ticket - Google Flights"`  
    *Heading*: `"Find cheap flights from New Delhi to anywhere"` (or `"from Bengaluru to anywhere"`).
  - The DOM contained 0 flight cards (`cards_detected: 0`), resulting in 0 raw records being saved.
  - In contrast, for `GAU-CCU` (Rank 48, where GAU was the origin), Google Flights successfully resolved `CCU` as destination, yielding full populations across all 6 lead times.

### Category B: Transient Upstream Google Flights Query Error (1 Cell)
* **Affected Stratum**:
  - `IDR-BOM` at lead time $T+7$ (Travel Date: `2026-10-04`) — Rank 56 (DGCA weight: 0.007762)
* **Diagnosis**:
  - The other 5 lead times for `IDR-BOM` collected healthy flight observations:
    - $T+1$: 16 raw cards, 16 observations
    - $T+15$: 16 raw cards, 16 observations
    - $T+21$: 16 raw cards, 16 observations
    - $T+30$: 16 raw cards, 16 observations
    - $T+45$: 18 raw cards, 18 observations
  - On the single run for $T+7$ (`run_id: d86f587d-b546-49db-8ff4-1cd483d285ec`), Google Flights properly recognized the route (`Title: Indore to Mumbai | Google Flights`), but Google Flights' backend returned a transient server error:
    `Search results: No results returned. Oops, something went wrong. Reload`
  - The scraper captured the rendered DOM correctly, confirming that Google Flights returned no flight offers for that specific request execution.

---

## 3. Evidence Traceability & Run Diagnostics

| Route | Lead Time | Run ID | Duration | Google Flights Terminal State | Evidence Directory |
| :--- | :---: | :--- | :---: | :---: | :--- |
| `DEL-GAU` | $T+1$ | `02a80a06-43e4-495f-b75f-97a9f0d70449` | 9.49s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=02a80a06-43e4-495f-b75f-97a9f0d70449` |
| `DEL-GAU` | $T+7$ | `769e1384-5352-4473-bee8-cc931c7830f3` | 9.72s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=769e1384-5352-4473-bee8-cc931c7830f3` |
| `DEL-GAU` | $T+15$ | `95e1a843-a319-498b-b1e0-6d1fdb51503a` | 10.33s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=95e1a843-a319-498b-b1e0-6d1fdb51503a` |
| `DEL-GAU` | $T+21$ | `ce0ffb79-0728-4968-907d-2daa59d19f49` | 9.42s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=ce0ffb79-0728-4968-907d-2daa59d19f49` |
| `DEL-GAU` | $T+30$ | `f9981387-413b-4dea-b1fa-3897b4a88a09` | 10.31s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=f9981387-413b-4dea-b1fa-3897b4a88a09` |
| `DEL-GAU` | $T+45$ | `00869cf2-08cd-4ece-92c8-b6a627f1e392` | 10.10s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=00869cf2-08cd-4ece-92c8-b6a627f1e392` |
| `BLR-GAU` | $T+1$ | `6a30a092-73b6-4308-aa02-9041e4845107` | 10.74s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=6a30a092-73b6-4308-aa02-9041e4845107` |
| `BLR-GAU` | $T+7$ | `41534975-a948-4e74-9bc4-a5e72e9c5679` | 10.59s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=41534975-a948-4e74-9bc4-a5e72e9c5679` |
| `BLR-GAU` | $T+15$ | `16878044-0dc5-4684-aca8-bf3862784508` | 10.09s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=16878044-0dc5-4684-aca8-bf3862784508` |
| `BLR-GAU` | $T+21$ | `924903d8-6707-4c72-9c6c-c6c3cc01014c` | 10.20s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=924903d8-6707-4c72-9c6c-c6c3cc01014c` |
| `BLR-GAU` | $T+30$ | `6ded657a-9e10-4c22-9341-b2ee3115b9c1` | 10.67s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=6ded657a-9e10-4c22-9341-b2ee3115b9c1` |
| `BLR-GAU` | $T+45$ | `c36ace21-80e1-4d5d-8f4e-5205716bcd57` | 9.67s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=c36ace21-80e1-4d5d-8f4e-5205716bcd57` |
| `IDR-BOM` | $T+7$ | `d86f587d-b546-49db-8ff4-1cd483d285ec` | 10.22s | `DONE` (0 cards) | `runtime/evidence/2026-09-27/source=google_flights/run=d86f587d-b546-49db-8ff4-1cd483d285ec` |

---

## 4. Required Final Audit Table

| route | lead_time | raw_count | valid_count | duplicate_count | higher_fare_count | foreign_transit_count | reason | action_required |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| `DEL-GAU` | `T+1` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `DEL-GAU` | `T+7` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `DEL-GAU` | `T+15` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `DEL-GAU` | `T+21` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `DEL-GAU` | `T+30` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `DEL-GAU` | `T+45` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `BLR-GAU` | `T+1` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `BLR-GAU` | `T+7` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `BLR-GAU` | `T+15` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `BLR-GAU` | `T+21` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `BLR-GAU` | `T+30` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `BLR-GAU` | `T+45` | 0 | 0 | 0 | 0 | 0 | No raw observations collected: Google Flights query parser failed to resolve destination code 'GAU', landing on general explore page | Update destination URL builder to resolve 'Guwahati / GAU' entity ID; schedule targeted collection on next scrape run |
| `IDR-BOM` | `T+7` | 0 | 0 | 0 | 0 | 0 | Google Flights returned no eligible result: Upstream Google Flights query returned transient server error ('Oops, something went wrong. Reload') | Retrigger targeted scrape for IDR-BOM T+7 on next run cycle; no pipeline or methodology change required |

---

## 5. Mathematical Coverage Verification

1. **Basket Weight Impact**:
   - `DEL-GAU` route weight: **0.016652** (Rank 19)
   - `BLR-GAU` route weight: **0.008116** (Rank 53)
   - Uncovered route weight: $0.016652 + 0.008116 = 0.024768$ (2.4768%)
   - Populated route weight coverage: $1.000000 - 0.024768 = \mathbf{0.975232}$ (**97.5232%**)
   - `IDR-BOM` route weight (0.007762, Rank 56) is populated in 5 of 6 lead times ($T+1, T+15, T+21, T+30, T+45$), maintaining route-level representation in the basket.

2. **Stratum-Level Invariants**:
   - Total available cells: $60 \times 6 = 360$
   - Populated cells: $360 - 13 = \mathbf{347}$
   - Cell coverage rate: $347 / 360 = \mathbf{96.3889\%}$

---

## 6. Test Suite Verification

The full regression test suite was executed to confirm that all production invariants and stratum reconciliation rules remain strictly intact:

```powershell
$env:PYTHONPATH="apps/scraper/src;apps/api/src"; pytest tests/reconciliation/
```
**Results**:
- `tests/reconciliation/test_cross_source_reconciliation.py`: **34 passed**
- `tests/reconciliation/test_production_regression.py`: **2 passed**
- **Total: 36 passed in 1.25s (100% pass rate)**

All governance rules, product definitions, route weights, lead-time weights, and production counts remain completely unmodified and preserved.
