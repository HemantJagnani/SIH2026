# APIx Provisional Basket-Based Reference Price (P_ref) Report

**Report Date**: September 28, 2026  
**Status / Classification**: `PROVISIONAL_PROJECT_REFERENCE`  
**Methodology Version**: `APIX_METHODOLOGY_V1` / `APIx_PRODUCT_DEF_v2.0_FROZEN`  
**Underlying Dataset**: Finalized 360-Cell APIx Production Matrix (`runtime/top60_observation_classification.json`, 11,716 observations)  

> [!IMPORTANT]
> **PROVISIONAL_PROJECT_REFERENCE NOTICE**  
> This reference price represents the basket-based reference derived from the project's 2026 production observations, not an observed official 2024 airfare average. It is calculated strictly to establish the basket-aggregated baseline $P_{\text{ref}}$ across all 60 DGCA CY2024 top routes and all 6 standardized lead-time classes without index calculation or arbitrary price imputation.

---

## 1. Executive Summary & Final Calculation

The provisional reference price $P_{\text{ref}}$ is calculated using a two-stage aggregation across all 360 populated cells:
1. **Stage 1 (Lead-Time Class Geometric Mean)**: For each route $r$ and lead-time horizon $L \in \{T+1, T+7, T+15, T+21, T+30, T+45\}$, compute the geometric mean of valid APIx baseline fares: $P_{(r,L)} = \exp\left(\frac{1}{N_{r,L}} \sum_{i=1}^{N_{r,L}} \ln(p_i)\right)$.
2. **Stage 2 (Route Reference Price)**: Compute the weighted average across lead times using frozen empirical weights: $P_r = \sum_L w_L \cdot P_{(r,L)}$.
3. **Stage 3 (Basket Reference Price)**: Compute the final index reference price weighted by DGCA CY2024 passenger traffic: $P_{\text{ref}} = \sum_r W_r \cdot P_r$.

### Summary Calculation Table (Table C)

| Metric | Value | Verification Status |
| :--- | :---: | :---: |
| **Methodology Classification** | `PROVISIONAL_PROJECT_REFERENCE` | Verified |
| **Number of Valid Observations Used** | **5,977** | 100% of validated baseline |
| **Total Raw Observations in Dataset** | **11,716** | Verified |
| **Number of Route × Lead-Time Cells Used** | **360 / 360** | 100.00% complete matrix |
| **Sum of Lead-Time Weights ($\sum w_L$)** | **1.0000** | Exactly 1.0000 |
| **Sum of DGCA Route Weights ($\sum W_r$)** | **1.000000** | Exactly 1.000000 |
| **$P_{\text{ref}}$ (Full Precision Internal)** | **`8641.449959639450392914009502`** | Exact decimal accumulator |
| **$P_{\text{ref}}$ (Rounded to ₹0.01)** | **₹8,641.45** | Official Displayed Baseline |

---

## 2. Regulatory & Methodological Compliance Invariants

1. **No Index Calculation**: Only $P_{\text{ref}}$ is calculated; no time-series index relatives or temporal link ratios are computed.
2. **No Observation-Count Weighting**: Cell observations enter via unweighted geometric means $P_{(r,L)}$; route weights $W_r$ are strictly DGCA CY2024 annual passenger shares.
3. **No 2022 Clean_Dataset Price Contamination**: The 2022 dataset was used strictly for historical lead-time booking proportions; zero 2022 prices entered $P_{\text{ref}}$.
4. **No Arbitrary Prototype Anchor**: The rejected ₹6,632.67 prototype value is entirely excluded.
5. **No CPI Expenditure Weight Contamination**: MoSPI CPI airfare expenditure weight (0.02951% / 0.0002951) was not used in calculating $P_{\text{ref}}$.
6. **Zero Imputation**: Every single one of the 360 cells was populated with genuine empirical production observations.

---

## 3. Table A: Route × Lead-Time Geometric Mean Prices

All prices represent the geometric mean of valid economic baseline observations within that specific stratum: $P_{(r,L)} = \exp(\text{mean}(\ln(p_i)))$.

| Rank | Route | T+1 (₹) | T+7 (₹) | T+15 (₹) | T+21 (₹) | T+30 (₹) | T+45 (₹) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `DEL-BOM` | 6,433.62 | 6,334.87 | 6,435.04 | 6,331.09 | 6,427.75 | 6,431.89 |
| 2 | `BLR-DEL` | 10,800.55 | 9,917.22 | 9,261.76 | 10,789.54 | 9,623.40 | 9,746.78 |
| 3 | `BLR-BOM` | 10,388.30 | 8,595.09 | 6,877.72 | 7,366.50 | 7,470.46 | 8,754.47 |
| 4 | `DEL-HYD` | 10,582.58 | 13,032.61 | 9,433.50 | 10,366.34 | 9,682.17 | 10,887.86 |
| 5 | `DEL-PNQ` | 10,809.67 | 11,762.40 | 7,138.11 | 8,790.87 | 8,202.42 | 11,224.18 |
| 6 | `DEL-CCU` | 9,247.79 | 9,240.94 | 9,511.60 | 13,158.71 | 13,417.18 | 10,573.67 |
| 7 | `AMD-DEL` | 7,330.56 | 6,712.81 | 6,097.62 | 6,124.48 | 6,250.48 | 10,713.36 |
| 8 | `MAA-DEL` | 12,045.85 | 12,789.62 | 9,934.69 | 10,679.16 | 10,005.59 | 12,285.66 |
| 9 | `HYD-BOM` | 8,066.45 | 7,089.70 | 6,753.93 | 6,635.29 | 6,301.05 | 7,307.80 |
| 10 | `DEL-SXR` | 17,747.77 | 6,792.77 | 7,188.60 | 11,234.08 | 6,973.20 | 10,674.77 |
| 11 | `BLR-CCU` | 10,863.96 | 13,310.32 | 14,588.99 | 12,045.72 | 9,612.83 | 9,921.08 |
| 12 | `MAA-BOM` | 9,792.01 | 9,667.61 | 7,715.00 | 7,977.49 | 7,516.28 | 8,557.06 |
| 13 | `BLR-HYD` | 9,281.74 | 9,398.21 | 6,813.65 | 8,429.98 | 6,311.03 | 5,714.31 |
| 14 | `AMD-BOM` | 9,725.21 | 6,310.62 | 6,505.87 | 6,714.05 | 6,364.83 | 10,695.62 |
| 15 | `CCU-BOM` | 10,868.57 | 13,351.59 | 8,939.23 | 13,322.44 | 13,540.05 | 11,506.53 |
| 16 | `BLR-PNQ` | 7,530.29 | 9,032.56 | 4,498.07 | 4,402.88 | 5,968.37 | 6,849.00 |
| 17 | `GOI-DEL` | 12,170.68 | 20,299.80 | 8,763.20 | 8,754.25 | 9,743.75 | 8,907.64 |
| 18 | `MAA-HYD` | 10,228.63 | 9,242.21 | 6,685.27 | 6,983.18 | 6,129.11 | 5,896.21 |
| 19 | `DEL-GAU` | 9,936.40 | 8,446.92 | 8,760.43 | 10,084.77 | 9,915.32 | 10,632.47 |
| 20 | `BLR-COK` | 4,296.55 | 8,502.98 | 5,942.19 | 10,185.85 | 4,261.14 | 7,844.66 |
| 21 | `DEL-LKO` | 4,782.61 | 4,353.10 | 4,246.85 | 4,350.25 | 4,287.99 | 4,808.65 |
| 22 | `GOI-BOM` | 11,394.61 | 16,174.58 | 6,232.21 | 5,974.76 | 5,913.46 | 6,654.24 |
| 23 | `BLR-MAA` | 4,230.46 | 7,798.34 | 6,630.47 | 5,551.52 | 4,069.23 | 4,914.50 |
| 24 | `DEL-PAT` | 8,443.76 | 7,857.81 | 6,799.11 | 7,897.85 | 6,795.66 | 14,281.49 |
| 25 | `JAI-BOM` | 11,191.61 | 14,005.92 | 8,586.81 | 8,388.84 | 9,309.32 | 12,260.44 |
| 26 | `ATQ-DEL` | 4,095.28 | 14,431.38 | 4,784.89 | 7,335.54 | 5,721.29 | 6,670.48 |
| 27 | `COK-BOM` | 10,190.64 | 11,350.09 | 7,870.29 | 7,774.53 | 7,765.20 | 10,240.38 |
| 28 | `HYD-CCU` | 10,338.19 | 10,569.11 | 11,912.35 | 12,444.45 | 8,092.45 | 9,898.37 |
| 29 | `BBI-DEL` | 13,725.22 | 18,599.90 | 10,598.91 | 16,419.17 | 10,759.43 | 10,413.94 |
| 30 | `BLR-GOI` | 13,456.80 | 3,669.48 | 4,053.18 | 6,670.19 | 4,597.39 | 4,249.62 |
| 31 | `GAU-CCU` | 6,469.69 | 8,738.93 | 6,007.17 | 8,250.22 | 7,183.41 | 6,236.41 |
| 32 | `GOX-BOM` | 15,337.07 | 19,043.04 | 6,425.89 | 6,785.82 | 4,883.25 | 5,127.77 |
| 33 | `IXB-DEL` | 6,920.24 | 12,333.11 | 7,975.35 | 11,479.94 | 10,897.42 | 8,837.31 |
| 34 | `DEL-COK` | 10,638.63 | 11,852.90 | 10,666.95 | 14,367.04 | 11,480.51 | 14,319.43 |
| 35 | `MAA-CCU` | 11,079.67 | 10,209.69 | 12,714.79 | 11,485.93 | 9,752.51 | 9,635.42 |
| 36 | `DEL-GOX` | 8,440.11 | 8,130.50 | 9,133.95 | 8,983.45 | 7,633.39 | 10,485.76 |
| 37 | `LKO-BOM` | 8,131.05 | 8,549.78 | 7,037.00 | 6,534.17 | 8,021.46 | 13,207.55 |
| 38 | `DEL-IXR` | 7,349.89 | 8,105.83 | 8,317.67 | 8,855.96 | 8,820.09 | 10,425.03 |
| 39 | `GOI-HYD` | 15,580.23 | 21,585.27 | 9,345.43 | 7,967.68 | 6,007.75 | 5,719.93 |
| 40 | `AMD-BLR` | 9,258.30 | 8,574.93 | 7,790.25 | 8,304.53 | 8,437.53 | 13,883.91 |
| 41 | `DEL-IDR` | 8,066.20 | 7,268.88 | 6,607.39 | 6,627.45 | 6,624.72 | 6,746.51 |
| 42 | `IXC-DEL` | 8,667.70 | 7,880.75 | 5,673.89 | 5,459.10 | 5,484.30 | 5,997.60 |
| 43 | `DEL-IXL` | 8,156.49 | 6,989.84 | 5,270.69 | 7,062.98 | 5,140.82 | 5,476.15 |
| 44 | `MAA-CJB` | 12,034.44 | 9,962.99 | 5,404.19 | 5,194.33 | 5,221.37 | 6,877.21 |
| 45 | `BLR-TRV` | 9,731.42 | 6,669.17 | 7,792.70 | 10,201.65 | 7,225.93 | 8,445.28 |
| 46 | `HYD-VTZ` | 5,317.47 | 6,670.71 | 4,830.68 | 6,412.83 | 10,544.21 | 6,458.00 |
| 47 | `BLR-BBI` | 18,847.62 | 14,827.96 | 17,786.42 | 13,498.17 | 9,340.93 | 7,826.36 |
| 48 | `DEL-VNS` | 9,031.89 | 6,775.23 | 6,296.93 | 7,931.89 | 6,152.05 | 8,107.90 |
| 49 | `IXA-CCU` | 4,383.32 | 4,148.91 | 4,724.13 | 6,627.88 | 8,024.48 | 4,821.16 |
| 50 | `DEL-RPR` | 10,173.36 | 8,352.22 | 7,504.01 | 7,475.01 | 7,214.77 | 7,088.05 |
| 51 | `BOM-VNS` | 11,105.91 | 5,871.84 | 7,255.13 | 7,627.02 | 7,635.66 | 10,810.32 |
| 52 | `BLR-VNS` | 12,810.34 | 9,259.97 | 10,162.55 | 10,384.80 | 8,978.83 | 10,376.74 |
| 53 | `BLR-GAU` | 14,135.13 | 12,837.87 | 12,735.85 | 16,992.43 | 11,691.13 | 12,489.93 |
| 54 | `BLR-LKO` | 8,617.02 | 10,177.13 | 11,363.75 | 12,200.80 | 10,561.26 | 9,611.13 |
| 55 | `CJB-BOM` | 16,994.07 | 12,254.58 | 8,752.68 | 11,153.19 | 10,377.64 | 9,483.38 |
| 56 | `IDR-BOM` | 7,197.64 | 10,151.29 | 6,841.80 | 6,855.13 | 7,087.09 | 7,841.90 |
| 57 | `BLR-JAI` | 9,473.47 | 9,427.10 | 9,486.45 | 9,935.01 | 10,144.95 | 9,381.46 |
| 58 | `HYD-TIR` | 10,123.03 | 5,975.23 | 6,282.55 | 6,453.32 | 7,217.87 | 7,034.60 |
| 59 | `HYD-COK` | 10,461.50 | 11,494.63 | 10,186.62 | 12,069.68 | 7,483.30 | 9,357.31 |
| 60 | `BOM-NAG` | 6,579.61 | 6,421.58 | 6,108.92 | 6,153.36 | 6,280.44 | 7,017.62 |

---

## 4. Table B: Route-Level Reference Prices

Calculated as $P_r = \sum_L w_L \cdot P_{(r,L)}$ using empirical weights: $w_{T+1}=0.0509$, $w_{T+7}=0.1350$, $w_{T+15}=0.1491$, $w_{T+21}=0.1519$, $w_{T+30}=0.2588$, $w_{T+45}=0.2543$.

| Rank | Route | City Pair | DGCA_weight | route_reference_price (₹) | Weighted Contribution (₹) |
| :---: | :--- | :--- | :---: | :---: | :---: |
| 1 | `DEL-BOM` | DELHI – MUMBAI | 0.07484135 | 6,402.97 | 479.21 |
| 2 | `BLR-DEL` | BENGALURU – DELHI | 0.05175940 | 9,877.58 | 511.26 |
| 3 | `BLR-BOM` | BENGALURU – MUMBAI | 0.04615148 | 7,993.16 | 368.90 |
| 4 | `DEL-HYD` | DELHI – HYDERABAD | 0.03566176 | 10,553.77 | 376.37 |
| 5 | `DEL-PNQ` | DELHI – PUNE | 0.03159143 | 9,514.86 | 300.59 |
| 6 | `DEL-CCU` | DELHI – KOLKATA | 0.02997911 | 11,296.48 | 338.66 |
| 7 | `AMD-DEL` | AHMEDABAD – DELHI | 0.02706171 | 7,460.85 | 201.90 |
| 8 | `MAA-DEL` | CHENNAI – DELHI | 0.02635744 | 11,156.85 | 294.07 |
| 9 | `HYD-BOM` | HYDERABAD – MUMBAI | 0.02606979 | 6,871.69 | 179.14 |
| 10 | `DEL-SXR` | DELHI – SRINAGAR | 0.02602129 | 9,117.92 | 237.26 |
| 11 | `BLR-CCU` | BENGALURU – KOLKATA | 0.02538815 | 11,365.56 | 288.55 |
| 12 | `MAA-BOM` | CHENNAI – MUMBAI | 0.02449531 | 8,286.90 | 202.99 |
| 13 | `BLR-HYD` | BENGALURU – HYDERABAD | 0.02448314 | 7,124.07 | 174.42 |
| 14 | `AMD-BOM` | AHMEDABAD – MUMBAI | 0.02334709 | 7,703.95 | 179.86 |
| 15 | `CCU-BOM` | KOLKATA – MUMBAI | 0.02239618 | 12,142.47 | 271.94 |
| 16 | `BLR-PNQ` | BENGALURU – PUNE | 0.02085407 | 6,228.46 | 129.89 |
| 17 | `GOI-DEL` | DABOLIM – DELHI | 0.01747668 | 10,783.22 | 188.45 |
| 18 | `MAA-HYD` | CHENNAI – HYDERABAD | 0.01683972 | 6,911.47 | 116.39 |
| 19 | `DEL-GAU` | DELHI – GUWAHATI | 0.01665173 | 9,754.07 | 162.42 |
| 20 | `BLR-COK` | BENGALURU – KOCHI | 0.01630521 | 6,897.49 | 112.47 |
| 21 | `DEL-LKO` | DELHI – LUCKNOW | 0.01619374 | 4,457.68 | 72.19 |
| 22 | `GOI-BOM` | DABOLIM – MUMBAI | 0.01595915 | 7,822.92 | 124.85 |
| 23 | `BLR-MAA` | BENGALURU – CHENNAI | 0.01553383 | 5,402.86 | 83.93 |
| 24 | `DEL-PAT` | DELHI – PATNA | 0.01502436 | 9,094.52 | 136.64 |
| 25 | `JAI-BOM` | JAIPUR – MUMBAI | 0.01362684 | 10,542.09 | 143.66 |
| 26 | `ATQ-DEL` | AMRITSAR – DELHI | 0.01346019 | 7,161.36 | 96.39 |
| 27 | `COK-BOM` | KOCHI – MUMBAI | 0.01293641 | 9,019.14 | 116.68 |
| 28 | `HYD-CCU` | HYDERABAD – KOLKATA | 0.01260405 | 10,230.97 | 128.95 |
| 29 | `BBI-DEL` | BHUBANESWAR – DELHI | 0.01220249 | 12,716.78 | 155.18 |
| 30 | `BLR-GOI` | BENGALURU – DABOLIM | 0.01205341 | 5,068.34 | 61.09 |
| 31 | `GAU-CCU` | GUWAHATI – KOLKATA | 0.01183655 | 7,102.92 | 84.07 |
| 32 | `GOX-BOM` | GOA – MUMBAI | 0.01159460 | 7,908.11 | 91.69 |
| 33 | `IXB-DEL` | BAGDOGRA – DELHI | 0.01147485 | 10,017.72 | 114.95 |
| 34 | `DEL-COK` | DELHI – KOCHI | 0.01101561 | 12,527.03 | 137.99 |
| 35 | `MAA-CCU` | CHENNAI – KOLKATA | 0.01096981 | 10,556.99 | 115.81 |
| 36 | `DEL-GOX` | DELHI – GOA | 0.01032483 | 8,895.73 | 91.85 |
| 37 | `LKO-BOM` | LUCKNOW – MUMBAI | 0.01012383 | 9,044.48 | 91.56 |
| 38 | `DEL-IXR` | DELHI – RANCHI | 0.01008714 | 8,987.50 | 90.66 |
| 39 | `GOI-HYD` | DABOLIM – HYDERABAD | 0.01002029 | 9,320.12 | 93.39 |
| 40 | `AMD-BLR` | AHMEDABAD – BENGALURU | 0.00992059 | 9,766.16 | 96.89 |
| 41 | `DEL-IDR` | DELHI – INDORE | 0.00979261 | 6,813.86 | 66.73 |
| 42 | `IXC-DEL` | CHANDIGARH – DELHI | 0.00962106 | 6,124.83 | 58.93 |
| 43 | `DEL-IXL` | DELHI – LEH | 0.00944974 | 5,940.55 | 56.14 |
| 44 | `MAA-CJB` | CHENNAI – COIMBATORE | 0.00931591 | 6,652.51 | 61.97 |
| 45 | `BLR-TRV` | BENGALURU – TRIVANDRUM | 0.00922258 | 8,124.89 | 74.93 |
| 46 | `HYD-VTZ` | HYDERABAD – VISAKHAPATNAM | 0.00912967 | 7,236.68 | 66.07 |
| 47 | `BLR-BBI` | BENGALURU – BHUBANESWAR | 0.00897736 | 12,071.12 | 108.37 |
| 48 | `DEL-VNS` | DELHI – VARANASI | 0.00871547 | 7,172.10 | 62.51 |
| 49 | `IXA-CCU` | AGARTALA – KOLKATA | 0.00858593 | 5,797.11 | 49.77 |
| 50 | `DEL-RPR` | DELHI – RAIPUR | 0.00839443 | 7,569.35 | 63.54 |
| 51 | `BOM-VNS` | MUMBAI – VARANASI | 0.00815319 | 8,323.45 | 67.86 |
| 52 | `BLR-VNS` | BENGALURU – VARANASI | 0.00814572 | 9,957.36 | 81.11 |
| 53 | `BLR-GAU` | BENGALURU – GUWAHATI | 0.00811640 | 13,134.51 | 106.60 |
| 54 | `BLR-LKO` | BENGALURU – LUCKNOW | 0.00802087 | 10,537.52 | 84.52 |
| 55 | `CJB-BOM` | COIMBATORE – MUMBAI | 0.00782849 | 10,615.92 | 83.11 |
| 56 | `IDR-BOM` | INDORE – MUMBAI | 0.00776197 | 7,626.53 | 59.20 |
| 57 | `BLR-JAI` | BENGALURU – JAIPUR | 0.00765834 | 9,689.63 | 74.21 |
| 58 | `HYD-TIR` | HYDERABAD – TIRUPATI | 0.00758223 | 6,895.79 | 52.29 |
| 59 | `HYD-COK` | HYDERABAD – KOCHI | 0.00748874 | 9,752.72 | 73.04 |
| 60 | `BOM-NAG` | MUMBAI – NAGPUR | 0.00734468 | 6,457.31 | 47.43 |

---

## 5. Mathematical Proof of Basket Aggregation

$$\sum_{r=1}^{60} W_r = 1.00000000$$
$$\sum_{L \in \text{LeadTimes}} w_L = 0.0509 + 0.1350 + 0.1491 + 0.1519 + 0.2588 + 0.2543 = 1.0000$$

$$P_{\text{ref}} = \sum_{r=1}^{60} W_r \left( \sum_{L} w_L P_{(r,L)} \right) = \mathbf{8641.44995963945\dots} \approx \mathbf{₹8,641.45}$$