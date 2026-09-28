# AERIX Phase 28  Production Coverage Report
**Route:** DEL ? BOM
**Phase:** AERIX Phase 28  Production Coverage + AERIX Product Lock
**Timestamp (UTC):** 2026-09-26T20:50:32Z
**Generated:** 2026-09-27

---

## Executive Summary

| Metric | Value |
|---|---|
| Route covered | DEL-BOM |
| Lead times | T+1, T+7, T+15, T+21, T+30, T+45 |
| Total jobs executed | 14 |
| Jobs completed (DONE) | **14 / 14** |
| Jobs blocked | **0** |
| Jobs failed | **0** |
| Total observations collected | **2,432** |
| Duplicate offers detected | **0** (EaseMyTrip) |

> **No anti-bot blocks, no CAPTCHA encounters, no failed requests across any job.**
> All 14 jobs returned `state=DONE` with full result stream stabilization.

---

## Collection Matrix  DEL-BOM

### Google Flights  CORE_ONLY

| Lead Time | Travel Date | Cards Detected | Observations | Unique Offers | State |
|---|---|---|---|---|---|
| T+1  | 2026-09-27 | 98  | 98  | 49 | DONE |
| T+7  | 2026-10-03 | 122 | 122 | 61 | DONE |
| T+15 | 2026-10-11 | 112 | 112 | 56 | DONE |
| T+21 | 2026-10-17 | 112 | 112 | 56 | DONE |
| T+30 | 2026-10-26 | 120 | 120 | 60 | DONE |
| T+45 | 2026-11-10 | 134 | 134 | 67 | DONE |
| **Total** | | **698** | **698** | **349** | |

> Google Flights CORE_ONLY returns 2 observations per itinerary (outbound + return-leg card), hence unique_offers approx cards/2.

---

### EaseMyTrip  CORE_ONLY

| Lead Time | Travel Date | Cards Detected | Observations | Unique Offers | Duplicates | State |
|---|---|---|---|---|---|---|
| T+1  | 2026-09-27 | 96  | 96  | 96  | 0 | DONE |
| T+7  | 2026-10-03 | 139 | 139 | 139 | 0 | DONE |
| T+15 | 2026-10-11 | 103 | 103 | 103 | 0 | DONE |
| T+21 | 2026-10-17 | 146 | 146 | 146 | 0 | DONE |
| T+30 | 2026-10-26 | 156 | 156 | 156 | 0 | DONE |
| T+45 | 2026-11-10 | 143 | 143 | 143 | 0 | DONE |
| **Total** | | **783** | **783** | **783** | **0** | |

---

### EaseMyTrip  CORE_AND_DETAILS (Fare Family Enrichment)

| Lead Time | Travel Date | Base Cards | Enriched Observations | Unique Offers | Duplicates | Avg Offers/Itin | State |
|---|---|---|---|---|---|---|---|
| T+7  | 2026-10-03 | 139 | 461 | 461 | 0 | ~3.32 | DONE |
| T+21 | 2026-10-17 | 146 | 490 | 490 | 0 | ~3.36 | DONE |
| **Total** | | **285** | **951** | **951** | **0** | **~3.34** | |

> CORE_AND_DETAILS expands each flight card into all available fare families (SpiceSaver, EMTEXCLUSIVE, SpiceFlex, SpiceMax). 139 base cards -> 461 enriched offers (T+7); 146 base cards -> 490 enriched offers (T+21).

---

## Observation Totals

| Source | Mode | Observations |
|---|---|---|
| Google Flights | CORE_ONLY | 698 |
| EaseMyTrip | CORE_ONLY | 783 |
| EaseMyTrip | CORE_AND_DETAILS | 951 |
| **Grand Total** | | **2,432** |

---

## Result Stream Stabilization

All EaseMyTrip jobs used the polling-based stabilization loop before DOM capture:

| Job | Initial Cards | Final Cards | Stable After | Duration |
|---|---|---|---|---|
| T+1  CORE | 96  | 96  | 3 checks | ~6s |
| T+7  CORE | 139 | 139 | 3 checks | ~6s |
| T+15 CORE | 103 | 103 | 3 checks | ~6s |
| T+21 CORE | 146 | 146 | 3 checks | ~6s |
| T+30 CORE | 156 | 156 | 3 checks | ~6s |
| T+45 CORE | 143 | 143 | 3 checks | ~6s |
| T+7  DETAILS | 139 | 139 | 3 checks | ~6s |
| T+21 DETAILS | 146 | 146 | 3 checks | ~6s |

All streams stabilized on the first three consecutive identical checks. No partial captures.

---

## Enriched Field Coverage (CORE_AND_DETAILS)

| Field | Coverage |
|---|---|
| fare_family | 100% |
| cabin_baggage_kg | 100% |
| checkin_baggage_kg | 100% |
| cancellation_fee | Where disclosed |
| change_fee | Where disclosed |
| refund_status | Where disclosed |
| discount | Metadata only (not deducted from total_fare) |
| base_fare | NOT exposed by EaseMyTrip |
| tax_breakdown | NOT exposed by EaseMyTrip |

---

## Canonical Sample  EaseMyTrip T+21 CORE_AND_DETAILS (SpiceJet SG-802)

Four fare families captured for the same itinerary:

| Fare Family | Total Fare (INR) | Cabin Bag | Check-in Bag |
|---|---|---|---|
| SpiceSaver    | 6,244 | 7 kg | 15 kg |
| EMTEXCLUSIVE  | 6,493 | 7 kg | 15 kg |
| SpiceFlex     | 6,761 | 7 kg | 15 kg |
| SpiceMax      | 7,653 | 7 kg | 15 kg |

---

## Reliability and Anti-Bot Status

| Check | Result |
|---|---|
| CAPTCHA encounters | None |
| HTTP 403 / 429 blocks | None |
| EaseMyTrip 401 errors | None |
| Crawlee handler timeouts | 2x60s (auto-retried, both recovered) |
| Safe-stop triggered | No |
| Session persistence | Active across all jobs |

Two Playwright handler timeouts occurred during CORE_AND_DETAILS runs (DOM parse for 461/490 observations is inherently slow). Both were auto-retried by Crawlee and succeeded on the second attempt with full data. No observations were lost.

---

## Phase Completion Status

| Goal | Status |
|---|---|
| DEL-BOM x 6 lead times x 2 sources (CORE_ONLY) | Complete |
| DEL-BOM CORE_AND_DETAILS (T+7, T+21) | Complete |
| Zero blocked searches | Achieved |
| Zero duplicate offers (EaseMyTrip) | Achieved |
| Result stream stabilization active | Active |
| AERIX Product Definition locked | Complete (AERIX_Product_Definition.md) |

---

## Next Steps

1. **Switch to hotspot/residential IP** before expanding to remaining routes  college/institutional IPs can trigger EaseMyTrip rate limits.
2. **Expand to remaining 9 routes** (BOM-DEL, DEL-MAA, BOM-BLR, DEL-CCU, BOM-HYD, DEL-GOI, CCU-DEL, HYD-BOM, BLR-BOM)  same 6 lead times, both sources.
3. **Run CORE_AND_DETAILS for all routes** if time permits (currently only T+7 and T+21 were enriched for DEL-BOM).
4. **Ingest to database**  push collected observations to PostgreSQL via the existing ingestion pipeline.
5. **CPI Index Computation**  apply AERIX product methodology to compute route-level price indices.

---

*Report generated by run_phase28_production.py | AERIX CPI Airfare Pipeline*
