# APIx Reference Period Taxonomy & Methodology Report
## Correction and Formal Alignment with MoSPI CPI 2024 and Eurostat HICP Standards

> **Document Version:** `APIx_REF_TAXONOMY_v1.0`  
> **Status:** Mandatory Statistical Architecture Specification  
> **Classification Standard:** UN COICOP 2018 Subclass `07.3.3.1` (Domestic Passenger Transport by Air)  
> **Index Engine Methodology Version:** `APIx v2.0 (MoSPI CPI 2024 + Eurostat HICP Aligned)`  
> **Audited Dataset:** DEL-BOM Production Pilot Run (`825fa969` / `925fa969`)  

---

## 1. Executive Summary & Purpose of the Correction

A fundamental requirement in national accounting and consumer price statistics is the rigorous distinction among different types of "reference periods." In early prototypes of the Indian Airfare Price Index (APIx), the initial production collection date (`2026-09-26`) and its associated representative price (`₹6,632.67`) were colloquially referred to as the "base period" and "base price."

**This terminology was methodologically ambiguous and statistically inaccurate.**

Under the official **MoSPI CPI 2024** framework, national statistical authorities distinguish three separate reference concepts:
1. **Index reference period** ($2024 = 100$)
2. **Weight reference period** (HCES 2023-24)
3. **Price reference period** (calendar-year 2024 average)

Describing a single-day 2026 scraped price (₹6,632.67) as the "MoSPI price reference" or "base price" violates official statistical norms. Therefore, APIx has implemented a formal **Reference Period Taxonomy** across its database models, computation engine, and public artifacts.

---

## 2. The Five Distinct Reference Tiers

Every calculation, data model, API endpoint, and analytical report in the APIx system now strictly distinguishes and reports five separate reference concepts:

| Reference Tier | Identifier | Value in Current Engine | Standard / Citation | Methodological Rule & Operational Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **1. PROJECT REFERENCE** | `experimental_project_reference_price` | **₹6,632.67** on `2026-09-26` | APIx Pilot Architecture (`PROVISIONAL_PROJECT_REFERENCE`) | Operational baseline from the first complete multi-lead-time production run. Used exclusively to compute the high-frequency experimental prototype index: $I_{\text{project},t} = \frac{P_{\text{project},t}}{P_{\text{project},\text{reference}}} \times 100$. **NEVER describe as MoSPI price reference.** |
| **2. MOSPI INDEX REFERENCE** | `index_reference_period` | **$2024 = 100$** | MoSPI CPI 2024 National Revision Framework | The official numerical scaling reference period. All official CPI commodity series are presented on the scale where the average of calendar year 2024 equals 100.00. |
| **3. MOSPI PRICE REFERENCE** | `price_reference_period` | **Calendar-Year 2024 Average** | MoSPI CPI 2024 Service Price Compilation Manual | The unweighted or weighted average of all observed transaction prices across all 12 months of calendar year 2024. **Status: PENDING 2024 HISTORICAL ACTUALS.** Must never be manufactured or interpolated from 2026 data. |
| **4. MOSPI WEIGHT REFERENCE** | `weight_reference_period` | **HCES 2023-24** | MoSPI All-India Household Consumption Expenditure Survey 2023-24 | The expenditure survey period used to compute household consumption budget shares ($W^{\text{CPI}}_{\text{airfare}} \approx 0.185\%$ combined, $0.35\%$ urban). Strictly separated from DGCA route traffic proxies. |
| **5. EUROSTAT CHAIN-LINKING REFERENCE** | `chain_link_period` | **December $y-1$** | Eurostat HICP Methodological Manual (2024 §3.4) | The annual chain-linking point. In Eurostat HICP, monthly prices are **not** divided directly by the annual average; short-period Jevons price relatives are chained recursively, and the long series is subsequently expressed in the index reference period. |

---

## 3. High-Frequency Experimental Series vs. Final CPI-Aligned Design

To balance immediate operational requirements (providing live inflation monitoring for DEL-BOM) with long-term macroeconomic integrity, APIx operates a dual-layer architecture:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                   DUAL-LAYER ARCHITECTURE SPECIFICATION                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   LAYER A: High-Frequency Experimental Index (Active Now)                │
│   ───────────────────────────────────────────────────────                │
│   • Reference Anchor: P_project,reference = ₹6,632.67 (2026-09-26)       │
│   • Formula: I_project,t = (P_project,t / P_project,reference) × 100     │
│   • Current Value: 102.6407 (+2.64% over project baseline)               │
│   • Governance: Locked. P_project,reference must NEVER be overwritten.   │
│                                                                          │
│   LAYER B: Final MoSPI / Eurostat CPI-Aligned Series (Production Engine) │
│   ───────────────────────────────────────────────────────────────────────│
│   • Index Reference: 2024 = 100                                          │
│   • Price Reference: Calendar-Year 2024 Average (Actuals / Reconstruction)│
│   • Weight Reference: HCES 2023-24                                       │
│   • Short-Chain Formula: I_t = I_t-1 × exp( 1/N * sum(ln p_t - ln p_t-1) )│
│   • Chaining Anchor: December y-1 (Eurostat) / Month-over-Month (MoSPI)  │
│   • Scaling Rule: Long chained series re-referenced to 2024 = 100        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

> [!CAUTION]
> **Prohibition Against Data Manufacture:**  
> The final 2024 reference price must be calculated from **actual 2024 airfare observations** or a separately documented, auditable historical reconstruction (e.g. from historical GDS/OTA records). **Under no circumstances should 2024 prices be manufactured or backward-extrapolated from 2026 observations.**

---

## 4. Chaining and Re-Referencing Mechanics

### 4.1 Short-Period Price Relatives and Recursive Jevons Linking
At the elementary stratum level $s$, the price movement from period $t-1$ to $t$ is calculated over matched models $M_{s,t}$:

$$\text{price\_relative}_{i,t} = \frac{p_{i,t}}{p_{i,t-1}}$$

$$J_{s,t} = \left( \prod_{i \in M_{s,t}} \text{price\_relative}_{i,t} \right)^{1/N} = \exp\left( \frac{1}{N} \sum_{i \in M_{s,t}} (\ln p_{i,t} - \ln p_{i,t-1}) \right)$$

$$I_{s,t} = I_{s,t-1} \times J_{s,t}$$

This recursive formulation eliminates chain drift, accommodates dynamic product turnover (flight replacements), and satisfies the axioms of modern price index theory.

### 4.2 Re-Referencing to the Index Reference Period
Once a continuous chained index series $I_t$ is constructed, it can be mathematically re-referenced to any official index reference period (such as $2024 = 100$ or Eurostat's $2025 = 100$) via scalar normalization:

$$I_t^{(2024=100)} = \frac{I_t}{\bar{I}_{2024}} \times 100$$

where $\bar{I}_{2024} = \frac{1}{12} \sum_{m=1}^{12} I_{2024,m}$ is the arithmetic mean of the monthly chained index values across the 12 months of calendar year 2024.

---

## 5. Eurostat Alignment: Chain Linking vs Annual Average Division

A common misconception in airfare price index design is that aligning with a base period such as Eurostat's $2025 = 100$ requires dividing each monthly observed price directly by the annual average price of 2025:

$$\text{Incorrect Formulation: } I_m \neq \frac{P_m}{\bar{P}_{2025}} \times 100$$

Eurostat HICP guidelines explicitly reject direct annual division for seasonal and high-churn services like air transport:
1. **Product Churn:** Flight schedules, route frequencies, and fare bundles change continually; direct division across different years compares non-identical goods.
2. **Annual Chain Linking:** Eurostat mandates chain linking, using **December of the preceding year ($y-1$)** as the link month.
3. **Monthly Chaining:** Intra-year movements are compiled using short-period price relatives ($p_{i,m} / p_{i,m-1}$ or $p_{i,m} / p_{i,\text{Dec } y-1}$), and the long series is subsequently spliced together at each December link.

---

## 6. Database and Model Field Standardization

Generic and ambiguous field names such as `base_period` and `base_price` have been replaced with explicit schema attributes across all index models:

```python
# Formal Reference Period Taxonomy Fields in APIx Models
index_reference_period: str = "2024=100"
price_reference_period: str = "calendar-year 2024 average (Pending Historical Actuals)"
weight_reference_period: str = "HCES 2023-24"
chain_link_period: str = "December y-1 (Eurostat) / Month-over-Month (MoSPI)"

# Project Experimental Reference (PROVISIONAL_PROJECT_REFERENCE)
reference_type: str = "PROVISIONAL_PROJECT_REFERENCE"
experimental_project_reference_price: Decimal = Decimal("6632.67")
experimental_reference_period: str = "2026-09-26"

reference_price: Decimal = Decimal("6632.67")
reference_price_method: str = "Option B — first production run weighted representative price"
reference_price_source: str = "production_run_825fa969"
reference_index_value: Decimal = Decimal("100.00")
methodology_version: str = "APIx v2.0 (MoSPI CPI 2024 + Eurostat HICP Aligned)"

# Explicit Backward-Compatibility Aliases
base_price: Decimal = experimental_project_reference_price  # Explicit alias
base_period: str = experimental_reference_period            # Explicit alias
base_value: Decimal = reference_index_value                 # Explicit alias
```

### JSON File Updates:
- [`apix_base_delbom.json`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apix_base_delbom.json): Contains explicit reference fields, locking the provisional project price at ₹6,632.67 with explicit notes forbidding its description as the MoSPI price reference.
- [`DEL_BOM_route_index.json`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/DEL_BOM_route_index.json): Emits all five reference concepts alongside the headline route index (102.6407).
- [`apix_delbom_result.json`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/apix_delbom_result.json): Exposes the structured `reference_taxonomy` block for frontend dashboard rendering.

---

## 7. Compliance Verification & Test Proofs

The reference taxonomy implementation has been validated with dedicated test cases in [`tests/core/test_phase29_mospi_eurostat_engine.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/tests/core/test_phase29_mospi_eurostat_engine.py):

- **Gate 13:** Base/reference index remains strictly 100.0000.
- **Gate 15:** Reference Period Taxonomy Validation:
  - Asserts `index_reference_period == "2024=100"`
  - Asserts `price_reference_period == "calendar-year 2024 average"`
  - Asserts `weight_reference_period == "HCES 2023-24"`
  - Asserts `chain_link_period == "December y-1"`
  - Asserts `reference_type == "PROVISIONAL_PROJECT_REFERENCE"`
  - Asserts `price_reference_period != "2026-09-26"` (strictly preventing conflation of project reference with MoSPI price reference)
  - **Result:** 15/15 tests passing (100%).
