# AERIX Pipeline Stratum Governance & Product Definition Fix Report

**Execution Date:** 2026-09-28  
**Governance Standard:** `AERIX_PRODUCT_DEF_v2.0_FROZEN` / `APIX_METHODOLOGY_V1`  
**Dataset Audited:** `runtime/top60_observation_classification.json` (11,430 Production Observations)  
**Target Invariant Verified:**  
$$\text{VALID\_BASELINE}\,(5,834) + \text{DUPLICATE}\,(4,772) + \text{HIGHER\_FARE}\,(666) + \text{FOREIGN\_TRANSIT}\,(158) = \mathbf{11,430}\quad (\Delta = 0)$$

---

## 1. Executive Summary

Based on the findings from [`AERIX_5834_vs_5134_Discrepancy_Audit.md`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/AERIX_5834_vs_5134_Discrepancy_Audit.md), the AERIX reconciliation and product comparability pipeline has been architectural upgraded to:
1. **Enforce Stratum Independence:** The minimum protected sampling stratum is $(\text{route}, \text{lead\_time})$. Observations from different lead times ($T+1, T+7, \dots, T+45$) can **never** collide or cross-deduplicate, even if their calendar travel date, flight number, and prices are identical.
2. **Centralize Product Definition Gates:** Created a single authoritative policy module ([`apps/scraper/src/reconciliation/policy.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/scraper/src/reconciliation/policy.py)) governing higher fare family exclusions and the complete list of 14 international carriers without domestic cabotage rights.
3. **Harmonize Pipeline & Production Classifier:** Executing `CrossSourceReconciliationPipeline.run()` dynamically on the 11,430-observation dataset now yields **EXACTLY 5,834 valid baseline observations**, 4,772 same-source duplicates, 666 higher fare family exclusions, and 158 foreign transit exclusions with **0 discrepancy**.

---

## 2. Files Changed

| File Path | Description of Changes |
| :--- | :--- |
| [`apps/scraper/src/reconciliation/policy.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/scraper/src/reconciliation/policy.py) | **New authoritative policy module.** Defines `INTERNATIONAL_CARRIERS` (all 14 carriers), `HIGHER_FARE_FAMILY_KEYWORDS` (`FLEX`, `UPFRONT`, `BUSINESS`, `PREMIUM`, `EXCLUSIVE`, `MAX`, `CLASSIC`), `is_foreign_transit_carrier()`, and `is_higher_fare_family()`. |
| [`apps/scraper/src/reconciliation/__init__.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/scraper/src/reconciliation/__init__.py) | Exposed centralized policy constants and functions to the package interface. |
| [`apps/scraper/src/reconciliation/engine.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/scraper/src/reconciliation/engine.py) | 1. Scoped same-source deduplication key by stratum `(source, (route, lead_time), fingerprint, fare)`.<br>2. Scoped cross-source match key by `(route, lead_time, travel_date, ...)`.<br>3. Added `merge()` method and exclusion counters to `ReconciliationDiagnostics`. |
| [`apps/scraper/src/reconciliation/pipeline.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/scraper/src/reconciliation/pipeline.py) | 1. Removed local truncated carrier set; imported shared `policy.py` rules.<br>2. Added `run_cell(route, lead_time, raw_items)` for single-cell execution.<br>3. Updated `run(raw_items)` to partition by stratum `(route, lead_time)` and aggregate diagnostics.<br>4. Added `classify_batch(raw_items)` matching production summary invariants. |
| [`apps/scraper/src/scripts/run_production_matrix_top60.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/scraper/src/scripts/run_production_matrix_top60.py) | Refactored to import `INTERNATIONAL_CARRIERS`, `is_foreign_transit_carrier()`, and `is_higher_fare_family()` from `reconciliation.policy`. |
| [`tests/reconciliation/test_cross_source_reconciliation.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/tests/reconciliation/test_cross_source_reconciliation.py) | Added 7 new governance regression tests (Tests A through G). |
| [`tests/reconciliation/test_production_regression.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/tests/reconciliation/test_production_regression.py) | **New test file.** Automated regression test asserting all production invariants on the full 11,430 dataset. |

---

## 3. Tests Added & Verification Results

### 3.1 Test Suite Status: 36 Passed in 1.33s (100% Pass Rate)

```bash
$env:PYTHONPATH="apps/scraper/src;apps/api/src"; pytest tests/reconciliation/ -v
============================= 36 passed in 1.33s ==============================
```

### 3.2 Specific Governance Tests Added:
1. **`test_governance_a_stratum_independence_no_cross_leadtime_dedup`**:  
   Verifies that an identical flight departing at 10:00 on 2026-10-04 observed at $T+1$ and $T+7$ yields **2 valid baseline observations** in their respective strata and **0 duplicates**.
2. **`test_governance_b_flexiplus_excluded`**:  
   Verifies that `FlexiPlus` tickets (₹8,500) are excluded from the baseline index, recorded in `excluded_offers`, and increment `diagnostics.higher_fare_family_exclusions`.
3. **`test_governance_c_gulf_air_excluded`**:  
   Verifies that Gulf Air domestic-looking transit (`BLR-GOI`, ₹61,131) is excluded from the baseline index as a foreign transit cabotage violation.
4. **`test_governance_d_singapore_airlines_excluded`**:  
   Verifies that Singapore Airlines domestic-looking transit (`HYD-CCU`, ₹49,221) is excluded from the baseline index as a foreign transit cabotage violation.
5. **`test_governance_e_existing_foreign_carriers_remain_excluded`**:  
   Verifies that Kuwait Airways, Emirates, Etihad, SriLankan, and Oman Air all remain strictly excluded.
6. **`test_governance_f_multi_source_same_product_aggregation_still_works`**:  
   Verifies that multi-source same-product aggregation functions properly within stratum: Google Flights (₹6,500) + EaseMyTrip (₹7,200) collapses to **1 AERIX observation at ₹6,850.00** with `PRICE_VARIANCE_AGGREGATED`.
7. **`test_governance_g_different_lead_time_cells_remain_independent`**:  
   Verifies that $T+1$ (GF ₹6,000 + EMT ₹6,200 $\to$ ₹6,100) and $T+7$ (GF ₹7,000 + EMT ₹7,400 $\to$ ₹7,200) produce **2 distinct observations**, one in each cell, without cross-averaging.
8. **`test_production_invariants_11430`**:  
   Runs `pipeline.run()` against all 11,430 observations and asserts `valid == 5834`, `dup == 4772`, `hff == 666`, `ft == 158`, `cells == 347`, `coverage == 97.5232%`.
9. **`test_classify_batch_invariants`**:  
   Verifies `pipeline.classify_batch()` matches production invariants with 0 discrepancy.

---

## 4. Before vs. After Pipeline Reconciliation Counts

| Metric / Dimension | Before Architecture Fix (Flat Batch) | After Architecture Fix (Stratum-Aware) | Status / Target |
| :--- | :---: | :---: | :---: |
| **Total Raw Observations** | **11,430** | **11,430** | Verified Identical |
| **Valid AERIX Baseline Observations** | 5,134 | **5,834** | **Target Met ($\Delta = 0$)** |
| **Same-Source Duplicates** | 6,220 *(False Cross-LT duplicates)* | **4,772** *(Within-cell duplicates)* | **Target Met ($\Delta = 0$)** |
| **Higher Fare Family Exclusions** | 0 *(344 FlexiPlus leaked into valid)* | **666** *(100% FlexiPlus excluded)* | **Target Met ($\Delta = 0$)** |
| **Foreign Transit Exclusions** | 76 offers *(3 flights leaked)* | **158** *(100% foreign carriers excluded)* | **Target Met ($\Delta = 0$)** |
| **Populated Matrix Cells** | 347 / 360 | **347 / 360** | **96.39% Intact** |
| **DGCA-Weighted Matrix Coverage** | 97.5232% | **97.5232%** | **100% Intact** |
| **Mathematical Discrepancy** | `+700` | **`0`** | **Airtight Proof** |

---

## 5. Architectural Invariant Confirmations

### 5.1 Confirmation That Cross-Lead-Time Deduplication is Impossible
- **Physical Fingerprint Purity:** The physical product identity hash (`canonical_offer_fingerprint`) continues to strictly describe physical aircraft offerings:
  $$\text{Fingerprint} = \text{Route} \,|\, \text{Date} \,|\, \text{Airline} \,|\, \text{FlightNo} \,|\, \text{DepTime} \,|\, \text{Stops} \,|\, \text{Cabin} \,|\, \text{FareFamily} \,|\, \text{Baggage} \,|\, \text{Refundability} \,|\, \text{Pax}$$
  `lead_time` was **not** conflated into the physical product identity.
- **Stratum Boundary Protection:** In `CrossSourceReconciliationEngine`:
  $$\text{Deduplication Key} = \left(\text{source},\; \mathbf{(\text{route}, \text{lead\_time})},\; \text{canonical\_offer\_fingerprint},\; \text{total\_fare}\right)$$
  $$\text{Match Key} = \left(\text{route},\; \mathbf{\text{lead\_time}},\; \text{travel\_date},\; \text{airline},\; \text{flight\_no},\; \dots\right)$$
  In addition, `CrossSourceReconciliationPipeline.run()` explicitly partitions batches by $(\text{route}, \text{lead\_time})$ and processes each cell via `run_cell()`. Cross-lead-time collisions are now structurally and mathematically impossible.

### 5.2 Confirmation That Product Definition Gates are Centralized
- All product gates now import directly from [`apps/scraper/src/reconciliation/policy.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apps/scraper/src/reconciliation/policy.py).
- `is_foreign_transit_carrier()` enforces the complete list of 14 international airlines (including Gulf Air and Singapore Airlines).
- `is_higher_fare_family()` enforces exclusions on all premium fare keywords (`FLEX`, `UPFRONT`, `BUSINESS`, `PREMIUM`, `EXCLUSIVE`, `MAX`, `CLASSIC`).
- Zero duplicate carrier sets or hardcoded regex strings remain in `pipeline.py` or `run_production_matrix_top60.py`.

### 5.3 Confirmation That Multi-Source Price Aggregation Still Works
- Within any given $(\text{route}, \text{lead\_time})$ stratum, multiple OTA observations of the exact same canonical flight offer are detected, tested for semantic compatibility, and aggregated using equal source weights:
  $$\text{canonical\_fare} = \frac{1}{K}\sum_{k=1}^K p_k$$
- Confirmed by `test_governance_f_multi_source_same_product_aggregation_still_works` and Test J (4 OTAs collapsing into 1 AERIX observation at ₹6,300.00).

---

## 6. Protection of Frozen Standards

The following core components were **strictly preserved** without modification:
1. **DGCA Route Weights ($W_r$):** Top-60 weights sum strictly to $1.000000$.
2. **Empirical Lead-Time Weights ($w_L$):** Weights sum strictly to $1.0000$ across all 6 horizons.
3. **CPI Airfare Weight:** Value $0.0014022$ remains unaltered and decoupled.
4. **Product Definition Standard:** `AERIX_PRODUCT_DEF_v2.0_FROZEN` remains unchanged.
5. **OTA Aggregation Methodology:** Arithmetic mean with full lineage preservation remains unchanged.
6. **Jevons Elementary Aggregator:** $\exp\left(\frac{1}{N}\sum \ln p_i\right)$ untouched.
7. **Reference Price ($P_{\text{ref}}$):** **$P_{\text{ref}}$ was NOT calculated**.
8. **Raw Observations:** The 11,430 observations in `runtime/top60_observation_classification.json` remain untouched.
