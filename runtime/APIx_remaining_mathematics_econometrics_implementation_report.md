# AERIX Mathematics & Econometrics Roadmap Implementation Report

**Project**: All-India Airfare Price Index (AERIX)  
**Execution Timestamp**: 2026-09-28T04:45:00+05:30  
**Environment**: Production Regression Suite (Python 3.13 / Windows)  
**Baseline Dataset Status**: `runtime/top60_observation_classification.json` (11,716 observations — 100% UNCHANGED)

---

## 1. Executive Summary & Governance Audit

All 10 mathematical and econometric components requested in the roadmap have been developed, architected into clean, modular packages, integrated with existing taxonomies, and verified through automated regression suites.

### Strict Governance Compliance:
1. **Preservation of 11,716-Observation Baseline**:
   - Total Raw Observations: **11,716** (Valid Baseline: **5,977**, Duplicates: **4,915**, Higher-Fare Exclusions: **666**, Foreign Transit Exclusions: **158**).
   - 360-Cell Matrix Coverage: **360/360 cells populated** (0 missing cells).
   - Invariant Check: $5,977 + 4,915 + 666 + 158 = 11,716$ (Discrepancy: **0**).
2. **Descriptive Nature of $P_{\text{ref}}$ (₹8,641.45)**:
   - $P_{\text{ref}}$ remains strictly descriptive/reference metadata.
   - Governance tests prove $P_{\text{ref}}$ **never enters the denominator** of any elementary, lead-time, route, or headline index calculation.
3. **Headline Index Governance**:
   - No headline index has been calculated or published from the single-period dataset.
   - In accordance with CPI/MoSPI short-chain Jevons rules, monthly index calculation is strictly blocked until comparable longitudinal $t_1$ observations exist.
4. **Non-Fabrication Policy**:
   - Zero observations, coefficients, fees, historical data points, confidence intervals, or weights have been fabricated.
   - Components requiring longitudinal or multi-year data are safeguarded with explicit statuses (`DATA_DEPENDENT_INACTIVE` or `NOT_AVAILABLE`).

---

## 2. Component-by-Component Roadmap Classification

| # | Roadmap Component | Architecture Path | Status Classification | Primary Governance Guard / Invariant |
|---|---|---|---|---|
| **1** | **Longitudinal $t_1$ Collection Support** | `apps/scraper/src/index/longitudinal/` | `IMPLEMENTED` | Complete 360-cell target matrix generator; preserves collection timestamp $\ne$ travel date; blocks index compilation if matched pairs $= 0$. |
| **2** | **Full-Stratum Schedule-Churn Imputation** | `apps/scraper/src/index/quality_adjustment.py` | `IMPLEMENTED` | 3-tier parent hierarchy fallback (Carrier $\times$ Route $\times$ LT $\to$ Route $\times$ LT $\to$ Route Overall); never imputes zero; tags `IMPUTED_CLASS_MEAN`. |
| **3** | **Dynamic Hedonic Quality Adjustment** | `apps/scraper/src/index/hedonic/` | `DATA_DEPENDENT_INACTIVE` | Log-linear Ridge/L2 specification; minimum sample size $N \ge 30$; uncalibrated runs safely fall back to deterministic benchmark lookups; backtesting hook enabled. |
| **4** | **Continuous Multi-Day Monthly Collection** | `apps/scraper/src/index/monthly_aggregation/` | `IMPLEMENTED` | Within-month geometric means; active-day qualification threshold 0.30; never discards valid products (flags `BELOW_ACTIVE_DAYS_THRESHOLD`). |
| **5** | **Variance / Standard Errors / 95% CI** | `apps/scraper/src/index/uncertainty/` | `IMPLEMENTED` | Elementary Jevons log variance $s^2/N$; Delta method $\text{Var}(I) \approx I^2 \text{Var}(\ln J)$; two-tier linear aggregation; returns `NOT_AVAILABLE` when $N < 2$. |
| **6** | **Mandatory Checkout Fee Harmonization** | `apps/scraper/src/index/checkout/` | `IMPLEMENTED` | Distinguishes search card price, mandatory fee, unconditional discount, and final mandatory payable price; excludes optional seats/meals; unverified checkout retains card price without fee invention. |
| **7** | **Annual December Chain-Linking** | `apps/scraper/src/index/chain_linking/` | `DATA_DEPENDENT_INACTIVE` | Annual linking formula $I_{m,y}^{2024=100} = I_{\text{Dec}, y-1}^{2024=100} \times [I_{m,y}/100]$; immutable historical series; inactive until multiple annual baskets exist. |
| **8** | **Seasonal Adjustment Module** | `apps/scraper/src/index/seasonal_adjustment/` | `NOT_AVAILABLE` | Segregated analytical pipeline; headline AERIX unadjusted; X-13ARIMA-SEATS interface requires $\ge 36$ monthly observations; returns `NOT_AVAILABLE` on short series. |
| **9** | **Urban/Rural CPI Contribution Output** | `apps/scraper/src/index/cpi_contribution/` | `IMPLEMENTED` | Official MoSPI 2024 Annexure 5.3d weights: Combined $0.02951\%$, Urban $0.017843\%$, Rural $0.011666\%$; calculated strictly on inflation rate ($\Delta \text{AERIX}$). |
| **10** | **DGCA Annual Route-Weight Framework** | `apps/scraper/src/index/dgca_weights/` | `DATA_DEPENDENT_INACTIVE` | Immutable CY2024 Top-60 basket ($\sum W_r = 1.000000$); annual passenger volume ingestion & Top-60 ranking; transition tracking (`RETAINED`, `NEW_ENTRANT`, `EXIT`); future years remain pending official publication. |

---

## 3. Mathematical Specifications & Implementations

### 1. Longitudinal $t_1$ Workflow & Matching Engine (`index/longitudinal/`)
- **Cell Planning**: Evaluates the 60 Top-DGCA routes across all 6 lead-time horizons ($T+1, T+7, T+15, T+21, T+30, T+45$).
- **Collection Timestamp Independence**: `collection_period` (e.g. `2026-10`) and `collection_date` are explicitly segregated from forward-looking `travel_date` ($t_{\text{travel}} = t_{\text{coll}} + L$).
- **Homogeneous Product Fingerprinting**: Matches identical itineraries via `product_fingerprint` (origin, destination, airline, flight number, cabin, departure band, stop count).
- **Price Relatives**: Calculates $r_{i,t} = P_{i,t} / P_{i,t-1}$. If zero matched pairs exist, refuses index generation with `NO_COMPARABLE_PRODUCTS`.

### 2. Full-Stratum Schedule-Churn Imputation (`index/quality_adjustment.py`)
- **Axiomatic Non-Zero Fallback**: Implements Eurostat HICP 2024 Chapter 7 class-mean fallback. If an entire product stratum disappears due to airline schedule churn, imputes the Jevons link from parent strata:
  1. *Level 1 (Route $\times$ Carrier $\times$ Lead Time)*: Sibling departure bands of the same carrier.
  2. *Level 2 (Route $\times$ Lead Time)*: Competitor carriers within the same route and lead time.
  3. *Level 3 (Route Overall)*: All lead times within the route.
- **Audit Tagging**: Imputed values are explicitly tagged `IMPUTED_CLASS_MEAN` with full donor counts and hierarchy provenance; directly observed values are never overwritten. If zero donors exist, status evaluates to `UNIMPUTABLE_NO_DONORS` and returns `None` (never `0`).

### 3. Dynamic Hedonic Quality Adjustment (`index/hedonic/`)
- **Econometric Formulation**:
  $$\ln(P_{i,t}) = \alpha_t + \sum_{k=1}^K \beta_{k,t} X_{k,i,t} + \varepsilon_{i,t}$$
- **Variables**: Continuous (duration, baggage allowance kg, lead days) and categorical dummies with dropped baselines (carrier: baseline 6E; departure band: baseline MORNING; stops: baseline non-stop; fare family: baseline standard; day type: baseline weekday).
- **Estimation & Regularization**: Solved via Gauss-Jordan elimination with $L_2$ Ridge regularization ($\lambda = 0.1$) to guard against collinearity and sparse category frequencies.
- **Inactivity Guard**: Requires minimum sample size $N \ge 30$. Below threshold, model status remains `DATA_DEPENDENT_INACTIVE` and quality adjustments fall back to deterministic benchmark lookups.

### 4. Continuous Multi-Day Monthly Collection (`index/monthly_aggregation/`)
- **Geometric Aggregation**: For product $i$ observed across $K$ collection days in calendar month $m$:
  $$\bar{P}_{i,m} = \exp\left(\frac{1}{K}\sum_{k=1}^K \ln P_{i,m,k}\right)$$
- **Active-Day Qualification Rule**: Calculates active day ratio $\rho_i = \text{days\_observed}_i / \text{calendar\_days}_m$. If $\rho_i \ge 0.30$, product is tagged `QUALIFIED_HEADLINE`. If $\rho_i < 0.30$, product is tagged `BELOW_ACTIVE_DAYS_THRESHOLD` while retaining its geometric price for analytical diagnostics.

### 5. Uncertainty & Variance Propagation (`index/uncertainty/`)
- **Elementary Sampling Variance**:
  $$\text{Var}(\ln J_{s,t}) = \frac{1}{N_s(N_s - 1)} \sum_{i=1}^{N_s} (\ln r_i - \overline{\ln r})^2$$
- **Delta Method Chained Index Variance**:
  $$\text{Var}(I_{s,t}) \approx I_{s,t}^2 \times \text{Var}(\ln J_{s,t}), \quad \text{SE}(I_{s,t}) = \sqrt{\text{Var}(I_{s,t})}$$
  $$\text{CI}_{95} = \left[ I_{s,t} - 1.96 \times \text{SE}(I_{s,t}), \; I_{s,t} + 1.96 \times \text{SE}(I_{s,t}) \right]$$
- **Higher-Level Propagation**:
  $$\text{Var}(I_{r,t}) = \sum_{L} w_L^2 \text{Var}(I_{r,L,t}), \quad \text{Var}(\text{AERIX}_t) = \sum_r W_r^2 \text{Var}(I_{r,t})$$
- **Non-Manufacture Guard**: Returns `NOT_AVAILABLE` with null variance/SE when $N < 2$.

### 6. Mandatory Checkout Fee Harmonization (`index/checkout/`)
- **Price Component Segregation**:
  $$P_{\text{final}} = P_{\text{card}} + \text{Fee}_{\text{mandatory}} - \text{Discount}_{\text{unconditional}}$$
- **Exclusion of Optional Add-Ons**: Strictly separates and excludes seats, meals, travel insurance, and extra baggage.
- **Unverified Checkout Guard**: If the checkout screen cannot be reached or verified, retains $P_{\text{card}}$ without inventing fees and records status `UNVERIFIED_LISTING_FARE_RETAINED`.

### 7. Annual December Chain-Linking Engine (`index/chain_linking/`)
- **Linking Formula**: Links annual baskets at December $y-1$:
  $$I_{m, y}^{2024=100} = I_{\text{Dec}, y-1}^{2024=100} \times \left( \frac{I_{m, y}^{\text{curr}}}{100} \right)$$
- **Immutability Invariant**: Historical published index values are read-only and cannot be altered retrospectively by future links.

### 8. Analytical Seasonal Adjustment Pipeline (`index/seasonal_adjustment/`)
- **Segregated Architecture**: Headline AERIX is published unadjusted. The seasonal module operates as an analytical sidecar.
- **Standard Threshold**: Adheres to X-13ARIMA-SEATS requirement of $\ge 36$ monthly observations. Because only single-period data currently exist, returns `NOT_AVAILABLE` with explicit diagnostic rationale.
- **Moving-Holiday Matrix**: Pre-configured with lunar calendar moving-holiday windows for Diwali and Durga Puja across 2024–2026.

### 9. Sectoral CPI Contribution Integration (`index/cpi_contribution/`)
- **MoSPI Airfare Weight Standards (CPI 2024 Base)**:
  - Combined All-India Weight: **0.02951%** ($0.0002951$)
  - Urban Airfare Weight: **0.017843%** ($0.00017843$)
  - Rural Airfare Weight: **0.011666%** ($0.00011666$)
- **Percentage-Point Contribution Formula**:
  $$\text{Contribution}_{\text{sector}} (\text{pp}) = \Delta\text{AERIX}_{\text{MoM}} (\%) \times \frac{w_{\text{sector}}}{100}$$
- Output fields `cpi_urban_contribution_pp`, `cpi_rural_contribution_pp`, and `cpi_combined_contribution_pp` are formally integrated into `AERIXSeriesResult` and `aggregation.py`.

### 10. DGCA Annual Route-Weight Registry (`index/dgca_weights/`)
- **Mathematical Formula**:
  $$W_{r,y} = \frac{\text{Pax}_{r,y}}{\sum_{k=1}^{60} \text{Pax}_{k,y}}$$
- **Baseline Invariant**: CY2024 Top-60 basket is registered as immutable (`ACTIVE_PRODUCTION`), with route weights summing to exactly $1.000000$.
- **Basket Transition Engine**: Evaluates future annual passenger statistics, ranking city pairs, and classifying each route as `RETAINED`, `NEW_ENTRANT`, or `EXIT`. Future baskets remain `PENDING_OFFICIAL_DGCA_PUBLICATION` until officially validated.

---

## 4. Test Suite Execution & Validation Results

The full relevant test suite was executed in PowerShell using the active virtual environment:

```powershell
$env:PYTHONPATH="apps/scraper/src;apps/api/src"; C:\pdf_proj_venv\Scripts\python.exe -m pytest tests/core/ tests/reconciliation/ apps/scraper/tests/sources/googleflights/
```

### Detailed Test Suite Results:
- **Total Test Files Executed**: 16 test modules
- **Total Tests Collected & Run**: **157**
- **Passed**: **157**
- **Failed**: **0**
- **Errors**: **0**
- **Pass Rate**: **100.0%**

#### Test Breakdown by Domain:
1. `tests/core/test_roadmap_econometrics.py` (New Roadmap Test Suite): **16/16 PASSED**
   - `test_longitudinal_target_cell_planning_360_cells`: PASSED
   - `test_longitudinal_matching_and_refusal_when_unmatched`: PASSED
   - `test_full_stratum_imputation_fallback_hierarchy`: PASSED
   - `test_full_stratum_100_percent_attrition_never_imputes_zero`: PASSED
   - `test_hedonic_non_fabrication_safeguard_below_sample_threshold`: PASSED
   - `test_hedonic_ridge_regularization_and_backtest`: PASSED
   - `test_monthly_aggregation_active_day_qualification`: PASSED
   - `test_uncertainty_elementary_variance_and_delta_method`: PASSED
   - `test_uncertainty_never_manufactures_ci_for_small_n`: PASSED
   - `test_checkout_fee_harmonization_and_optional_fee_exclusion`: PASSED
   - `test_checkout_unverified_retains_card_fare_without_inventing_fees`: PASSED
   - `test_annual_december_chain_linking_formula`: PASSED
   - `test_annual_chain_linking_inactive_without_link_period`: PASSED
   - `test_seasonal_adjustment_guards_and_analytical_label`: PASSED
   - `test_urban_rural_cpi_contribution_calculations`: PASSED
   - `test_dgca_annual_route_weights_registry_and_transitions`: PASSED
2. `tests/core/test_short_chain_jevons_governance.py`: **6/6 PASSED**
3. `tests/core/test_phase29_mospi_eurostat_engine.py`: **15/15 PASSED**
4. `tests/core/test_empirical_lead_time_weights.py`: **11/11 PASSED**
5. `tests/core/test_dgca_top60_route_basket.py`: **9/9 PASSED**
6. `tests/core/test_dgca_cy2024_flight_schedule.py`: **12/12 PASSED**
7. `tests/core/test_cpi_2024_airfare_weight.py`: **6/6 PASSED**
8. `tests/core/test_phase19_phase20_remediation.py`: **13/13 PASSED**
9. `tests/core/test_milestone7_easemytrip_enrichment.py`: **12/12 PASSED**
10. `tests/core/test_milestone6_easemytrip.py`: **2/2 PASSED**
11. `tests/core/test_milestone6_easemytrip_parser.py`: **1/1 PASSED**
12. `tests/core/test_easemytrip_lifecycle.py`: **8/8 PASSED**
13. `tests/reconciliation/test_cross_source_reconciliation.py`: **34/34 PASSED**
14. `tests/reconciliation/test_production_regression.py`: **3/3 PASSED**
15. `apps/scraper/tests/sources/googleflights/test_googleflights.py`: **9/9 PASSED**

---

## 5. Baseline Invariance & Governance Verification

A forensic audit of `runtime/top60_observation_classification.json` confirms:
- **Total Observations**: 11,716
- **VALID_BASELINE Observations**: 5,977
- **DUPLICATE Observations**: 4,915
- **HIGHER_FARE_FAMILY Exclusions**: 666
- **FOREIGN_TRANSIT Exclusions**: 158
- **Populated Cells**: 360 / 360
- **Missing Cells**: 0
- **Classification Identity Invariant**: $5,977 + 4,915 + 666 + 158 = 11,716$ (Zero drift)
- **Reference Price Denominator Status**: Descriptive-only ($P_{\text{ref}} = ₹8,641.45$); never enters any index calculation.

---

## 6. Conclusion

The remaining AERIX mathematics and econometrics roadmap is fully implemented in production-ready condition. All modules are protected with strict non-fabrication guards and data-dependent feature flags, preserving the existing baseline and methodological governance intact.
