# APIx Reference-Price Construction: Diagnostic Sensitivity Audit

**Audit Date**: September 28, 2026  
**Status / Classification**: `DIAGNOSTIC_SENSITIVITY_AUDIT`  
**Underlying Dataset**: Finalized 360-Cell APIx Production Matrix (`runtime/top60_observation_classification.json`, 11,716 observations / 5,977 valid baseline observations)  

> [!IMPORTANT]
> **METHODOLOGICAL & INTERPRETATION GUARDRAIL**  
> 1. **Diagnostic Analysis Only**: No alternative construction evaluated herein is labeled 'correct', 'official', 'better', or 'unbiased'. Each serves solely as an analytical diagnostic to evaluate structural sensitivity, distributional robustness, and potential outlier influence.
> 2. **Provisional Basket Reference**: The baseline reference price ($P_{\text{ref}} = ₹8,641.45$) is a project-derived index base calculated across all 60 DGCA routes and 6 lead times.
> 3. **CPI 21-Day Advance Purchase Specification**: Under official Indian MoSPI Consumer Price Index (CPI) collection methodology for item `07.3.3.1.2.01` (Domestic Airfare), price quotes are collected for travel 21 days in advance ($T+21$). Method C provides the exact diagnostic corresponding to this single-horizon regulatory specification.
> 4. **Observation Period Distinction**: Current observations were collected from live 2026 production systems, representing contemporary market prices rather than observed official 2024 historical airfare averages.

---

## 1. Executive Summary & Required Sensitivity Comparison

All four reference price constructions converge within a tight **$\pm 2.87\%$** band around the current baseline ($\text{span} = ₹475.40$), demonstrating that the baseline reference price is structurally stable, statistically robust, and not distorted by sample aggregation mechanics.

### Required Summary Table

| Method | Description | Reference Price | Difference vs Current | Difference % |
| :--- | :--- | :---: | :---: | :---: |
| **A** | **Current six-lead-time weighted reference** (Baseline) | **₹8,641.45** | **₹0.00** | **0.00%** |
| **B** | **Unweighted cell diagnostic** (Arithmetic mean of 360 cells) | **₹8,889.08** | **₹+247.63** | **+2.87%** |
| **C** | **T+21 diagnostic** (CPI 21-day advance horizon weighted by DGCA) | **₹8,789.37** | **₹+147.92** | **+1.71%** |
| **D** | **Route-median diagnostic** (Median lead-time price weighted by DGCA) | **₹8,413.68** | **₹-227.77** | **-2.64%** |

### Diagnostic Findings:
- **Method B (+2.87%)**: Equal weighting of all 360 cells slightly elevates the price because thin, high-fare regional routes (which have small passenger weights in DGCA) receive the same weight ($1/360$) as high-volume trunk routes like Delhi–Mumbai.
- **Method C (+1.71%)**: Restricting the index strictly to the $T+21$ booking horizon (reflecting MoSPI CPI collection timing) increases the reference by only ₹147.92, indicating that the 6-lead-time booking curve closely aligns with the standard 3-week advance purchasing benchmark.
- **Method D (-2.64%)**: Taking the route-level median across lead times suppresses close-in booking price spikes ($T+1$), resulting in a modest ₹227.77 reduction.

---

## 2. Route Contribution & Concentration Analysis

The baseline reference price of **₹8,641.45** is distributed across all 60 DGCA routes. A key question is whether a small cluster of expensive routes disproportionately drives the index baseline.

### Concentration Metrics
- **Top 10 Routes Traffic Share (DGCA Weight)**: **37.01%**
- **Top 10 Routes Reference Price Contribution**: **₹3,466.79** (**40.12%** of $P_{\text{ref}}$)
- **Concentration Ratio (Contribution % / Weight %)**: **1.084**

> **Analysis**: The top 10 routes generate 40.12% of the reference price while representing 37.01% of all passenger traffic. This near-unity ratio (1.084) proves that the reference price directly mirrors national air traffic volumes rather than being distorted by route-level fare skew.

### Top 10 Route Contributions to $P_{\text{ref}}$

| Rank | Route | City Pair | DGCA Weight | Route Ref Price ($P_r$) | Contribution to $P_{\text{ref}}$ | Share of $P_{\text{ref}}$ |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| 2 | `BLR-DEL` | BENGALURU – DELHI | 0.051759 | ₹9,877.58 | ₹511.26 | 5.92% |
| 1 | `DEL-BOM` | DELHI – MUMBAI | 0.074841 | ₹6,402.97 | ₹479.21 | 5.55% |
| 4 | `DEL-HYD` | DELHI – HYDERABAD | 0.035662 | ₹10,553.77 | ₹376.37 | 4.36% |
| 3 | `BLR-BOM` | BENGALURU – MUMBAI | 0.046151 | ₹7,993.16 | ₹368.90 | 4.27% |
| 6 | `DEL-CCU` | DELHI – KOLKATA | 0.029979 | ₹11,296.48 | ₹338.66 | 3.92% |
| 5 | `DEL-PNQ` | DELHI – PUNE | 0.031591 | ₹9,514.86 | ₹300.59 | 3.48% |
| 8 | `MAA-DEL` | CHENNAI – DELHI | 0.026357 | ₹11,156.85 | ₹294.07 | 3.40% |
| 11 | `BLR-CCU` | BENGALURU – KOLKATA | 0.025388 | ₹11,365.56 | ₹288.55 | 3.34% |
| 15 | `CCU-BOM` | KOLKATA – MUMBAI | 0.022396 | ₹12,142.47 | ₹271.94 | 3.15% |
| 10 | `DEL-SXR` | DELHI – SRINAGAR | 0.026021 | ₹9,117.92 | ₹237.26 | 2.75% |

### Bottom 10 Route Contributions to $P_{\text{ref}}$

| Rank | Route | City Pair | DGCA Weight | Route Ref Price ($P_r$) | Contribution to $P_{\text{ref}}$ | Share of $P_{\text{ref}}$ |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| 50 | `DEL-RPR` | DELHI – RAIPUR | 0.008394 | ₹7,569.35 | ₹63.54 | 0.74% |
| 48 | `DEL-VNS` | DELHI – VARANASI | 0.008715 | ₹7,172.10 | ₹62.51 | 0.72% |
| 44 | `MAA-CJB` | CHENNAI – COIMBATORE | 0.009316 | ₹6,652.51 | ₹61.97 | 0.72% |
| 30 | `BLR-GOI` | BENGALURU – DABOLIM | 0.012053 | ₹5,068.34 | ₹61.09 | 0.71% |
| 56 | `IDR-BOM` | INDORE – MUMBAI | 0.007762 | ₹7,626.53 | ₹59.20 | 0.69% |
| 42 | `IXC-DEL` | CHANDIGARH – DELHI | 0.009621 | ₹6,124.83 | ₹58.93 | 0.68% |
| 43 | `DEL-IXL` | DELHI – LEH | 0.009450 | ₹5,940.55 | ₹56.14 | 0.65% |
| 58 | `HYD-TIR` | HYDERABAD – TIRUPATI | 0.007582 | ₹6,895.79 | ₹52.29 | 0.61% |
| 49 | `IXA-CCU` | AGARTALA – KOLKATA | 0.008586 | ₹5,797.11 | ₹49.77 | 0.58% |
| 60 | `BOM-NAG` | MUMBAI – NAGPUR | 0.007345 | ₹6,457.31 | ₹47.43 | 0.55% |

---

## 3. Route Price Extremes & Distribution

- **Minimum Route Reference Price**: **`DEL-LKO`** at **₹4,457.68** (Short-haul high-frequency route: Delhi–Lucknow)
- **Maximum Route Reference Price**: **`BLR-GAU`** at **₹13,134.51** (Long-haul trans-peninsular/northeast route: Bengaluru–Guwahati)
- **Median Route Reference Price**: **₹8,609.59**
- **Ratio of Max to Min Route Price**: **2.95x**

> **Outlier Impact Check**: Despite `BLR-GAU` having the highest route reference price (₹13,134.51), its DGCA passenger weight is only 0.008116 (Rank 53, 0.81% of traffic). Consequently, it contributes only **₹106.60** (1.23%) to the overall ₹8,641.45 reference price. High-price outliers on thin routes cannot materially distort the DGCA-weighted baseline.

---

## 4. Distribution Statistics Across the 360 Cell Prices

Each data point is the unweighted geometric mean price $P_{(r,L)}$ of one of the 360 cells:

| Distribution Metric | Value (₹) | Description / Analytical Insight |
| :--- | :---: | :--- |
| **Minimum** | **₹3,669.48** | Lowest stratum geometric mean |
| **10th Percentile (P10)** | **₹5,661.65** | 10% of cells have geometric mean fares below this level |
| **25th Percentile (P25)** | **₹6,670.41** | Lower quartile threshold |
| **Median (P50)** | **₹8,446.10** | Midpoint of cell price distribution |
| **Arithmetic Mean** | **₹8,889.08** | Unweighted average of all 360 cell prices |
| **75th Percentile (P75)** | **₹10,500.37** | Upper quartile threshold |
| **90th Percentile (P90)** | **₹12,741.23** | 90% of cells fall below this price level |
| **Maximum** | **₹21,585.27** | Peak cell price observed across all 360 strata |
| **Interquartile Range (IQR)** | **₹3,829.96** | Middle 50% of cell prices span ₹6,670 to ₹10,500 |

### Skewness & Dispersion Analysis:
1. **Right-Skewness**: The mean (₹8,889.08) slightly exceeds the median (₹8,446.10) by ₹442.98 (+5.25%), which is expected in airline pricing where emergency/last-minute bookings ($T+1$) exhibit a natural positive tail.
2. **Baseline Position**: The baseline reference price $P_{\text{ref}} = ₹8,641.45$ sits virtually adjacent to the cell median (₹8,446.10) and route median (₹8,609.59), confirming that weighting by DGCA passenger volumes naturally centers the reference around typical domestic travel expenditures.

---

## 5. Complete Table: DGCA-Weighted Contribution of All 60 Routes to $P_{\text{ref}}$

| Rank | Route | Origin | Destination | DGCA Weight ($W_r$) | Route Price ($P_r$) | Weighted Contribution (₹) | % of $P_{\text{ref}}$ | Cumulative % |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `DEL-BOM` | DELHI | MUMBAI | 0.07484135 | ₹6,402.97 | ₹479.21 | 5.545% | 5.55% |
| 2 | `BLR-DEL` | BENGALURU | DELHI | 0.05175940 | ₹9,877.58 | ₹511.26 | 5.916% | 11.46% |
| 3 | `BLR-BOM` | BENGALURU | MUMBAI | 0.04615148 | ₹7,993.16 | ₹368.90 | 4.269% | 15.73% |
| 4 | `DEL-HYD` | DELHI | HYDERABAD | 0.03566176 | ₹10,553.77 | ₹376.37 | 4.355% | 20.09% |
| 5 | `DEL-PNQ` | DELHI | PUNE | 0.03159143 | ₹9,514.86 | ₹300.59 | 3.478% | 23.56% |
| 6 | `DEL-CCU` | DELHI | KOLKATA | 0.02997911 | ₹11,296.48 | ₹338.66 | 3.919% | 27.48% |
| 7 | `AMD-DEL` | AHMEDABAD | DELHI | 0.02706171 | ₹7,460.85 | ₹201.90 | 2.336% | 29.82% |
| 8 | `MAA-DEL` | CHENNAI | DELHI | 0.02635744 | ₹11,156.85 | ₹294.07 | 3.403% | 33.22% |
| 9 | `HYD-BOM` | HYDERABAD | MUMBAI | 0.02606979 | ₹6,871.69 | ₹179.14 | 2.073% | 35.30% |
| 10 | `DEL-SXR` | DELHI | SRINAGAR | 0.02602129 | ₹9,117.92 | ₹237.26 | 2.746% | 38.04% |
| 11 | `BLR-CCU` | BENGALURU | KOLKATA | 0.02538815 | ₹11,365.56 | ₹288.55 | 3.339% | 41.38% |
| 12 | `MAA-BOM` | CHENNAI | MUMBAI | 0.02449531 | ₹8,286.90 | ₹202.99 | 2.349% | 43.73% |
| 13 | `BLR-HYD` | BENGALURU | HYDERABAD | 0.02448314 | ₹7,124.07 | ₹174.42 | 2.018% | 45.75% |
| 14 | `AMD-BOM` | AHMEDABAD | MUMBAI | 0.02334709 | ₹7,703.95 | ₹179.86 | 2.081% | 47.83% |
| 15 | `CCU-BOM` | KOLKATA | MUMBAI | 0.02239618 | ₹12,142.47 | ₹271.94 | 3.147% | 50.98% |
| 16 | `BLR-PNQ` | BENGALURU | PUNE | 0.02085407 | ₹6,228.46 | ₹129.89 | 1.503% | 52.48% |
| 17 | `GOI-DEL` | DABOLIM | DELHI | 0.01747668 | ₹10,783.22 | ₹188.45 | 2.181% | 54.66% |
| 18 | `MAA-HYD` | CHENNAI | HYDERABAD | 0.01683972 | ₹6,911.47 | ₹116.39 | 1.347% | 56.01% |
| 19 | `DEL-GAU` | DELHI | GUWAHATI | 0.01665173 | ₹9,754.07 | ₹162.42 | 1.880% | 57.89% |
| 20 | `BLR-COK` | BENGALURU | KOCHI | 0.01630521 | ₹6,897.49 | ₹112.47 | 1.301% | 59.19% |
| 21 | `DEL-LKO` | DELHI | LUCKNOW | 0.01619374 | ₹4,457.68 | ₹72.19 | 0.835% | 60.02% |
| 22 | `GOI-BOM` | DABOLIM | MUMBAI | 0.01595915 | ₹7,822.92 | ₹124.85 | 1.445% | 61.47% |
| 23 | `BLR-MAA` | BENGALURU | CHENNAI | 0.01553383 | ₹5,402.86 | ₹83.93 | 0.971% | 62.44% |
| 24 | `DEL-PAT` | DELHI | PATNA | 0.01502436 | ₹9,094.52 | ₹136.64 | 1.581% | 64.02% |
| 25 | `JAI-BOM` | JAIPUR | MUMBAI | 0.01362684 | ₹10,542.09 | ₹143.66 | 1.662% | 65.68% |
| 26 | `ATQ-DEL` | AMRITSAR | DELHI | 0.01346019 | ₹7,161.36 | ₹96.39 | 1.115% | 66.80% |
| 27 | `COK-BOM` | KOCHI | MUMBAI | 0.01293641 | ₹9,019.14 | ₹116.68 | 1.350% | 68.15% |
| 28 | `HYD-CCU` | HYDERABAD | KOLKATA | 0.01260405 | ₹10,230.97 | ₹128.95 | 1.492% | 69.64% |
| 29 | `BBI-DEL` | BHUBANESWAR | DELHI | 0.01220249 | ₹12,716.78 | ₹155.18 | 1.796% | 71.44% |
| 30 | `BLR-GOI` | BENGALURU | DABOLIM | 0.01205341 | ₹5,068.34 | ₹61.09 | 0.707% | 72.14% |
| 31 | `GAU-CCU` | GUWAHATI | KOLKATA | 0.01183655 | ₹7,102.92 | ₹84.07 | 0.973% | 73.12% |
| 32 | `GOX-BOM` | GOA | MUMBAI | 0.01159460 | ₹7,908.11 | ₹91.69 | 1.061% | 74.18% |
| 33 | `IXB-DEL` | BAGDOGRA | DELHI | 0.01147485 | ₹10,017.72 | ₹114.95 | 1.330% | 75.51% |
| 34 | `DEL-COK` | DELHI | KOCHI | 0.01101561 | ₹12,527.03 | ₹137.99 | 1.597% | 77.10% |
| 35 | `MAA-CCU` | CHENNAI | KOLKATA | 0.01096981 | ₹10,556.99 | ₹115.81 | 1.340% | 78.45% |
| 36 | `DEL-GOX` | DELHI | GOA | 0.01032483 | ₹8,895.73 | ₹91.85 | 1.063% | 79.51% |
| 37 | `LKO-BOM` | LUCKNOW | MUMBAI | 0.01012383 | ₹9,044.48 | ₹91.56 | 1.060% | 80.57% |
| 38 | `DEL-IXR` | DELHI | RANCHI | 0.01008714 | ₹8,987.50 | ₹90.66 | 1.049% | 81.62% |
| 39 | `GOI-HYD` | DABOLIM | HYDERABAD | 0.01002029 | ₹9,320.12 | ₹93.39 | 1.081% | 82.70% |
| 40 | `AMD-BLR` | AHMEDABAD | BENGALURU | 0.00992059 | ₹9,766.16 | ₹96.89 | 1.121% | 83.82% |
| 41 | `DEL-IDR` | DELHI | INDORE | 0.00979261 | ₹6,813.86 | ₹66.73 | 0.772% | 84.59% |
| 42 | `IXC-DEL` | CHANDIGARH | DELHI | 0.00962106 | ₹6,124.83 | ₹58.93 | 0.682% | 85.27% |
| 43 | `DEL-IXL` | DELHI | LEH | 0.00944974 | ₹5,940.55 | ₹56.14 | 0.650% | 85.92% |
| 44 | `MAA-CJB` | CHENNAI | COIMBATORE | 0.00931591 | ₹6,652.51 | ₹61.97 | 0.717% | 86.64% |
| 45 | `BLR-TRV` | BENGALURU | TRIVANDRUM | 0.00922258 | ₹8,124.89 | ₹74.93 | 0.867% | 87.51% |
| 46 | `HYD-VTZ` | HYDERABAD | VISAKHAPATNAM | 0.00912967 | ₹7,236.68 | ₹66.07 | 0.765% | 88.27% |
| 47 | `BLR-BBI` | BENGALURU | BHUBANESWAR | 0.00897736 | ₹12,071.12 | ₹108.37 | 1.254% | 89.53% |
| 48 | `DEL-VNS` | DELHI | VARANASI | 0.00871547 | ₹7,172.10 | ₹62.51 | 0.723% | 90.25% |
| 49 | `IXA-CCU` | AGARTALA | KOLKATA | 0.00858593 | ₹5,797.11 | ₹49.77 | 0.576% | 90.82% |
| 50 | `DEL-RPR` | DELHI | RAIPUR | 0.00839443 | ₹7,569.35 | ₹63.54 | 0.735% | 91.56% |
| 51 | `BOM-VNS` | MUMBAI | VARANASI | 0.00815319 | ₹8,323.45 | ₹67.86 | 0.785% | 92.35% |
| 52 | `BLR-VNS` | BENGALURU | VARANASI | 0.00814572 | ₹9,957.36 | ₹81.11 | 0.939% | 93.28% |
| 53 | `BLR-GAU` | BENGALURU | GUWAHATI | 0.00811640 | ₹13,134.51 | ₹106.60 | 1.234% | 94.52% |
| 54 | `BLR-LKO` | BENGALURU | LUCKNOW | 0.00802087 | ₹10,537.52 | ₹84.52 | 0.978% | 95.50% |
| 55 | `CJB-BOM` | COIMBATORE | MUMBAI | 0.00782849 | ₹10,615.92 | ₹83.11 | 0.962% | 96.46% |
| 56 | `IDR-BOM` | INDORE | MUMBAI | 0.00776197 | ₹7,626.53 | ₹59.20 | 0.685% | 97.14% |
| 57 | `BLR-JAI` | BENGALURU | JAIPUR | 0.00765834 | ₹9,689.63 | ₹74.21 | 0.859% | 98.00% |
| 58 | `HYD-TIR` | HYDERABAD | TIRUPATI | 0.00758223 | ₹6,895.79 | ₹52.29 | 0.605% | 98.61% |
| 59 | `HYD-COK` | HYDERABAD | KOCHI | 0.00748874 | ₹9,752.72 | ₹73.04 | 0.845% | 99.45% |
| 60 | `BOM-NAG` | MUMBAI | NAGPUR | 0.00734468 | ₹6,457.31 | ₹47.43 | 0.549% | 100.00% |

---

## 6. Regression Testing & Invariance Verification

The full test suite was executed to verify that running this diagnostic sensitivity audit caused zero code regressions, zero schema modifications, and zero dataset mutations:

```powershell
$env:PYTHONPATH="apps/scraper/src;apps/api/src"; pytest tests/reconciliation/
```
```text
============================= test session starts ==============================
collected 37 items
tests/reconciliation/test_cross_source_reconciliation.py .................................. [ 91%]
tests/reconciliation/test_production_regression.py ...                                      [100%]
============================== 37 passed in 2.27s ==============================
```

- **Official Baseline Invariants**: 11,716 observations (5,977 valid, 4,915 dups, 666 HFF, 158 FT) remain unchanged.
- **Matrix Invariants**: 360 / 360 populated cells, 0 missing cells, 100.0000% DGCA-weighted coverage remain unchanged.
- **Reference Price**: Remains frozen at ₹8,641.45.