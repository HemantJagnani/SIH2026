# APIx Synthetic Demonstration Report — August 2026

> [!CAUTION]
> **SYNTHETIC DATA — NOT REAL AIRFARE DATA**  
> This report describes calculations performed on a **SYNTHETIC** dataset generated solely to
> validate the APIx econometric pipeline. **These results MUST NEVER be cited, quoted, or
> published as observed Indian airfare inflation or real price movements.**

**Generated (UTC)**: `2026-09-28T00:33:27Z`  
**Data Label**: `SYNTHETIC_METHODOLOGY_DEMONSTRATION`  
**Generation Version**: `AUG2026_DEMO_V1`  
**Random Seed**: `42` (100% reproducible)  

---

## 1. Production Baseline Integrity

| Metric | Value |
|--------|-------|
| Real observations in production baseline | **11,716** |
| Synthetic records leaked into production | **0** ✅ |
| File SHA-256 (prefix) | `36be7b34ff101ad8a246018583b2e43a` |
| Verification status | **CLEAN** ✅ |

---

## 2. Frozen Weights

### Empirical Lead-Time Weights (from `Clean_Dataset.csv`)

| Lead-Time Class | Weight | % Share |
|:-:|:-:|:-:|
| T+1 | 0.0509 | 5.09% |
| T+7 | 0.1350 | 13.50% |
| T+15 | 0.1491 | 14.91% |
| T+21 | 0.1519 | 15.19% |
| T+30 | 0.2588 | 25.88% |
| T+45 | 0.2543 | 25.43% |
| **SUM** | **1.0000** | **100.00%** |

> [!NOTE]
> Route weights (60 DGCA CY2024 routes) sum to **1.000000**. See `route_basket.py`.

---

## 3. Daily Synthetic APIx Series

> [!IMPORTANT]  
> Index base: **Day 1 (2026-08-01) = 100.0000**.  
> Formula: `I_d = I_{d-1} × exp(mean_{r,L}(w_L × W_r × ln(P_t/P_{t-1})))`  
> P_ref (₹8,641.45) is **NEVER** used as a denominator.

| Date | Day | Observations | Matched Pairs | Daily Relative | Daily Index | SE | 95% CI Lower | 95% CI Upper | CI? |
|:----:|:---:|:------------:|:-------------:|:--------------:|:-----------:|:--:|:------------:|:------------:|:---:|
| `2026-08-01` | 01 | 4,333 | 4,333 | 1.000000 | **100.0000** | ±0.0000 | 100.00 | 100.00 | ✅ |
| `2026-08-02` | 02 | 4,308 | 3,227 | 1.001874 | **100.1874** | ±0.7881 | 98.64 | 101.73 | ✅ |
| `2026-08-03` | 03 | 4,290 | 3,205 | 0.994567 | **99.6431** | ±0.7811 | 98.11 | 101.17 | ✅ |
| `2026-08-04` | 04 | 4,332 | 3,197 | 1.008042 | **100.4444** | ±0.7956 | 98.88 | 102.00 | ✅ |
| `2026-08-05` | 05 | 4,316 | 3,249 | 0.996773 | **100.1203** | ±0.8524 | 98.45 | 101.79 | ✅ |
| `2026-08-06` | 06 | 4,304 | 3,215 | 1.004092 | **100.5300** | ±0.7617 | 99.04 | 102.02 | ✅ |
| `2026-08-07` | 07 | 4,335 | 3,223 | 0.999808 | **100.5107** | ±0.8063 | 98.93 | 102.09 | ✅ |
| `2026-08-08` | 08 | 4,324 | 3,256 | 0.996114 | **100.1202** | ±0.7992 | 98.55 | 101.69 | ✅ |
| `2026-08-09` | 09 | 4,332 | 3,207 | 1.000103 | **100.1305** | ±0.8456 | 98.47 | 101.79 | ✅ |
| `2026-08-10` | 10 | 4,272 | 3,206 | 0.999151 | **100.0455** | ±0.7985 | 98.48 | 101.61 | ✅ |
| `2026-08-11` | 11 | 4,314 | 3,199 | 1.002215 | **100.2671** | ±0.8065 | 98.69 | 101.85 | ✅ |
| `2026-08-12` | 12 | 4,267 | 3,162 | 0.997608 | **100.0273** | ±0.8426 | 98.38 | 101.68 | ✅ |
| `2026-08-13` | 13 | 4,311 | 3,170 | 1.008645 | **100.8920** | ±0.8764 | 99.17 | 102.61 | ✅ |
| `2026-08-14` | 14 | 4,262 | 3,176 | 0.995952 | **100.4836** | ±0.8368 | 98.84 | 102.12 | ✅ |
| `2026-08-15` | 15 | 4,265 | 3,154 | 0.995603 | **100.0418** | ±0.7514 | 98.57 | 101.51 | ✅ |
| `2026-08-16` | 16 | 4,302 | 3,168 | 1.002721 | **100.3140** | ±0.8202 | 98.71 | 101.92 | ✅ |
| `2026-08-17` | 17 | 4,326 | 3,200 | 0.994637 | **99.7760** | ±0.8358 | 98.14 | 101.41 | ✅ |
| `2026-08-18` | 18 | 4,269 | 3,165 | 1.002786 | **100.0540** | ±0.7794 | 98.53 | 101.58 | ✅ |
| `2026-08-19` | 19 | 4,292 | 3,177 | 1.003861 | **100.4403** | ±0.7642 | 98.94 | 101.94 | ✅ |
| `2026-08-20` | 20 | 4,308 | 3,205 | 1.005098 | **100.9524** | ±0.8187 | 99.35 | 102.56 | ✅ |
| `2026-08-21` | 21 | 4,377 | 3,264 | 0.994775 | **100.4250** | ±0.8024 | 98.85 | 102.00 | ✅ |
| `2026-08-22` | 22 | 4,234 | 3,168 | 0.999763 | **100.4012** | ±0.7626 | 98.91 | 101.90 | ✅ |
| `2026-08-23` | 23 | 4,314 | 3,157 | 0.997588 | **100.1590** | ±0.8403 | 98.51 | 101.81 | ✅ |
| `2026-08-24` | 24 | 4,216 | 3,156 | 0.997786 | **99.9372** | ±0.8315 | 98.31 | 101.57 | ✅ |
| `2026-08-25` | 25 | 4,263 | 3,130 | 1.002622 | **100.1992** | ±0.8011 | 98.63 | 101.77 | ✅ |
| `2026-08-26` | 26 | 4,215 | 3,125 | 1.002286 | **100.4283** | ±0.7842 | 98.89 | 101.97 | ✅ |
| `2026-08-27` | 27 | 4,296 | 3,128 | 0.999352 | **100.3633** | ±0.8000 | 98.80 | 101.93 | ✅ |
| `2026-08-28` | 28 | 4,294 | 3,223 | 1.006584 | **101.0240** | ±0.7940 | 99.47 | 102.58 | ✅ |
| `2026-08-29` | 29 | 4,322 | 3,221 | 0.994353 | **100.4536** | ±0.8448 | 98.80 | 102.11 | ✅ |
| `2026-08-30` | 30 | 4,258 | 3,161 | 1.002308 | **100.6854** | ±0.8415 | 99.04 | 102.33 | ✅ |
| `2026-08-31` | 31 | 4,297 | 3,151 | 0.997262 | **100.4097** | ±0.8328 | 98.78 | 102.04 | ✅ |

---

## 4. Weekly Synthetic APIx Series

> [!IMPORTANT]  
> Base: **Week 1 (Aug 1–7) = 100.0000**.  
> Method: Intra-week geometric mean per product → week-on-week short-chain Jevons.

| Week | Period | Observations | Matched Products | Weekly Relative | Weekly Index | SE | 95% CI | CI? |
|:----:|:------:|:------------:|:----------------:|:---------------:|:------------:|:--:|:------:|:---:|
| **Week 1** | 2026-08-01 – 2026-08-07 | 30,218 | 5,973 | 1.000000 | **100.0000** | ±0.0000 | [100.00, 100.00] | ✅ |
| **Week 2** | 2026-08-08 – 2026-08-14 | 30,082 | 5,968 | 1.000105 | **100.0105** | ±0.3135 | [99.40, 100.62] | ✅ |
| **Week 3** | 2026-08-15 – 2026-08-21 | 30,139 | 5,967 | 0.999702 | **99.9807** | ±0.3202 | [99.35, 100.61] | ✅ |
| **Week 4** | 2026-08-22 – 2026-08-31 | 42,709 | 5,971 | 1.000357 | **100.0164** | ±0.2875 | [99.45, 100.58] | ✅ |

---

## 5. Monthly Synthetic Aggregation — August 2026

| Metric | Value |
|--------|-------|
| Month | `2026-08` |
| Data Label | `SYNTHETIC_METHODOLOGY_DEMONSTRATION` |
| Canonical Products Evaluated | 5,977 |
| Qualified (active_ratio ≥ 0.30) | **5,967** |
| Disqualified | 10 |
| Populated Cells | **360 / 360** |
| Synthetic Representative Price (INR) | **₹5,769.64** |
| P_ref used as denominator | **NO** ✅ |

> [!NOTE]  
> P_ref (₹8,641.45) is **strictly descriptive** and was NOT used as a denominator in this calculation.

---

## 6. Compact Summary Table

> Date | Daily APIx | Weekly APIx | SE | CI95

| Date | Daily APIx | Weekly APIx | Monthly APIx | SE (Daily) | CI 95% (Daily) |
|:----:|:-----------:|:-----------:|:------------:|:----------:|:--------------:|
| `2026-08-01` | 100.0000 | 100.0000 | — | ±0.0000 | [100.00, 100.00] |
| `2026-08-02` | 100.1874 | 100.0000 | — | ±0.7881 | [98.64, 101.73] |
| `2026-08-03` | 99.6431 | 100.0000 | — | ±0.7811 | [98.11, 101.17] |
| `2026-08-04` | 100.4444 | 100.0000 | — | ±0.7956 | [98.88, 102.00] |
| `2026-08-05` | 100.1203 | 100.0000 | — | ±0.8524 | [98.45, 101.79] |
| `2026-08-06` | 100.5300 | 100.0000 | — | ±0.7617 | [99.04, 102.02] |
| `2026-08-07` | 100.5107 | 100.0000 | — | ±0.8063 | [98.93, 102.09] |
| `2026-08-08` | 100.1202 | 100.0105 | — | ±0.7992 | [98.55, 101.69] |
| `2026-08-09` | 100.1305 | 100.0105 | — | ±0.8456 | [98.47, 101.79] |
| `2026-08-10` | 100.0455 | 100.0105 | — | ±0.7985 | [98.48, 101.61] |
| `2026-08-11` | 100.2671 | 100.0105 | — | ±0.8065 | [98.69, 101.85] |
| `2026-08-12` | 100.0273 | 100.0105 | — | ±0.8426 | [98.38, 101.68] |
| `2026-08-13` | 100.8920 | 100.0105 | — | ±0.8764 | [99.17, 102.61] |
| `2026-08-14` | 100.4836 | 100.0105 | — | ±0.8368 | [98.84, 102.12] |
| `2026-08-15` | 100.0418 | 99.9807 | — | ±0.7514 | [98.57, 101.51] |
| `2026-08-16` | 100.3140 | 99.9807 | — | ±0.8202 | [98.71, 101.92] |
| `2026-08-17` | 99.7760 | 99.9807 | — | ±0.8358 | [98.14, 101.41] |
| `2026-08-18` | 100.0540 | 99.9807 | — | ±0.7794 | [98.53, 101.58] |
| `2026-08-19` | 100.4403 | 99.9807 | — | ±0.7642 | [98.94, 101.94] |
| `2026-08-20` | 100.9524 | 99.9807 | — | ±0.8187 | [99.35, 102.56] |
| `2026-08-21` | 100.4250 | 99.9807 | — | ±0.8024 | [98.85, 102.00] |
| `2026-08-22` | 100.4012 | 100.0164 | — | ±0.7626 | [98.91, 101.90] |
| `2026-08-23` | 100.1590 | 100.0164 | — | ±0.8403 | [98.51, 101.81] |
| `2026-08-24` | 99.9372 | 100.0164 | — | ±0.8315 | [98.31, 101.57] |
| `2026-08-25` | 100.1992 | 100.0164 | — | ±0.8011 | [98.63, 101.77] |
| `2026-08-26` | 100.4283 | 100.0164 | — | ±0.7842 | [98.89, 101.97] |
| `2026-08-27` | 100.3633 | 100.0164 | — | ±0.8000 | [98.80, 101.93] |
| `2026-08-28` | 101.0240 | 100.0164 | — | ±0.7940 | [99.47, 102.58] |
| `2026-08-29` | 100.4536 | 100.0164 | — | ±0.8448 | [98.80, 102.11] |
| `2026-08-30` | 100.6854 | 100.0164 | — | ±0.8415 | [99.04, 102.33] |
| `2026-08-31` | 100.4097 | 100.0164 | ₹5,769.64 | ±0.8328 | [98.78, 102.04] |

---

## 7. Mathematical Governance Validation Proofs

### P1 P REF NEVER DENOMINATOR: ✅ PASSED
- **Description**: P_ref (INR 8641.45) is never used as an index denominator.
  - daily: formula uses I_{d-1} * J_d; no 8641.45 in denominator.
  - weekly: formula uses I_{w-1} * J_w; no 8641.45 in denominator.
  - monthly: formula sums route prices; no 8641.45 in denominator.

### P2 JEVONS USES PRICE RELATIVES: ✅ PASSED
- **Description**: Jevons index uses P_t / P_{t-1}, not P_t / P_ref.
- **Formula**: `J_{s,t} = exp( (1/N) * sum_i(ln(P_{i,t} / P_{i,t-1})) )`
- Cell log-relatives computed as ln(total_fare_curr / total_fare_prev).

### P3 ROUTE WEIGHTS SUM TO 1: ✅ PASSED
- **Description**: DGCA Top-60 route weights sum to exactly 1.0.
- **Sum**: 1.00000000

### P4 LEAD TIME WEIGHTS SUM TO 1: ✅ PASSED
- **Description**: Empirical lead-time weights sum to exactly 1.0.
- **Sum**: 1.00000000

### P5 SYNTHETIC NEVER IN PRODUCTION: ✅ PASSED
- **Description**: No synthetic observation was written to the production baseline.

### P6 FIRST REFERENCE PERIOD EQUALS 100: ✅ PASSED
- **Description**: The first reference period (Day 1 / Week 1) is set to exactly 100.0000.

### P7 NO ZERO OR NEGATIVE FARES: ✅ PASSED
- **Description**: No zero-price or negative-price observations are used in index calculation.
- Pre-load governance check confirmed 0 zero/negative fares.

---

## 8. Uncertainty Diagnostics

| Metric | Value |
|--------|-------|
| Days with CI available | 31 |
| Days without CI | 0 |
| Mean daily standard error | 0.7837 |
| Mean daily CI width (95%) | 3.0716 |
| Weeks with CI | 4 |
| Uncertainty method | Delta method (first-order Taylor approximation on log-price relatives) |
| CI coverage | 95% (z = 1.96) |

---

## 9. Conclusion

The Synthetic August 2026 demonstration dataset successfully validates the end-to-end operation of the APIx daily, weekly, and monthly aggregation engines, short-chain Jevons methodology, empirical lead-time weighting, DGCA route weighting, and Delta-method uncertainty propagation. All 7 governance invariants were verified automatically.

> [!CAUTION]
> **REMINDER**: These are SYNTHETIC calculations. No result in this report constitutes
> observed Indian airfare inflation, actual price movement, or any statistical claim
> about the real Indian domestic airfare market.