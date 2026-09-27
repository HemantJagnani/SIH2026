# APIx Reference Coverage Audit: DGCA Top-60 Routes × 6 Lead-Time Matrix

**Audit Date:** 2026-09-27  
**Standard:** `APIX_METHODOLOGY_V1` / `APIx_PRODUCT_DEF_v2.0_FROZEN`  
**Target Universe:** 60 DGCA Domestic Routes × 6 Lead-Time Classes ($T+1, T+7, T+15, T+21, T+30, T+45$) = **360 Cells**  
**Weights Framework:** Finalized DGCA CY2024 Top-60 Route Weights ($W_r$) & Empirical Booking Lead-Time Weights ($w_L$)  

---

## 1. Executive Summary: Matrix Coverage Statistics

| Metric | Value | Percentage | Notes |
| :--- | :---: | :---: | :--- |
| **Total Target Matrix Cells** | **360** | 100.00% | 60 DGCA routes × 6 lead-time horizons |
| **Populated Matrix Cells** | **60** | **16.67%** | Ranks 1 to 10 active across all 6 horizons |
| **Missing Matrix Cells** | **300** | **83.33%** | Ranks 11 to 60 (50 routes × 6 horizons unobserved) |
| **Route Dimension Coverage** | 10 / 60 | 16.67% | Top-10 routes populated |
| **Lead-Time Dimension Coverage** | 6 / 6 | 100.00% | All 6 advance horizons active ($T+1$ to $T+45$) |
| **DGCA Top-60 Basket Weighted Coverage ($W_r$)** | **0.375495** | **37.5495%** | Cumulative weight of Ranks 1–10 in Top-60 basket |
| **DGCA All-India Passenger Traffic Coverage** | 34,547,489 pax | **21.4126%** | Share of 161,325,253 total annual domestic passengers |
| **Total Raw Scraped Observations Audited** | **5,218** | — | 2,432 (DEL-BOM) + 2,786 (Ranks 2–10 expansion) |
| **Total Valid Baseline Observations** | **2,423** | — | Unique, domestic adult economy baseline fares |

---

## 2. Populated Cells Audit (All 60 Cells)

For every populated cell $(r, L)$, the table below details the route, rank, lead time, valid observation count, median fare, and geometric mean fare:

| Rank | Route ID | Route Name | Lead Time | Raw Obs | Valid Obs | Median Fare (INR) | Geometric Mean Fare (INR) | Route Weight ($W_r$) |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `DEL-BOM` | DELHI - MUMBAI | **T+1** | 194 | **137** | ₹11,670.00 | **₹11,973.78** | 0.074841 |
| 1 | `DEL-BOM` | DELHI - MUMBAI | **T+7** | 722 | **190** | ₹6,530.00 | **₹7,643.16** | 0.074841 |
| 1 | `DEL-BOM` | DELHI - MUMBAI | **T+15** | 215 | **150** | ₹6,771.00 | **₹7,298.78** | 0.074841 |
| 1 | `DEL-BOM` | DELHI - MUMBAI | **T+21** | 748 | **189** | ₹7,120.00 | **₹7,942.92** | 0.074841 |
| 1 | `DEL-BOM` | DELHI - MUMBAI | **T+30** | 276 | **199** | ₹7,207.00 | **₹8,204.28** | 0.074841 |
| 1 | `DEL-BOM` | DELHI - MUMBAI | **T+45** | 277 | **194** | ₹9,136.00 | **₹9,741.72** | 0.074841 |
| 2 | `BLR-DEL` | BENGALURU - DELHI | **T+1** | 66 | **33** | ₹8,714.00 | **₹10,800.55** | 0.051759 |
| 2 | `BLR-DEL` | BENGALURU - DELHI | **T+7** | 80 | **40** | ₹10,045.00 | **₹9,917.22** | 0.051759 |
| 2 | `BLR-DEL` | BENGALURU - DELHI | **T+15** | 82 | **41** | ₹9,250.00 | **₹9,261.76** | 0.051759 |
| 2 | `BLR-DEL` | BENGALURU - DELHI | **T+21** | 82 | **41** | ₹10,699.00 | **₹10,789.54** | 0.051759 |
| 2 | `BLR-DEL` | BENGALURU - DELHI | **T+30** | 84 | **42** | ₹9,549.00 | **₹9,623.40** | 0.051759 |
| 2 | `BLR-DEL` | BENGALURU - DELHI | **T+45** | 84 | **42** | ₹9,659.00 | **₹9,746.78** | 0.051759 |
| 3 | `BLR-BOM` | BENGALURU - MUMBAI | **T+1** | 56 | **28** | ₹8,853.50 | **₹10,388.30** | 0.046151 |
| 3 | `BLR-BOM` | BENGALURU - MUMBAI | **T+7** | 58 | **29** | ₹9,971.00 | **₹8,595.09** | 0.046151 |
| 3 | `BLR-BOM` | BENGALURU - MUMBAI | **T+15** | 60 | **30** | ₹6,926.00 | **₹6,877.72** | 0.046151 |
| 3 | `BLR-BOM` | BENGALURU - MUMBAI | **T+21** | 62 | **31** | ₹7,362.00 | **₹7,366.50** | 0.046151 |
| 3 | `BLR-BOM` | BENGALURU - MUMBAI | **T+30** | 80 | **40** | ₹7,637.00 | **₹7,470.46** | 0.046151 |
| 3 | `BLR-BOM` | BENGALURU - MUMBAI | **T+45** | 76 | **38** | ₹8,643.00 | **₹8,754.47** | 0.046151 |
| 4 | `DEL-HYD` | DELHI - HYDERABAD | **T+1** | 54 | **27** | ₹8,874.00 | **₹10,582.58** | 0.035662 |
| 4 | `DEL-HYD` | DELHI - HYDERABAD | **T+7** | 60 | **30** | ₹12,907.00 | **₹13,032.61** | 0.035662 |
| 4 | `DEL-HYD` | DELHI - HYDERABAD | **T+15** | 62 | **31** | ₹9,289.00 | **₹9,433.50** | 0.035662 |
| 4 | `DEL-HYD` | DELHI - HYDERABAD | **T+21** | 60 | **30** | ₹10,397.00 | **₹10,366.34** | 0.035662 |
| 4 | `DEL-HYD` | DELHI - HYDERABAD | **T+30** | 60 | **30** | ₹9,858.00 | **₹9,682.17** | 0.035662 |
| 4 | `DEL-HYD` | DELHI - HYDERABAD | **T+45** | 54 | **27** | ₹10,968.00 | **₹10,887.86** | 0.035662 |
| 5 | `DEL-PNQ` | DELHI - PUNE | **T+1** | 44 | **22** | ₹9,489.50 | **₹10,809.67** | 0.031591 |
| 5 | `DEL-PNQ` | DELHI - PUNE | **T+7** | 50 | **25** | ₹12,250.00 | **₹11,762.40** | 0.031591 |
| 5 | `DEL-PNQ` | DELHI - PUNE | **T+15** | 46 | **23** | ₹7,050.00 | **₹7,138.11** | 0.031591 |
| 5 | `DEL-PNQ` | DELHI - PUNE | **T+21** | 54 | **27** | ₹8,504.00 | **₹8,790.87** | 0.031591 |
| 5 | `DEL-PNQ` | DELHI - PUNE | **T+30** | 56 | **28** | ₹8,055.00 | **₹8,202.42** | 0.031591 |
| 5 | `DEL-PNQ` | DELHI - PUNE | **T+45** | 58 | **29** | ₹11,192.00 | **₹11,224.18** | 0.031591 |
| 6 | `DEL-CCU` | DELHI - KOLKATA | **T+1** | 50 | **25** | ₹8,866.00 | **₹9,247.79** | 0.029979 |
| 6 | `DEL-CCU` | DELHI - KOLKATA | **T+7** | 62 | **31** | ₹8,867.00 | **₹9,240.94** | 0.029979 |
| 6 | `DEL-CCU` | DELHI - KOLKATA | **T+15** | 52 | **26** | ₹9,254.50 | **₹9,511.60** | 0.029979 |
| 6 | `DEL-CCU` | DELHI - KOLKATA | **T+21** | 66 | **33** | ₹14,221.00 | **₹13,158.71** | 0.029979 |
| 6 | `DEL-CCU` | DELHI - KOLKATA | **T+30** | 72 | **36** | ₹13,381.00 | **₹13,417.18** | 0.029979 |
| 6 | `DEL-CCU` | DELHI - KOLKATA | **T+45** | 60 | **30** | ₹11,071.00 | **₹10,573.67** | 0.029979 |
| 7 | `AMD-DEL` | AHMEDABAD - DELHI | **T+1** | 36 | **18** | ₹6,414.00 | **₹7,330.56** | 0.027062 |
| 7 | `AMD-DEL` | AHMEDABAD - DELHI | **T+7** | 40 | **18** | ₹6,612.50 | **₹6,712.81** | 0.027062 |
| 7 | `AMD-DEL` | AHMEDABAD - DELHI | **T+15** | 38 | **17** | ₹6,034.00 | **₹6,097.62** | 0.027062 |
| 7 | `AMD-DEL` | AHMEDABAD - DELHI | **T+21** | 38 | **17** | ₹6,039.00 | **₹6,124.48** | 0.027062 |
| 7 | `AMD-DEL` | AHMEDABAD - DELHI | **T+30** | 38 | **18** | ₹6,039.00 | **₹6,250.48** | 0.027062 |
| 7 | `AMD-DEL` | AHMEDABAD - DELHI | **T+45** | 32 | **16** | ₹10,455.50 | **₹10,713.36** | 0.027062 |
| 8 | `MAA-DEL` | CHENNAI - DELHI | **T+1** | 38 | **17** | ₹10,409.00 | **₹12,045.85** | 0.026357 |
| 8 | `MAA-DEL` | CHENNAI - DELHI | **T+7** | 48 | **22** | ₹13,592.00 | **₹12,789.62** | 0.026357 |
| 8 | `MAA-DEL` | CHENNAI - DELHI | **T+15** | 40 | **18** | ₹9,946.00 | **₹9,934.69** | 0.026357 |
| 8 | `MAA-DEL` | CHENNAI - DELHI | **T+21** | 44 | **20** | ₹10,874.00 | **₹10,679.16** | 0.026357 |
| 8 | `MAA-DEL` | CHENNAI - DELHI | **T+30** | 42 | **19** | ₹9,946.00 | **₹10,005.59** | 0.026357 |
| 8 | `MAA-DEL` | CHENNAI - DELHI | **T+45** | 52 | **23** | ₹12,630.00 | **₹12,285.66** | 0.026357 |
| 9 | `HYD-BOM` | HYDERABAD - MUMBAI | **T+1** | 36 | **16** | ₹6,269.00 | **₹8,066.45** | 0.026070 |
| 9 | `HYD-BOM` | HYDERABAD - MUMBAI | **T+7** | 42 | **20** | ₹6,961.00 | **₹7,089.70** | 0.026070 |
| 9 | `HYD-BOM` | HYDERABAD - MUMBAI | **T+15** | 40 | **18** | ₹6,297.50 | **₹6,753.93** | 0.026070 |
| 9 | `HYD-BOM` | HYDERABAD - MUMBAI | **T+21** | 44 | **20** | ₹6,344.00 | **₹6,635.29** | 0.026070 |
| 9 | `HYD-BOM` | HYDERABAD - MUMBAI | **T+30** | 36 | **16** | ₹6,269.00 | **₹6,301.05** | 0.026070 |
| 9 | `HYD-BOM` | HYDERABAD - MUMBAI | **T+45** | 34 | **17** | ₹7,424.00 | **₹7,307.80** | 0.026070 |
| 10 | `DEL-SXR` | DELHI - SRINAGAR | **T+1** | 22 | **11** | ₹18,140.00 | **₹17,747.77** | 0.026021 |
| 10 | `DEL-SXR` | DELHI - SRINAGAR | **T+7** | 28 | **14** | ₹6,873.50 | **₹6,792.77** | 0.026021 |
| 10 | `DEL-SXR` | DELHI - SRINAGAR | **T+15** | 30 | **15** | ₹6,892.00 | **₹7,188.60** | 0.026021 |
| 10 | `DEL-SXR` | DELHI - SRINAGAR | **T+21** | 30 | **15** | ₹10,070.00 | **₹11,234.08** | 0.026021 |
| 10 | `DEL-SXR` | DELHI - SRINAGAR | **T+30** | 34 | **17** | ₹6,948.00 | **₹6,973.20** | 0.026021 |
| 10 | `DEL-SXR` | DELHI - SRINAGAR | **T+45** | 34 | **17** | ₹9,944.00 | **₹10,674.77** | 0.026021 |

---

## 3. Missing Cells Audit (All 300 Cells)

Ranks 11 through 60 are currently unobserved in the production dataset. For each of the 50 missing routes, exactly 6 lead-time cells ($T+1, T+7, T+15, T+21, T+30, T+45$) are missing, totaling **300 missing cells**:

| Rank | Route ID | Origin City | Destination City | Annual Pax Volume | Basket Weight ($W_r$) | Missing Lead-Time Cells | Missing Cell Count |
| :---: | :---: | :--- | :--- | :---: | :---: | :--- | :---: |
| 11 | `BLR-CCU` | BENGALURU | KOLKATA | 2,335,591 | 0.025388 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 12 | `MAA-BOM` | CHENNAI | MUMBAI | 2,253,454 | 0.024495 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 13 | `BLR-HYD` | BENGALURU | HYDERABAD | 2,252,334 | 0.024483 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 14 | `AMD-BOM` | AHMEDABAD | MUMBAI | 2,147,823 | 0.023347 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 15 | `CCU-BOM` | KOLKATA | MUMBAI | 2,060,343 | 0.022396 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 16 | `BLR-PNQ` | BENGALURU | PUNE | 1,918,477 | 0.020854 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 17 | `GOI-DEL` | DABOLIM | DELHI | 1,607,773 | 0.017477 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 18 | `MAA-HYD` | CHENNAI | HYDERABAD | 1,549,175 | 0.016840 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 19 | `DEL-GAU` | DELHI | GUWAHATI | 1,531,881 | 0.016652 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 20 | `BLR-COK` | BENGALURU | KOCHI | 1,500,003 | 0.016305 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 21 | `DEL-LKO` | DELHI | LUCKNOW | 1,489,748 | 0.016194 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 22 | `GOI-BOM` | DABOLIM | MUMBAI | 1,468,167 | 0.015959 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 23 | `BLR-MAA` | BENGALURU | CHENNAI | 1,429,039 | 0.015534 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 24 | `DEL-PAT` | DELHI | PATNA | 1,382,171 | 0.015024 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 25 | `JAI-BOM` | JAIPUR | MUMBAI | 1,253,605 | 0.013627 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 26 | `ATQ-DEL` | AMRITSAR | DELHI | 1,238,274 | 0.013460 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 27 | `COK-BOM` | KOCHI | MUMBAI | 1,190,089 | 0.012936 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 28 | `HYD-CCU` | HYDERABAD | KOLKATA | 1,159,513 | 0.012604 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 29 | `BBI-DEL` | BHUBANESWAR | DELHI | 1,122,572 | 0.012202 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 30 | `BLR-GOI` | BENGALURU | DABOLIM | 1,108,857 | 0.012053 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 31 | `GAU-CCU` | GUWAHATI | KOLKATA | 1,088,907 | 0.011837 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 32 | `GOX-BOM` | GOA | MUMBAI | 1,066,649 | 0.011595 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 33 | `IXB-DEL` | BAGDOGRA | DELHI | 1,055,632 | 0.011475 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 34 | `DEL-COK` | DELHI | KOCHI | 1,013,384 | 0.011016 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 35 | `MAA-CCU` | CHENNAI | KOLKATA | 1,009,171 | 0.010970 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 36 | `DEL-GOX` | DELHI | GOA | 949,836 | 0.010325 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 37 | `LKO-BOM` | LUCKNOW | MUMBAI | 931,345 | 0.010124 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 38 | `DEL-IXR` | DELHI | RANCHI | 927,970 | 0.010087 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 39 | `GOI-HYD` | DABOLIM | HYDERABAD | 921,820 | 0.010020 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 40 | `AMD-BLR` | AHMEDABAD | BENGALURU | 912,648 | 0.009921 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 41 | `DEL-IDR` | DELHI | INDORE | 900,874 | 0.009793 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 42 | `IXC-DEL` | CHANDIGARH | DELHI | 885,092 | 0.009621 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 43 | `DEL-IXL` | DELHI | LEH | 869,332 | 0.009450 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 44 | `MAA-CJB` | CHENNAI | COIMBATORE | 857,020 | 0.009316 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 45 | `BLR-TRV` | BENGALURU | TRIVANDRUM | 848,434 | 0.009223 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 46 | `HYD-VTZ` | HYDERABAD | VISAKHAPATNAM | 839,887 | 0.009130 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 47 | `BLR-BBI` | BENGALURU | BHUBANESWAR | 825,875 | 0.008977 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 48 | `DEL-VNS` | DELHI | VARANASI | 801,782 | 0.008715 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 49 | `IXA-CCU` | AGARTALA | KOLKATA | 789,865 | 0.008586 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 50 | `DEL-RPR` | DELHI | RAIPUR | 772,248 | 0.008394 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 51 | `BOM-VNS` | MUMBAI | VARANASI | 750,055 | 0.008153 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 52 | `BLR-VNS` | BENGALURU | VARANASI | 749,368 | 0.008146 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 53 | `BLR-GAU` | BENGALURU | GUWAHATI | 746,671 | 0.008116 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 54 | `BLR-LKO` | BENGALURU | LUCKNOW | 737,882 | 0.008021 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 55 | `CJB-BOM` | COIMBATORE | MUMBAI | 720,184 | 0.007828 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 56 | `IDR-BOM` | INDORE | MUMBAI | 714,065 | 0.007762 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 57 | `BLR-JAI` | BENGALURU | JAIPUR | 704,531 | 0.007658 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 58 | `HYD-TIR` | HYDERABAD | TIRUPATI | 697,530 | 0.007582 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 59 | `HYD-COK` | HYDERABAD | KOCHI | 688,929 | 0.007489 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |
| 60 | `BOM-NAG` | MUMBAI | NAGPUR | 675,676 | 0.007345 | $T+1, T+7, T+15, T+21, T+30, T+45$ | 6 |

### 3.1 Missing Cell Enumeration by Lead Time

The 300 missing cells grouped by lead time are:
- **Lead Time T+1 (50 missing routes):** `BLR-CCU`, `MAA-BOM`, `BLR-HYD`, `AMD-BOM`, `CCU-BOM`, `BLR-PNQ`, `GOI-DEL`, `MAA-HYD`, `DEL-GAU`, `BLR-COK`, ... (+40 more, Ranks 11–60)
- **Lead Time T+7 (50 missing routes):** `BLR-CCU`, `MAA-BOM`, `BLR-HYD`, `AMD-BOM`, `CCU-BOM`, `BLR-PNQ`, `GOI-DEL`, `MAA-HYD`, `DEL-GAU`, `BLR-COK`, ... (+40 more, Ranks 11–60)
- **Lead Time T+15 (50 missing routes):** `BLR-CCU`, `MAA-BOM`, `BLR-HYD`, `AMD-BOM`, `CCU-BOM`, `BLR-PNQ`, `GOI-DEL`, `MAA-HYD`, `DEL-GAU`, `BLR-COK`, ... (+40 more, Ranks 11–60)
- **Lead Time T+21 (50 missing routes):** `BLR-CCU`, `MAA-BOM`, `BLR-HYD`, `AMD-BOM`, `CCU-BOM`, `BLR-PNQ`, `GOI-DEL`, `MAA-HYD`, `DEL-GAU`, `BLR-COK`, ... (+40 more, Ranks 11–60)
- **Lead Time T+30 (50 missing routes):** `BLR-CCU`, `MAA-BOM`, `BLR-HYD`, `AMD-BOM`, `CCU-BOM`, `BLR-PNQ`, `GOI-DEL`, `MAA-HYD`, `DEL-GAU`, `BLR-COK`, ... (+40 more, Ranks 11–60)
- **Lead Time T+45 (50 missing routes):** `BLR-CCU`, `MAA-BOM`, `BLR-HYD`, `AMD-BOM`, `CCU-BOM`, `BLR-PNQ`, `GOI-DEL`, `MAA-HYD`, `DEL-GAU`, `BLR-COK`, ... (+40 more, Ranks 11–60)

---

## 4. DGCA-Route-Weighted Coverage Analysis

Under the finalized DGCA CY2024 Top-60 route weighting scheme ($W_r$):

$$\text{Weighted Basket Coverage} = \sum_{r=1}^{10} W_r = 0.375495 \quad (\mathbf{37.55\%})$$
$$\text{Unobserved Basket Weight} = \sum_{r=11}^{60} W_r = 0.624505 \quad (\mathbf{62.45\%})$$

In terms of total Indian domestic scheduled passenger traffic:
$$\text{All-India Observed Traffic Share} = \sum_{r=1}^{10} \text{Share}_r = \mathbf{21.4126\%}$$
$$\text{All-India Unobserved Traffic Share (Top-60 Basket)} = \sum_{r=11}^{60} \text{Share}_r = \mathbf{35.6121\%}$$

### Top-10 Cumulative Weight Breakdown:

| Rank | Route ID | Route Name | DGCA CY2024 Pax | Basket Weight ($W_r$) | Cumulative Weight |
| :---: | :---: | :--- | :---: | :---: | :---: |
| 1 | `DEL-BOM` | DELHI - MUMBAI | 6,885,053 | 0.074841 | 0.074841 (7.48%) |
| 2 | `BLR-DEL` | BENGALURU - DELHI | 4,761,622 | 0.051759 | 0.126601 (12.66%) |
| 3 | `BLR-BOM` | BENGALURU - MUMBAI | 4,245,720 | 0.046151 | 0.172752 (17.28%) |
| 4 | `DEL-HYD` | DELHI - HYDERABAD | 3,280,715 | 0.035662 | 0.208414 (20.84%) |
| 5 | `DEL-PNQ` | DELHI - PUNE | 2,906,263 | 0.031591 | 0.240005 (24.00%) |
| 6 | `DEL-CCU` | DELHI - KOLKATA | 2,757,937 | 0.029979 | 0.269985 (27.00%) |
| 7 | `AMD-DEL` | AHMEDABAD - DELHI | 2,489,550 | 0.027062 | 0.297046 (29.70%) |
| 8 | `MAA-DEL` | CHENNAI - DELHI | 2,424,761 | 0.026357 | 0.323404 (32.34%) |
| 9 | `HYD-BOM` | HYDERABAD - MUMBAI | 2,398,298 | 0.026070 | 0.349473 (34.95%) |
| 10 | `DEL-SXR` | DELHI - SRINAGAR | 2,393,837 | 0.026021 | 0.375495 (37.55%) |

---

## 5. Sufficiency Assessment for Provisional Basket-Based Reference Price ($P_{\text{ref}}$)

The target specification for the basket-based reference price is defined as:

$$P_{\text{ref}} = \sum_{r=1}^{60} W_r \times \sum_{L \in \mathcal{L}} w_L \times P_{(r,L)}$$

where:
- $W_r$: Finalized DGCA CY2024 Top-60 route weights (summing to 1.000000 across 60 routes).
- $w_L$: Finalized empirical booking lead-time weights ($T+1: 0.0509, T+7: 0.1350, T+15: 0.1491, T+21: 0.1519, T+30: 0.2588, T+45: 0.2543$, summing to 1.0000).
- $P_{(r,L)}$: Elementary price for route $r$ at lead time $L$.

### 5.1 Determination: **INSUFFICIENT FOR FULL BASKET REFERENCE PRICE**

The current production dataset is **NOT sufficient** to calculate the official 60-route basket-based reference price $P_{\text{ref}}$.

#### Reasons:
1. **Missing 62.45% of Target Basket Weight:** Ranks 11–60 carry 62.45% of the Top-60 statistical weight. Without price observations for these 50 routes, evaluating the full summation $\sum_{r=1}^{60} W_r \dots$ would leave nearly two-thirds of the basket undefined.
2. **Missing 300 of 360 Matrix Cells (83.33%):** Only 60 of the 360 required cells are currently populated.
3. **Strict Zero-Fabrication Rule:** Methodology strictly forbids filling missing cells with synthetic imputations, unverified cross-route proxies, or heuristic averages.
4. **Explicit Prohibition on Legacy Fallbacks:** Legacy single-route pilot prices (specifically ₹6,632.67) are strictly excluded.

### 5.2 Conditional Feasibility of a Provisional Top-10 Pilot Sub-Index

While insufficient for the full Top-60 basket:
- **Lead-Time Completeness:** For the 10 populated routes, lead-time coverage is **100% complete** across all six horizons ($w_L$ evaluates to 1.0 with zero missing lead times).
- **Provisional Pilot Calculation Feasibility:** If authorized by governance as an interim measure, a provisional re-normalized Top-10 pilot price could be evaluated by scaling the Top-10 weights to unity ($W'_r = W_r / 0.375495$):

$$P_{\text{ref}}^{\text{Top10-Pilot}} = \sum_{r=1}^{10} \left( \frac{W_r}{\sum_{i=1}^{10} W_i} \right) \left( \sum_{L} w_L P_{(r,L)} \right)$$

> [!IMPORTANT]
> In accordance with the user instructions, **no reference price $P_{\text{ref}}$ was calculated**, no missing cells were filled, and legacy values (₹6,632.67) were not used.

---

## 6. Recommendations & Next Steps
1. **Matrix Expansion:** Schedule production crawler jobs for the remaining 50 routes (Ranks 11–60) across all six lead times to populate the 300 missing cells.
2. **Regulatory Reference Pricing:** Maintain the reference price calculation in abeyance until the full 360-cell matrix or an officially sanctioned provisional Top-10 pilot scope is mandated.
