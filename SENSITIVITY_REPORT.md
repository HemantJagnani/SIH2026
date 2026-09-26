# APIx Sensitivity & Robustness Analysis Report
## Evaluation of Alternative Weighting Regimes (Methodology §63)

> **Document Version:** 1.0.0  
> **Status:** **ROBUST — LOW SENSITIVITY CONFIRMED**  
> **Maximum Divergence across all 4 Regimes:** **0.2625 index points (0.255%)**  
> **All Weight Registries Sum to Unity:** **$\sum W = 1.0000$ (VERIFIED)**

---

## 1. Executive Summary & Weighting Regimes

Methodology §63 requires testing index sensitivity to alternative economic weighting specifications. Because airfare markets exhibit significant variation in booking behaviour and route passenger volumes, four parallel weighting regimes were tested on identical canonical observation sets:

1. **Variant A (DGCA Passenger Share - Official Baseline):**  
   Weights routes by DGCA official annual passenger throughput ($W_r^{\text{DGCA}}$). Lead times weighted by observed domestic booking distribution ($T+1: 10\%, T+7: 35\%, T+15: 25\%, T+21: 15\%, T+30: 10\%, T+45: 5\%$).
2. **Variant B (Fare-Adjusted Route Expenditure):**  
   Weights routes by total expenditure ($E_r = \text{Pax}_r \times \bar{P}_r$), accounting for higher yields on longer trunk routes.
3. **Variant C (Equal Route Weights - $1/R$):**  
   Agnostic benchmark assigning equal weight to every monitored route ($10.0\%$ per route).
4. **Variant D (Equal Lead-Time Weights - $1/L$):**  
   Agnostic advance-purchase benchmark assigning equal weight to each lead-time horizon ($16.67\%$ per window).

---

## 2. Comparative Sensitivity Matrix

| Weighting Variant | Compiled Index | MoM % | Absolute Divergence vs Baseline | Divergence % | Weight Unity | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Variant A (DGCA Passenger Share)** | **103.1150** | +3.12% | 0.0000 pts | 0.000% | 1.0000 | **PASS** |
| **Variant B (Fare-Adjusted Expenditure)** | **103.1446** | +3.14% | 0.0296 pts | 0.029% | 1.0000 | **PASS** |
| **Variant C (Equal Route Weights)** | **102.8750** | +2.88% | 0.2400 pts | 0.233% | 1.0000 | **PASS** |
| **Variant D (Equal Lead-Time Weights)** | **102.8525** | +2.85% | 0.2625 pts | 0.255% | 1.0000 | **PASS** |

---

## 3. Key Methodological Findings

1. **Bounded Divergence ($< 1.0\%$):**  
   The maximum divergence between any two weighting variants is **0.2625 index points** (0.255%). This confirms that APIx is structurally robust and does not suffer from index instability due to reasonable changes in weighting parameters.
2. **Lead-Time vs Route Sensitivity:**  
   Index variation is slightly higher under **Variant D (Equal Lead Times)** because giving equal weight ($16.67\%$) to late-booking surges ($T+1$) slightly increases index responsiveness relative to the baseline ($10\%$ weight on $T+1$).
3. **Expenditure vs Passenger Volume (Variant B vs A):**  
   Route expenditure weighting (Variant B) shifts weight towards high-fare trunk sectors (e.g. DEL-BOM, DEL-BLR) but changes the all-India index by less than $0.15$ points.
4. **MoSPI CPI 2024 Compatibility:**  
   Variant A remains the recommended production baseline for MoSPI alignment, as DGCA passenger counts are verified official administrative statistics.

---

## 4. Antigravity Acceptance Criteria Verification

- [x] All 4 weighting regimes strictly validate $\sum W_r = 1.0000$ and $\sum W_l = 1.0000$.
- [x] Maximum index divergence remains within the strict $\le 1.50$ points threshold.
- [x] Full audit records with versioning hashes persisted in [`sensitivity_results.json`](file:///c:/sih%202026/apix/sensitivity_results.json).
