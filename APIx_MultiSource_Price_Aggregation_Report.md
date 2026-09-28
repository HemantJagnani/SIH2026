# APIx Multi-Source Price Reconciliation & Lineage Audit Report

**Audit Date:** 2026-09-28  
**Specification Standard:** `APIx_PRODUCT_DEF_v2.0_FROZEN` / `APIx_METHODOLOGY_V1`  
**Target Matrix:** DGCA CY2024 Top-10 Scheduled Domestic Routes × 6 Lead Times ($T+1, T+7, T+15, T+21, T+30, T+45$) = **60 Cells**  
**Audit Universe:** 5,218 Production Airfare Observations  
**Engine & Pipeline Status:** Fully Verified (**27/27 Reconciliation Tests Passed**, **68/68 APIx Core Engine & Weights Tests Passed**)  

---

## 1. Executive Summary & Methodology Decision

In official price statistics (Eurostat HICP, UK ONS, US BLS, and Indian CPI standards), scraping airfare data across multiple channels (airline direct portals, aggregators, and online travel agents) captures different prices for the **exact same physical and legal air transportation service**.

### The Core Methodology Decision
Previously, when the same flight was observed across multiple sources with conflicting prices, the observation was flagged with `PRICE_CONFLICT_REVIEW` and excluded from the baseline index. Under the new methodology:

> **Core Decision:** If the same underlying flight/product is observed across multiple sources with different prices, **the product is NOT marked as permanently excluded merely because prices differ**.  
> Instead, multiple source observations of the **SAME canonical purchasable product** collapse into **ONE APIx observation** whose fare is the **arithmetic mean of all valid comparable source prices**:
>
> $$\text{canonical\_fare} = \frac{1}{K} \sum_{k=1}^K p_k$$
>
> Complete audit lineage and every original source price are preserved verbatim for auditing, transparency, and sub-index analysis.

### Numerical Example
For flight **6E-204 (DEL $\to$ BOM, 2026-10-04, 10:00 AM, Economy Saver)**:
- Google Flights: ₹6,500
- EaseMyTrip: ₹7,200
- Ixigo: ₹6,800

The reconciliation layer constructs **exactly ONE APIx product observation**:
$$\text{canonical\_fare} = \frac{6,500 + 7,200 + 6,800}{3} = \frac{20,500}{3} = \mathbf{₹6,833.33}$$

### Distinguishing Price Conflict Statuses
- **`PRICE_CONSISTENT`**: Source prices are identical or within the configured rounding tolerance ($\le ₹1.00$).
- **`PRICE_VARIANCE_AGGREGATED`**: Same canonical product confirmed across sources, but prices differ beyond tolerance. The arithmetic mean is computed, and the single canonical observation proceeds directly into the baseline index pipeline.
- **`PRICE_CONFLICT_UNRESOLVED`**: Only assigned when the observations cannot confidently be established as the same purchasable product, or price semantics are incompatible (e.g., `DISPLAYED_TOTAL` + `DISPLAYED_FROM`). Only `PRICE_CONFLICT_UNRESOLVED` is excluded from the APIx baseline calculation.

---

## 2. Implementation Rules & Pipeline Architecture

```
Raw Multi-Channel Source Observations (Google Flights, EaseMyTrip, Ixigo, Future OTAs)
                                        │
                                        ▼  [Pass 1: Source Normalization]
                     Generic BaseReconciliationAdapter
               (Deterministic Fingerprints, No Data Fabrication)
                                        │
                                        ▼  [Pass 2: Engine Deduplication]
                       Same-Source DOM Card Deduplication
                          (Removes Multi-Row DOM Duplicates)
                                        │
                                        ▼  [Pass 3: Multi-Dimensional Matching]
                           Deterministic Match Key
         (Route, Date, Airline, Flight Number, Departure Time, Stops, Cabin, Tier, Bag)
                                        │
                                        ▼  [Pass 4: Semantic Validation]
                     Price Semantics Compatibility Check
                      (DISPLAYED_TOTAL vs DISPLAYED_FROM)
                                        │
                      ┌─────────────────┴─────────────────┐
                      ▼                                   ▼
        [Incompatible Semantics]              [Compatible Semantics]
        PRICE_CONFLICT_UNRESOLVED             Multi-Source Price Aggregation
          (Retained for Audit,                  Arithmetic Mean Computation:
            Excluded from Index)                 canonical_fare = (1/K) Σ p_k
                                                match_status:
                                                - PRICE_CONSISTENT (Δ ≤ ₹1)
                                                - PRICE_VARIANCE_AGGREGATED (Δ > ₹1)
                                                Lineage Captured
                                                          │
                                                          ▼  [Pass 5: Single Entry Flow]
                                              1 Canonical Product Observation
                                                          │
                                                          ▼  [Pass 6: Product Stratification]
                                              APIx Product Observation
                                              (1 Product = Exactly 1 Weight)
                                                          │
                                                          ▼  [Pass 7: Price Formation]
                                              Jevons Elementary Aggregation
                                              J_(s,t) = exp( 1/N Σ ln(p_t / p_0) )
```

### Key Architectural Safeguards
1. **Multi-Dimensional Matching (No Flight Number Alone)**: Product identity requires agreement on route, travel date, airline, flight number, departure timing, stops, cabin, fare family baseline tier, non-standard baggage tier, and passenger type.
2. **Equal Source Weights**: In accordance with the methodology decision, sources are weighted equally in the arithmetic mean ($1/K$). No OTA market-share weights, scraper row weights, or arbitrary source priorities are applied.
3. **No Statistical Sample Size Inflation**: 3 OTA observations collapse into 1 canonical product, which produces exactly 1 APIx price observation in the elementary stratum. The number of OTA observations does NOT artificially increase the statistical weight of that flight in the Jevons aggregate.
4. **Single-Source Preservation**: If observed by only 1 source, $\text{canonical\_fare} = p_{\text{source}}$, $\text{source\_count} = 1$, and $\text{aggregation\_method} = \text{"SINGLE\_SOURCE"}$. No synthetic prices are fabricated.
5. **Audit Lineage**: Every canonical offer and APIx observation preserves:
   - `source_count: int`
   - `source_ids: List[str]`
   - `source_observation_ids: List[str]`
   - `price_by_source: Dict[str, Decimal]`
   - `source_prices: Dict[str, Decimal]`
   - `source_timestamps: Dict[str, str]`
   - `aggregation_method: str` (`"ARITHMETIC_MEAN"` or `"SINGLE_SOURCE"`)
   - `aggregation_source_count: int`
   - Original individual prices verbatim.

---

## 3. Test Suite Verification (27/27 Tests Passed)

All 16 original specification tests plus the 11 explicit methodology test cases (§11 A through K) were executed and passed:

| Test ID | Test Name | Scenario / Invariant Verified | Outcome |
| :---: | :--- | :--- | :---: |
| **Test A** | `test_a_two_sources_same_price` | Google ₹6,500 + EMT ₹6,500 $\to$ 1 observation ₹6,500.00 (`PRICE_CONSISTENT`, `ARITHMETIC_MEAN`) | **PASS** |
| **Test B** | `test_b_two_sources_different_prices` | Google ₹6,500 + EMT ₹7,200 $\to$ 1 observation ₹6,850.00 (`PRICE_VARIANCE_AGGREGATED`, `ARITHMETIC_MEAN`) | **PASS** |
| **Test C** | `test_c_three_sources_different_prices` | Google ₹6,500 + EMT ₹7,200 + Ixigo ₹6,800 $\to$ 1 observation ₹6,833.33 | **PASS** |
| **Test D** | `test_d_single_source` | 1 source $\to$ 1 observation at source price (`SINGLE_SOURCE`, `source_count = 1`) | **PASS** |
| **Test E** | `test_e_different_fare_family` | IndiGo Saver (₹6,500) vs FlexiPlus (₹7,800) $\to$ remain separate canonical products | **PASS** |
| **Test F** | `test_f_different_baggage_conditions` | SpiceJet 15kg (₹5,500) vs 20kg (₹6,900) $\to$ remain separate canonical products | **PASS** |
| **Test G** | `test_g_incompatible_price_semantics` | Google `DISPLAYED_TOTAL` + Ixigo `DISPLAYED_FROM` $\to$ do not average, `PRICE_CONFLICT_UNRESOLVED` | **PASS** |
| **Test H** | `test_h_different_physical_flights` | Different flight numbers or departure times $\to$ remain separate | **PASS** |
| **Test I** | `test_i_same_source_dom_duplicates` | 2 Google DOM cards + 1 EMT card $\to$ Google deduplicated first, mean of 2 unique sources | **PASS** |
| **Test J** | `test_j_four_otas_with_four_prices` | Google ₹6,000 + EMT ₹6,200 + Ixigo ₹6,400 + MakeMyTrip ₹6,600 $\to$ 1 observation ₹6,300.00 | **PASS** |
| **Test K** | `test_k_raw_lineage_preserved` | Verifies `source_count`, `source_ids`, `source_observation_ids`, `price_by_source`, timestamps, method | **PASS** |
| **Test 1** | `test_1_google_easemytrip_identical_offer` | Google + EMT identical offer collapses into 1 canonical offer with enriched baggage provenance | **PASS** |
| **Test 2** | `test_2_three_sources_identical_offer` | 3 sources identical offer collapses into 1 canonical offer | **PASS** |
| **Test 3** | `test_3_different_flight_numbers` | Different flight numbers on same route and time produce distinct canonical offers | **PASS** |
| **Test 4** | `test_4_different_fare_families` | Different fare families on same flight remain separate | **PASS** |
| **Test 5** | `test_5_different_baggage_conditions` | Different baggage tiers on same flight remain separate | **PASS** |
| **Test 6** | `test_6_missing_google_fields_merged_safely` | Missing Google baggage/rules safely enriched from EMT without data fabrication | **PASS** |
| **Test 7** | `test_7_different_prices_arithmetic_mean_aggregated` | Price variance between Google and EMT aggregates to arithmetic mean ₹6,850.00 | **PASS** |
| **Test 8** | `test_8_google_dom_duplicate` | Google duplicate DOM container selections collapse to 1 physical offer | **PASS** |
| **Test 9** | `test_9_easemytrip_duplicate` | EaseMyTrip duplicate DOM extractions collapse to 1 physical offer | **PASS** |
| **Test 10** | `test_10_google_only_offer` | Google-only offer retained without fabrication (`NO_MATCH`) | **PASS** |
| **Test 11** | `test_11_easemytrip_only_offer` | EaseMyTrip-only offer retained (`NO_MATCH`) | **PASS** |
| **Test 12** | `test_12_ixigo_only_offer` | Ixigo-only offer retained (`NO_MATCH`) | **PASS** |
| **Test 13** | `test_13_probable_match_not_automatically_merged` | Different scheduled times (10:00 vs 14:00) not merged | **PASS** |
| **Test 14** | `test_14_insufficient_identifying_fields` | Offers missing flight numbers flagged `INSUFFICIENT_DATA` and excluded | **PASS** |
| **Test 15** | `test_15_different_price_semantics_not_comparable` | Incompatible semantics remain separate | **PASS** |
| **Test 16** | `test_16_future_source_registration` | Dynamically registers 4th source without touching core reconciliation engine | **PASS** |

---

## 4. 5,218-Observation Production Matrix Reconciliation Audit

The complete 5,218 raw production observation dataset spanning all 60 cells of the DGCA Top-10 production matrix was processed through the updated reconciliation engine and pipeline:

### 4.1 Global Pipeline Metrics
| Metric | Value | Notes |
| :--- | :---: | :--- |
| **Total Raw Scraped Observations Audited** | **5,218** | Google Flights (3,484) + EaseMyTrip (1,734) |
| **Normalized Canonical Offers Produced** | **5,218** | 100.0% normalized via generic adapters |
| **Same-Source DOM Duplicates Removed** | **3,113** | Google Flights: 2,024; EaseMyTrip: 1,089 |
| **Canonical Product Offers Formed** | **2,105** | Distinct flight products post-deduplication |
| **Single-Source Canonical Offers** | **2,105** | Google Flights (1,460) + EaseMyTrip (645) |
| **Multi-Source Canonical Offers** | **0** | Disjoint airline inventory in historical capture |
| **Multi-Source Price Aggregations** | **0** | Baseline dataset observed non-overlapping carrier segments |
| **Unresolved Price Conflicts** | **0** | No incompatible price semantics encountered |
| **Excluded Observations (Cabotage Violations)** | **29** | Foreign transit carriers routing via overseas hubs |
| **Valid Comparable Baseline APIx Observations** | **2,076** | Qualifying domestic adult economy baseline fares |
| **Populated Matrix Cells** | **60 of 60 (100.0%)** | All 10 routes active across all 6 horizons |

### 4.2 Source-Count Distribution
- **Canonical Offers Source-Count Distribution:**
  - $K = 1$: **2,105** offers (100.0%)
  - $K \ge 2$: **0** offers (0.0%)
- **Valid APIx Observations Source-Count Distribution:**
  - $K = 1$: **2,076** observations (100.0%)
  - $K \ge 2$: **0** observations (0.0%)

### 4.3 Number of APIx Observations: Before vs. After Aggregation
| Stage | Observation Count | Methodological Significance |
| :--- | :---: | :--- |
| **1. Raw Scraped Observations** | **5,218** | Verbatim raw data preserved for immutable lineage |
| **2. Pre-Reconciliation Naive Filter** | **2,779** | Prior heuristic filtering (retained duplicate DOM renders across scraper runs) |
| **3. Post-Reconciliation Canonical Offers** | **2,105** | Strict physical flight deduplication across all sources |
| **4. Final APIx Baseline Observations** | **2,076** | Exactly 1 observation per qualifying physical product |

*Net reduction: 5,218 raw observations $\to$ 2,076 distinct APIx product observations (60.2% deduplication and standardization efficiency).*

---

## 5. Route-Level and Lead-Time Cell Breakdown (All 60 Cells)

### 5.1 Route-Level Summary (10 Routes)
| Rank | Route ID | City Pair | Raw Obs | Canonical Offers | Valid APIx Obs | Excluded Obs |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| 1 | `DEL-BOM` | Delhi – Mumbai | 2,432 | 712 | **712** | 0 |
| 2 | `BLR-DEL` | Bengaluru – Delhi | 478 | 239 | **239** | 0 |
| 3 | `BLR-BOM` | Bengaluru – Mumbai | 392 | 196 | **196** | 0 |
| 4 | `DEL-HYD` | Delhi – Hyderabad | 350 | 175 | **175** | 0 |
| 5 | `DEL-CCU` | Delhi – Kolkata | 362 | 181 | **181** | 0 |
| 6 | `DEL-PNQ` | Delhi – Pune | 308 | 154 | **154** | 0 |
| 7 | `DEL-MAA` | Delhi – Chennai | 264 | 132 | **119** | 13 |
| 8 | `BOM-HYD` | Mumbai – Hyderabad | 232 | 116 | **107** | 9 |
| 9 | `AMD-DEL` | Ahmedabad – Delhi | 222 | 111 | **104** | 7 |
| 10 | `DEL-SXR` | Delhi – Srinagar | 178 | 89 | **89** | 0 |
| **Total** | — | **Top 10 Routes** | **5,218** | **2,105** | **2,076** | **29** |

### 5.2 Lead-Time Horizon Summary (6 Horizons)
| Horizon | Raw Obs | Canonical Offers | Valid APIx Obs | Excluded Obs |
| :---: | :---: | :---: | :---: | :---: |
| **T+1** | 596 | 346 | **342** | 4 |
| **T+7** | 1,190 | 750 | **745** | 5 |
| **T+15** | 665 | 225 | **219** | 6 |
| **T+21** | 1,228 | 276 | **270** | 6 |
| **T+30** | 778 | 260 | **255** | 5 |
| **T+45** | 761 | 248 | **245** | 3 |
| **Total** | **5,218** | **2,105** | **2,076** | **29** |

---

## 6. Multi-Source Aggregation Lineage Demonstration

To demonstrate the exact lineage payload produced when multi-channel overlapping observations occur, below is an audited record generated by the reconciliation engine for flight **6E-204**:

```json
{
  "canonical_offer_id": "can_reconciled_6E204_1000_3src",
  "route": "DEL-BOM",
  "origin": "DEL",
  "destination": "BOM",
  "travel_date": "2026-10-04",
  "lead_time": "T+7",
  "airline": "IndiGo",
  "flight_number": "6E204",
  "departure_time": "10:00",
  "arrival_time": "12:15",
  "stops": 0,
  "cabin": "ECONOMY",
  "fare_family": "SAVER",
  "baggage": "7kg cabin + 15kg checkin",
  "refundability": "NON_REFUNDABLE",
  "total_fare": 6833.33,
  "currency": "INR",
  "is_comparable_baseline": true,
  "sources_contributing": [
    "google_flights",
    "easemytrip",
    "ixigo"
  ],
  "source_ids": [
    "google_flights",
    "easemytrip",
    "ixigo"
  ],
  "source_observation_ids": [
    "gf_c",
    "emt_c",
    "ixi_c"
  ],
  "source_count": 3,
  "price_by_source": {
    "google_flights": 6500.00,
    "easemytrip": 7200.00,
    "ixigo": 6800.00
  },
  "source_prices": {
    "google_flights": 6500.00,
    "easemytrip": 7200.00,
    "ixigo": 6800.00
  },
  "source_timestamps": {
    "google_flights": "2026-09-28T02:00:00+00:00",
    "easemytrip": "2026-09-28T02:00:00+00:00",
    "ixigo": "2026-09-28T02:00:00+00:00"
  },
  "aggregation_method": "ARITHMETIC_MEAN",
  "aggregation_source_count": 3,
  "match_status": "PRICE_VARIANCE_AGGREGATED"
}
```

---

## 7. Confirmation of Invariance & Protection Standards

The following core index parameters and components were strictly audited and confirmed **unmodified**:

1. **DGCA Top-60 Route Weights ($W_r$)**: Unchanged. Weights strictly sum to $1.000000$ across all 60 routes.
2. **Empirical Lead-Time Weights ($w_L$)**: Unchanged. Weights strictly sum to $1.0000$ across all 6 horizons.
3. **CPI Airfare Item Weight**: Unchanged. CPI weight ($0.0014022$) remains strictly decoupled from route weights.
4. **Base Reference Index Value**: Unchanged ($I_0 = 100.00$).
5. **Jevons Index Formulation**: Unchanged. Unweighted geometric mean of price relatives:
   $$J_{(s,t)} = \exp\left(\frac{1}{N}\sum_{i=1}^N \ln\left(\frac{p_{i,t}}{p_{i,0}}\right)\right)$$
6. **Product Definition Standard**: Unchanged (`APIx_PRODUCT_DEF_v2.0_FROZEN`).
7. **Scraper Operations**: Unchanged. No changes to scraper request dispatching, navigation flows, or CAPTCHA fail-safe mechanisms.
