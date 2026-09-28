# APIx Synthetic August 2026 Demonstration & Validation Report

**Generation Timestamp**: 2026-09-28T00:21:25.960161+00:00  
**Dataset Name**: `APIx_Synthetic_August_2026_Longitudinal_Demonstration`  
**Generation Version**: `AUG2026_DEMO_V1`  
**Random Seed**: `42` (100% Deterministic & Reproducible)  
**Data Status**: `SYNTHETIC`  

---

## 1. Strict Governance & Non-Contamination Statement

> [!CAUTION]
> **EXPLICIT NON-HISTORICAL DISCLAIMER**  
> This dataset is **SYNTHETIC** and was generated strictly to demonstrate and validate the daily, weekly, and monthly APIx econometric calculation pipeline. It **MUST NEVER** be presented, cited, or published as observed historical Indian airfare data.

> [!IMPORTANT]
> **DATASET SEPARATION INVARIANT**  
> The real production dataset (`runtime/top60_observation_classification.json`, containing 11,716 verified observations) remains **100% UNCHANGED and uncontaminated**. No synthetic record has been written to the production database or merged into real observations.
> August synthetic data and September real data are strictly segregated. No cross-month inflation rates (e.g. August-to-September inflation) are calculated or published.

---

## 2. Dataset Architecture & Empirical Source Distribution

The synthetic panel was constructed using the real 5,977 `VALID_BASELINE` observations from `runtime/top60_observation_classification.json` as the empirical distribution template across all 60 DGCA routes and 6 lead-time classes (360 cells):

- **Collection Calendar Days**: 31 days (2026-08-01 through 2026-08-31)
- **Total Synthetic Observations**: 133,148
- **Average Daily Collection Volume**: 4,295.1 quotes/day (order of magnitude ~4,300/day matches the real collection basket)
- **Canonical Product Pool**: 5,977 distinct flight products
- **Route Basket**: 60 Top DGCA routes (sum of weights = 1.000000)
- **Lead-Time Classes**: 6 classes (T+1, T+7, T+15, T+21, T+30, T+45; sum of weights = 1.0000)
- **Cell Matrix**: Exactly 360 / 360 cells populated

### Econometric Perturbation Formulation:
For product $i$ on August day $d$ with forward-looking travel date $t_{\text{travel}} = t_{\text{coll}} + L$:
$$\ln P_{i, d} = \ln P_i^0 + \mu_r(d) + \gamma_L(d) + \delta_{\text{day\_type}}(d) + \varepsilon_{i, d}$$
Where:
- $P_i^0$: Empirical baseline price from the real production dataset.
- $\mu_r(d) = 0.7 \mu_r(d-1) + \eta_r(d)$ with $\eta_r(d) \sim \mathcal{N}(0, 0.008^2)$: Route-level common market shock with realistic autoregressive persistence.
- $\gamma_L(d) \sim \mathcal{N}(0, 0.005^2)$: Lead-time class variation.
- $\delta_{\text{day\_type}}(d) = +0.015$ for Friday and Sunday travel dates (weekend travel surge).
- $\varepsilon_{i, d} \sim \mathcal{N}(0, 0.012^2)$: Idiosyncratic daily price movement with occasional small yield shifts.
- Plausibility floor: $P_{i, d} = \max(\text{round}(\exp(\ln P_{i, d}), 2), 1200.00)$ (zero negative or impossible fares).
- Schedule presence: Product presence sampled with intrinsic schedule frequency $p_i \in [0.50, 0.94]$, preserving realistic schedule churn and active-day variation without artificial 100% daily availability.

---

## 3. Daily Demonstration APIx Series (August 1 to 31, 2026)

Calculated using consecutive daily short-chain Jevons price relatives ($r_{i,d} = P_{i,d} / P_{i,d-1}$), weighted empirical lead-time aggregation ($w_L$), and DGCA Top-60 route weights ($W_r$):

| Date | Day | Matched Pairs | Daily Relative | Daily Chain Index | Std Error | 95% CI Lower | 95% CI Upper |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `2026-08-01` | 01 | 4,333 | 1.000000 | **100.0000** | ±0.0000 | 100.00 | 100.00 |
| `2026-08-02` | 02 | 3,227 | 1.001874 | **100.1874** | ±0.7881 | 98.64 | 101.73 |
| `2026-08-03` | 03 | 3,205 | 0.994567 | **99.6431** | ±0.7811 | 98.11 | 101.17 |
| `2026-08-04` | 04 | 3,197 | 1.008042 | **100.4444** | ±0.7956 | 98.88 | 102.00 |
| `2026-08-05` | 05 | 3,249 | 0.996773 | **100.1203** | ±0.8524 | 98.45 | 101.79 |
| `2026-08-06` | 06 | 3,215 | 1.004092 | **100.5300** | ±0.7617 | 99.04 | 102.02 |
| `2026-08-07` | 07 | 3,223 | 0.999808 | **100.5107** | ±0.8063 | 98.93 | 102.09 |
| `2026-08-08` | 08 | 3,256 | 0.996114 | **100.1202** | ±0.7992 | 98.55 | 101.69 |
| `2026-08-09` | 09 | 3,207 | 1.000103 | **100.1305** | ±0.8456 | 98.47 | 101.79 |
| `2026-08-10` | 10 | 3,206 | 0.999151 | **100.0455** | ±0.7985 | 98.48 | 101.61 |
| `2026-08-11` | 11 | 3,199 | 1.002215 | **100.2671** | ±0.8065 | 98.69 | 101.85 |
| `2026-08-12` | 12 | 3,162 | 0.997608 | **100.0273** | ±0.8426 | 98.38 | 101.68 |
| `2026-08-13` | 13 | 3,170 | 1.008645 | **100.8920** | ±0.8764 | 99.17 | 102.61 |
| `2026-08-14` | 14 | 3,176 | 0.995952 | **100.4836** | ±0.8368 | 98.84 | 102.12 |
| `2026-08-15` | 15 | 3,154 | 0.995603 | **100.0418** | ±0.7514 | 98.57 | 101.51 |
| `2026-08-16` | 16 | 3,168 | 1.002721 | **100.3140** | ±0.8202 | 98.71 | 101.92 |
| `2026-08-17` | 17 | 3,200 | 0.994637 | **99.7760** | ±0.8358 | 98.14 | 101.41 |
| `2026-08-18` | 18 | 3,165 | 1.002786 | **100.0540** | ±0.7794 | 98.53 | 101.58 |
| `2026-08-19` | 19 | 3,177 | 1.003861 | **100.4403** | ±0.7642 | 98.94 | 101.94 |
| `2026-08-20` | 20 | 3,205 | 1.005098 | **100.9524** | ±0.8187 | 99.35 | 102.56 |
| `2026-08-21` | 21 | 3,264 | 0.994775 | **100.4250** | ±0.8024 | 98.85 | 102.00 |
| `2026-08-22` | 22 | 3,168 | 0.999763 | **100.4012** | ±0.7626 | 98.91 | 101.90 |
| `2026-08-23` | 23 | 3,157 | 0.997588 | **100.1590** | ±0.8403 | 98.51 | 101.81 |
| `2026-08-24` | 24 | 3,156 | 0.997786 | **99.9372** | ±0.8315 | 98.31 | 101.57 |
| `2026-08-25` | 25 | 3,130 | 1.002622 | **100.1992** | ±0.8011 | 98.63 | 101.77 |
| `2026-08-26` | 26 | 3,125 | 1.002286 | **100.4283** | ±0.7842 | 98.89 | 101.97 |
| `2026-08-27` | 27 | 3,128 | 0.999352 | **100.3633** | ±0.8000 | 98.80 | 101.93 |
| `2026-08-28` | 28 | 3,223 | 1.006584 | **101.0240** | ±0.7940 | 99.47 | 102.58 |
| `2026-08-29` | 29 | 3,221 | 0.994353 | **100.4536** | ±0.8448 | 98.80 | 102.11 |
| `2026-08-30` | 30 | 3,161 | 1.002308 | **100.6854** | ±0.8415 | 99.04 | 102.33 |
| `2026-08-31` | 31 | 3,151 | 0.997262 | **100.4097** | ±0.8328 | 98.78 | 102.04 |

---

## 4. Weekly Demonstration APIx Series

August 2026 was grouped into 4 standard calendar weeks. Each product's intra-week representative price was computed via within-week geometric means, then chained week-over-week using short-chain Jevons:

| Week | Period Window | Observations | Matched Products | Weekly Relative | Weekly Chain Index | Std Error | 95% CI |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Week 1 (Aug 1 - Aug 7)** | `2026-08-01` to `2026-08-07` | 30,218 | 5,973 | 1.000000 | **100.0000** | ±0.0000 | [100.00, 100.00] |
| **Week 2 (Aug 8 - Aug 14)** | `2026-08-08` to `2026-08-14` | 30,082 | 5,968 | 1.000105 | **100.0105** | ±0.3135 | [99.40, 100.62] |
| **Week 3 (Aug 15 - Aug 21)** | `2026-08-15` to `2026-08-21` | 30,139 | 5,967 | 0.999702 | **99.9807** | ±0.3202 | [99.35, 100.61] |
| **Week 4 (Aug 22 - Aug 31)** | `2026-08-22` to `2026-08-31` | 42,709 | 5,971 | 1.000357 | **100.0164** | ±0.2875 | [99.45, 100.58] |

---

## 5. Monthly Demonstration Aggregation (August 2026)

Using `MonthlyAggregationEngine` with active-day qualification threshold **0.30** (minimum 10 collection days observed out of 31 calendar days):

- **Total Canonical Products Evaluated**: 5,977
- **Qualified Products (Active Ratio $\ge 0.30$)**: 5,967 (99.8%)
- **Disqualified Products (Active Ratio $< 0.30$)**: 10 (0.2%)
- **Populated Cells**: Exactly 360 / 360 cells populated
- **Synthetic August Representative Price**: **₹5,769.64**

> [!NOTE]
> P_ref (₹8,641.45) is strictly descriptive and was NOT used as a denominator in this monthly calculation.

---

## 6. Mathematical Governance Verification

1. **Reference Price ($P_{\text{ref}} = ₹8,641.45$) Governance**:
   - $P_{\text{ref}}$ is strictly descriptive and was **never used as a denominator** in the daily, weekly, or monthly index calculations.
   - All indices were calculated strictly from homogeneous product price relatives $r_{i,t} = P_{i,t} / P_{i,t-1}$.
2. **Weights Sum Invariants**:
   - Empirical Lead-Time Weights sum: $0.0509 + 0.1350 + 0.1491 + 0.1519 + 0.2588 + 0.2543 = 1.0000$ (Exact).
   - DGCA Top-60 Route Weights sum: $1.000000$ (Exact).
3. **Zero Contamination Verification**:
   - Production baseline `runtime/top60_observation_classification.json` remains exactly 11,716 observations.
   - Zero synthetic observations have been merged into real datasets.

---

## 7. Conclusion

The Synthetic August 2026 dataset successfully validates the end-to-end operation of the daily, weekly, and monthly APIx aggregation and uncertainty calculation engines without compromising or altering real historical observations.