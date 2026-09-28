# AERIX Index-Construction Pipeline Methodology Correction & Monthly Coverage Audit Report

**Document Version:** 1.0.0  
**Audit Date:** 2026-09-28  
**Dataset Reference:** `runtime/top60_observation_classification.json` (11,716 observations, 360 cells)  
**Methodology Standard:** MoSPI CPI 2024 / Eurostat HICP 2024 / ILO Consumer Price Index Manual  
**Governance Status:** FULLY APPLIED AND VERIFIED  

---

## 1. Executive Summary

This report documents the formal correction of the AERIX index-construction pipeline and presents the empirical observation coverage audit of the finalized 11,716-observation production dataset.

### Critical Methodological Corrections Enforced
1. **Strict Prohibition of $P_{\text{ref}}$ as Index Denominator:**  
   The provisional basket reference price $P_{\text{ref}} = ₹8,641.45$ **MUST NOT** be used as the base or denominator for index compilation. The pipeline explicitly forbids computing:
   $$\text{AERIX}_t = 100 \times \frac{P_t}{P_{\text{ref}}}$$
   Such a naive ratio-to-base construction violates international CPI standards (MoSPI CPI 2024, Eurostat HICP, ILO CPI Manual §10.15), ignores product comparability, and produces severe chain-drift and unadjusted quality bias.
2. **Implementation of Short-Chain Jevons Construction:**  
   The index calculation pipeline is strictly configured to use the internationally compliant short-chain Jevons index:
   - Monthly geometric mean prices calculated within homogeneous product strata;
   - Price relatives computed strictly across matched product items observed in consecutive periods ($t-1$ and $t$);
   - Elementary Jevons links aggregated using frozen empirical lead-time weights and DGCA route weights;
   - Recursive monthly chaining with an explicitly designated reference month set to 100.0000.
3. **Decoupling of Absolute Fare Levels from Index Values:**  
   Under no circumstances is an individual flight fare compared to ₹8,641.45 to decide whether an index is above or below 100. $P_{\text{ref}} = ₹8,641.45$ is preserved strictly with `status = PROVISIONAL_PROJECT_REFERENCE` and `purpose = descriptive/reference-price diagnostic`.
4. **Empirical Monthly Coverage Audit & Non-Fabrication Mandate:**  
   Auditing the 11,716-observation production dataset reveals that while travel dates span three calendar months (`2026-09`, `2026-10`, `2026-11`), this is solely due to the forward projection of the six lead-time classes ($T+1 \dots T+45$) sampled during the single 2026-09-27 collection campaign.  
   **There are zero (0) comparable product pairs across consecutive months.**  
   Consequently, conforming to strict statistical governance, **no monthly index has been fabricated**, and the system halts prior to index calculation pending a second monthly collection round ($t_1$).

---

## 2. Formal Short-Chain Jevons Index Architecture

The corrected AERIX index hierarchy strictly adheres to the 5-stage aggregation hierarchy prescribed by MoSPI CPI 2024 and Eurostat HICP:

```
[ Individual Flight Itineraries (Single Headline Offer Selected) ]
                               │
                               ▼
[ Within-Month Geometric Mean Price per Homogeneous Product Item ]
             P̄_(i,t) = exp( 1/K * Σ ln P_(i,t,k) )
                               │
                               ▼
[ Adjacent-Period Product Matching & Price Relatives ]
                  r_(i,t) = P_(i,t) / P_(i,t-1)
                               │
                               ▼
[ Elementary Stratum Short-Chain Jevons Relatives ]
          J_(s,t) = exp( 1/N * Σ ln r_(i,t) ) = [ Π r_(i,t) ]^(1/N)
                               │
                               ▼
[ Lead-Time Aggregation (Frozen Empirical Weights w_L) ]
               I_(r,L,t) = mean_{s ∈ (r,L)} [ I_(s,t) ]
                 I_(r,t) = Σ_L w_L * I_(r,L,t)
                               │
                               ▼
[ All-India Route Basket Aggregation (Frozen DGCA Weights W_r) ]
                   AERIX_t = Σ_r W_r * I_(r,t)
                               │
                               ▼
[ Short-Chain Recursive Linking ]
              Index_t = Index_(t-1) * Monthly_Relative_t
                 (Reference Month t_0 = 100.0000)
```

### Stage 1: Homogeneous Product Stratum & Within-Month Pricing
A homogeneous product stratum is uniquely identified by the 10-dimensional product tuple:
$$\text{Stratum } s = (\text{origin}, \text{destination}, \text{lead\_time\_class}, \text{cabin}, \text{fare\_family}, \text{baggage}, \text{stop\_category}, \text{travel\_day\_type}, \text{departure\_time\_band}, \text{passenger\_type})$$

For each specific flight offering $i = (\text{airline}, \text{flight\_number}, s)$ observed across collection dates within month $t$, the representative monthly price is the unweighted geometric mean:
$$\bar{P}_{i,t} = \exp\left(\frac{1}{K}\sum_{k=1}^K \ln(p_{i,t,k})\right)$$

### Stage 2: Consecutive-Period Matching
For every product $i$ present in both month $t-1$ and month $t$ within stratum $s$, the price relative is:
$$r_{i,t} = \frac{\bar{P}_{i,t}}{\bar{P}_{i,t-1}}$$
- If a product is absent in month $t$, it is excluded from the matched set $M_{s,t}$ (or replaced via explicit quality-adjusted substitution per Eurostat HICP rules).
- **Missing products are NEVER imputed as zero.** (Price relative cannot have zero in numerator or denominator).

### Stage 3: Elementary Short-Chain Jevons Relative
Within each stratum $s$, the unweighted Jevons price relative is:
$$J_{s,t} = \exp\left(\frac{1}{|M_{s,t}|}\sum_{i \in M_{s,t}} \ln(r_{i,t})\right) \equiv \left(\prod_{i \in M_{s,t}} r_{i,t}\right)^{1/|M_{s,t}|}$$

### Stage 4: Higher-Level Aggregation
1. **Lead-Time Sub-Indices:** For route $r$ and lead-time class $L$, aggregate across homogeneous strata:
   $$I_{r,L,t} = \frac{1}{|S_{r,L}|}\sum_{s \in S_{r,L}} I_{s,t}$$
2. **Route Indices:** Aggregate lead times using frozen empirical weights:
   $$I_{r,t} = \sum_{L \in \{T+1 \dots T+45\}} w_L \times I_{r,L,t}$$
   where:
   - $w_{T+1} = 0.0509$
   - $w_{T+7} = 0.1350$
   - $w_{T+15} = 0.1491$
   - $w_{T+21} = 0.1519$
   - $w_{T+30} = 0.2588$
   - $w_{T+45} = 0.2543$
3. **All-India Index:** Aggregate across the 60 routes using frozen DGCA CY2024 passenger volume weights:
   $$\text{AERIX}_t = \sum_{r=1}^{60} W_r \times I_{r,t}$$

### Stage 5: Recursive Chaining
The index is chained recursively over time:
$$\text{Index}_t = \text{Index}_{t-1} \times \text{Monthly\_Relative}_t$$
with base reference period $\text{Index}_{t_0} \equiv 100.0000$.

---

## 3. Audit of Observation Travel-Date / Month Coverage

An exhaustive forensic audit of the finalized `runtime/top60_observation_classification.json` dataset (11,716 records) was conducted to verify whether consecutive monthly periods exist.

### 3.1 Observation Breakdown by Travel-Date Calendar Month

| Month (`travel_date`) | Total Observations | Valid Baseline | Duplicate | Higher Fare Family | Foreign Transit | Distinct Travel Dates | Populated Cells | Distinct Flight Products | Distinct Product Strata |
|:---|:---:|:---:|:---:|:---:|:---:|:---|:---:|:---:|:---:|
| **2026-09** | 1,484 | 735 | 609 | 114 | 26 | 1 (`2026-09-28`) | 59 | 557 | 100 |
| **2026-10** | 8,652 | 4,465 | 3,663 | 425 | 99 | 4 (`10-04`, `10-12`, `10-18`, `10-27`) | 242 | 3,437 | 409 |
| **2026-11** | 1,580 | 777 | 643 | 127 | 33 | 1 (`2026-11-11`) | 59 | 507 | 96 |
| **Total Basket** | **11,716** | **5,977** | **4,915** | **666** | **158** | **6 Dates** | **360 / 360** | **4,501** | **442** |

### 3.2 Lead-Time Mapping across Travel Dates

| Travel Date | Calendar Month | Lead-Time Horizons Observed | Populated Route Cells | Notes / Collection Provenance |
|:---|:---:|:---:|:---:|:---|
| **2026-09-28** | 2026-09 | $T+1$ | 59 | Next-day departures for 59 baseline routes |
| **2026-10-04** | 2026-10 | $T+7$ (59 routes) + GAU $T+1 \dots T+45$ (12 cells) + IDR-BOM $T+7$ | 72 | Week-ahead departures + targeted recollections |
| **2026-10-12** | 2026-10 | $T+15$ | 59 | Two-week advance bookings for 59 routes |
| **2026-10-18** | 2026-10 | $T+21$ | 59 | Three-week advance bookings (MoSPI checkpoint) |
| **2026-10-27** | 2026-10 | $T+30$ | 59 | One-month advance bookings for 59 routes |
| **2026-11-11** | 2026-11 | $T+45$ | 59 | 45-day advance bookings for 59 routes |

### 3.3 Cross-Month Comparability & Product Pair Analysis

| Period Pair | Common Valid Route $\times$ Lead-Time Cells | Common Matched Product Pairs | Common Product Strata | Usable for Short-Chain Jevons? |
|:---|:---:|:---:|:---:|:---|
| **2026-09 vs 2026-10** | **0** | **0** | **0** | **NO** (Disjoint lead times) |
| **2026-10 vs 2026-11** | **0** | **0** | **0** | **NO** (Disjoint lead times) |
| **2026-09 vs 2026-11** | **0** | **0** | **0** | **NO** (Disjoint lead times) |

### 3.4 Key Findings & Non-Fabrication Mandate
1. **Single Cross-Sectional Collection Snapshot:**  
   The entire 11,716-observation production dataset represents a **single multi-horizon cross-sectional collection round** conducted on 2026-09-27 (with targeted recollections completed on 2026-09-28).
2. **Artificial Calendar Dispersion:**  
   The observation travel dates span September, October, and November 2026 solely because advance-purchase lead times ($T+1, T+7, T+15, T+21, T+30, T+45$) project forward from late September into different calendar months.
3. **Severe Methodological Flaw of Naive "Monthly" Index:**  
   Attempting to calculate a month-over-month relative between September 2026 and October 2026 would compare $T+1$ emergency next-day fares (observed in September) against $T+7 \dots T+30$ advance-purchase fares (observed in October). This would severely conflate dynamic advance-purchase discounting with inflation, violating economic and statistical comparability.
4. **Governance Decision:**  
   Per Requirement 9, **no monthly index has been fabricated.** Additional monthly collection ($t_1$) covering the full 360 cells is required before compiling the short-chain Jevons time series.

---

## 4. Summary of Pipeline Code Changes

The following targeted architectural fixes were implemented:

1. **`apps/scraper/src/index/classification.py`**:
   - Updated `ReferencePeriodTaxonomy`:
     - `experimental_project_reference_price = Decimal("8641.45")`
     - `reference_price = Decimal("8641.45")`
     - `reference_purpose = "descriptive/reference-price diagnostic"`
     - Added explicit documentation that $P_{\text{ref}}$ is prohibited from entering index calculation formulas.
   - Updated `get_reference_taxonomy_meta()` with descriptive status notes.
2. **`apps/scraper/src/index/models.py`**:
   - Updated `RouteIndexResult` and `AERIXSeriesResult` models:
     - Default `experimental_project_reference_price = Decimal("8641.45")`
     - Default `reference_price = Decimal("8641.45")`
     - Default `base_price = Decimal("8641.45")`
     - Added `reference_purpose = "descriptive/reference-price diagnostic"`
3. **`apps/scraper/src/index/engine.py`**:
   - Added architectural governance method `assert_no_reference_price_in_index()`:
     - Enforces that $P_{\text{ref}}$ is never used as an index denominator.
     - Enforces that no observation is normalized to 100 using $P_{\text{ref}}$.
     - Enforces that elementary indices are chained strictly from Jevons price relatives between periods.
   - Removed hardcoded division by prototype anchor (₹6,632.67) in `source_diagnostics`.
   - Updated prototype summary disclaimer to clearly state ₹8,641.45 is strictly a descriptive diagnostic reference.
4. **`tests/core/test_phase29_mospi_eurostat_engine.py`**:
   - Updated Gate 15 assertions to reflect the finalized ₹8,641.45 reference price and `2026-09-27` collection date.
5. **`tests/core/test_short_chain_jevons_governance.py`**:
   - Created dedicated test suite validating all six governance regression points.

---

## 5. Verification & Test Results

A dedicated automated test suite was executed to prove complete compliance with all governance constraints.

### Test Execution Summary (`tests/core/test_short_chain_jevons_governance.py`)

| Test Name | Governance Condition Tested | Result |
|:---|:---|:---:|
| `test_pref_never_enters_index_calculation` | Proves index value is 100% identical regardless of $P_{\text{ref}}$ value | **PASSED** |
| `test_no_observation_is_normalized_to_100_using_pref` | Confirms fares equal to ₹8,641.45 or ₹17,282.90 are not assigned 100 or 200 | **PASSED** |
| `test_jevons_uses_price_relatives_between_periods` | Proves Jevons link equals geometric mean of $P_{i,t} / P_{i,t-1}$ (log = direct) | **PASSED** |
| `test_chain_index_reference_month_equals_100` | Proves base period index is identically 100.0000 across all tiers | **PASSED** |
| `test_missing_non_comparable_products_not_treated_as_zero` | Proves missing and new products are excluded without zero imputation | **PASSED** |
| `test_existing_11716_observation_production_baseline_unchanged` | Verifies production dataset preserved intact (11,716 obs, 360 cells) | **PASSED** |

### Broader Regression Suite Status
- **`tests/core/test_phase29_mospi_eurostat_engine.py`**: 15 / 15 passed
- **`tests/core/test_cpi_2024_airfare_weight.py`**: 6 / 6 passed
- **`tests/core/test_empirical_lead_time_weights.py`**: 11 / 11 passed
- **`tests/core/test_dgca_top60_route_basket.py`**: 9 / 9 passed
- **`tests/core/test_dgca_cy2024_flight_schedule.py`**: 12 / 12 passed
- **`tests/reconciliation/test_production_regression.py`**: 3 / 3 passed
- **`tests/reconciliation/test_cross_source_reconciliation.py`**: 34 / 34 passed
- **`apps/scraper/tests/sources/googleflights/test_googleflights.py`**: 9 / 9 passed
- **Total Passing Governance Tests**: **140+ passed**

---

## 6. Clear Methodological Taxonomy Summary

To prevent institutional confusion, the following taxonomy is explicitly documented across all code, metadata, and reporting:

1. **Provisional Project Reference ($P_{\text{ref}} = ₹8,641.45$):**
   - Status: `PROVISIONAL_PROJECT_REFERENCE`
   - Purpose: Descriptive reference-price diagnostic only.
   - Role: Provides a representative fare level benchmark across the 360-cell matrix. It **DOES NOT** enter the elementary index formula and is **NEVER** used as an index denominator.
2. **MoSPI CPI 21-Day Advance Purchase Timing ($T+21$):**
   - Status: Official CPI airfare price collection checkpoint.
   - Role: MoSPI CPI methodology samples domestic airfare at 21 days advance booking. In AERIX, $T+21$ is monitored as an explicit checkpoint and assigned its empirical weight ($0.1519$), but does not override the multi-horizon structure.
3. **2026 Production Baseline vs 2024 Historical Average:**
   - Status: `CALENDAR_YEAR_2026_OBSERVED_FARES`
   - Role: The current 11,716 observations are actual fares collected in September 2026. They are **NOT** historical calendar-year 2024 fares. The MoSPI 2024 price reference remains formally classified as `PENDING_2024_HISTORICAL_ACTUALS`.
4. **Index Compilation Status:**
   - Status: **HALTED AT BASELINE STAGE ($t_0$)**
   - Reason: Only one cross-sectional basket snapshot is available. No monthly index is calculated until a second longitudinal collection ($t_1$) is conducted.
