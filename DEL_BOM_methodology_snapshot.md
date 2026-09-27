# APIx DEL-BOM Methodology Snapshot
## Alignment with MoSPI CPI 2024 Framework and Eurostat HICP 2024 Standards

> **Document Status:** Official Production Methodology Snapshot — Phase 29  
> **Route Identifier:** `DEL-BOM` (Indira Gandhi International Airport, Delhi ⇄ Chhatrapati Shivaji Maharaj International Airport, Mumbai)  
> **Methodology Version:** `APIx v2.0 (MoSPI CPI 2024 + Eurostat HICP Aligned)`  
> **Product Definition Version:** `APIx_PRODUCT_DEF_v2.0_FROZEN`  
> **Weight Version:** `2026.09` (`PROVISIONAL EQUAL LEAD-TIME WEIGHTS`, $w_L = 1/6$)  
> **Classification Standard:** UN COICOP 2018, Subclass `07.3.3.1` (Domestic Passenger Transport by Air)  
> **Target Frequency:** Monthly CPI-compatible series + High-Frequency daily diagnostic indicators  
> **Institutional Scope Note:** APIx is an experimental airfare price index engineered for potential Consumer Price Index (CPI) augmentation. It is **not** an official publication of MoSPI / NSO.

---

## 1. Executive Summary & Institutional Alignment

The Indian Airfare Price Index (APIx) has been re-architected in Phase 29 to achieve strict methodological alignment with international and national consumer price index compilation standards:

1. **MoSPI CPI 2024 Alignment:**
   - **Index Reference Period:** Adopts the $2024 = 100$ conceptual index reference scale.
   - **Classification:** Formally mapped to UN COICOP 2018 Subclass `07.3.3.1` (Domestic Passenger Transport by Air), matching the CPI 2024 commodity basket.
   - **Advance-Purchase Checkpoint:** Incorporates $T+21$ (21 days prior to departure) as the designated domestic airfare advance-booking reference period cited in MoSPI CPI 2024 Expert Group documentation.
   - **Elementary Index Formula:** Employs the unweighted Jevons geometric mean link for elementary aggregates.
   - **Higher-Level Aggregation:** Utilizes weighted arithmetic aggregation (Young / modified Laspeyres) across lead times and routes.
   - **Weight Separation:** Strictly separates DGCA passenger traffic share proxies from official MoSPI CPI household expenditure weights (HCES 2023-24).

2. **Eurostat HICP 2024 Alignment:**
   - **Data Treatment:** Treats web-scraped airfare data at the product-offer level, isolating pure price movements from transaction churn.
   - **Product Definition:** Freezes the headline product definition to the lowest qualifying mandatory-payable adult economy fare per itinerary.
   - **Short-Chain Linking:** Implements period-over-period recursive short chaining ($I_t = I_{t-1} \times J_t$) to accommodate frequent flight schedule replacements.
   - **Replacement & Quality Adjustment:** Enforces explicit replacement protocols, tracking 14 service characteristics and applying explicit quality adjustments for baggage and schedule changes.
   - **Zero-Price Axiom:** Strictly forbids treating sold-out or unavailable flights as ₹0.
   - **Multi-Source Treatment:** Evaluates scrapers (Google Flights and EaseMyTrip) as independent diagnostic channels rather than treating scraped row counts as statistical weights.

---

## 1.1 Formal Reference Period Taxonomy (Mandatory Distinction)

`[MO SPI REQUIREMENT / PRACTICE]` / `[EUROSTAT METHODOLOGICAL REFERENCE]`

To prevent fundamental methodological error, APIx strictly separates and distinguishes the five distinct reference concepts:

| Reference Concept | Standard / Authority | APIx Production Value | Methodological Rule & Operational Meaning |
| :--- | :--- | :--- | :--- |
| **1. PROJECT REFERENCE** | `PROVISIONAL_PROJECT_REFERENCE` (APIx Engine) | `₹6,632.67` on `2026-09-26` | First complete production run representative price. Used exclusively to compute the high-frequency prototype index: $I_{\text{project},t} = \frac{P_{\text{project},t}}{P_{\text{project},\text{reference}}} \times 100$. **DO NOT describe this as the MoSPI price reference!** |
| **2. MOSPI INDEX REFERENCE** | MoSPI CPI 2024 Framework | `2024 = 100` | The official numerical scaling reference period for the all-India CPI revision. |
| **3. MOSPI PRICE REFERENCE** | MoSPI CPI 2024 Specification | `calendar-year 2024 average` | The official reference price must be derived from actual calendar-year 2024 observations or a documented historical reconstruction. **Never manufactured from 2026 data.** |
| **4. MOSPI WEIGHT REFERENCE** | MoSPI National Sample Survey | `HCES 2023-24` | Household Consumption Expenditure Survey 2023-24 basket used to establish consumption expenditure weights ($W^{\text{CPI}}_{\text{airfare}} \approx 0.185\%$). |
| **5. EUROSTAT CHAIN-LINKING REFERENCE** | Eurostat HICP 2024 Manual §3 | `December y-1` | Annual linking point. Monthly prices are NOT directly divided by the annual average; short-period Jevons price relatives are chained recursively, and the long series is subsequently expressed in the index reference period. |

## 2. Frozen Headline Product Definition

`[PROJECT DESIGN CHOICE]` / `[EUROSTAT METHODOLOGICAL REFERENCE — HICP Manual 2024 §12.3]`

### 2.1 Specification
The headline APIx product is formally defined as:
> **"Lowest qualifying mandatory-payable domestic one-way adult economy airfare for a defined itinerary/product stratum."**

### 2.2 Mathematical Selection Rule
For every detected flight itinerary $k$ and advance-purchase horizon $l \in \{T+1, T+7, T+15, T+21, T+30, T+45\}$:

$$p^*_{k,l,t} = \min_{o \in \Omega_{k,l,t}} \left( p_{k,l,t,o}^{\text{mandatory}} \right)$$

where $\Omega_{k,l,t}$ is the set of all qualifying commercial fare offers detected for itinerary $k$.

### 2.3 Statistical Invariant: Single Baseline Contribution
- **Axiom:** One itinerary contributes at most **ONE** headline qualifying baseline price.
- **Fare Family Treatment:** Higher fare families (e.g. IndiGo *FlexiPlus*, *IndigoUpFront*, SpiceJet *SpiceFlex*, *SpiceMax*, Akasa *Flexi*) do **NOT** receive additional headline statistical weight merely because they appear on the search page.
- **Analytical Preservation:** All non-selected higher offers are systematically preserved with reason tags (`HIGHER_FARE_FAMILY_OF_ITINERARY`) for downstream ancillary and fare-family dispersion analytics.

---

## 3. Mathematical Compilation Hierarchy

```text
Scraped Raw Observations (Google Flights + EaseMyTrip)
                    ↓
Offer Identification & Product Selection (MIN per Itinerary)
                    ↓
Homogeneous Stratum Formation (Route × DayType × TimeBand × Cabin × LeadClass)
                    ↓
Monthly Representative Geometric Product Price (P̄_i,t)
                    ↓
Longitudinal Product Matching (M_s,t) & Replacement / Quality Adjustment
                    ↓
Short-Chain Jevons Elementary Index (J_s,t via log-formulation)
                    ↓
Recursive Elementary Chaining (I_s,t = I_s,t-1 × J_s,t)
                    ↓
Lead-Time Aggregation (I_r,l,t via w_L = 1/6 Provisional Equal Weights)
                    ↓
Route Aggregation (I_r,t via DGCA Traffic Proxy W_r = 1.0000)
                    ↓
All-India Experimental APIx Index (APIx_t)
                    ↓
CPI Integration Layer (Impact on Headline CPI via HCES 2023-24 Weight)
```

### 3.1 Elementary Index: Short-Chain Jevons Engine
`[MO SPI REQUIREMENT / PRACTICE — CPI 2024 Expert Group]` / `[EUROSTAT METHODOLOGICAL REFERENCE — HICP Manual 2024 §3.4]`

For homogeneous product stratum $s$ in period $t$ with matched product set $M_{s,t}$ ($N = |M_{s,t}|$):

$$\ln J_{s,t} = \frac{1}{N} \sum_{i \in M_{s,t}} \left( \ln p_{i,t} - \ln p_{i,t-1} \right)$$

$$J_{s,t} = \exp\left( \ln J_{s,t} \right)$$

$$I_{s,t} = I_{s,t-1} \times J_{s,t} \quad \text{with } I_{s,0} = 100.0000$$

#### Numerical Equivalence Proof:
The logarithmic formulation is mathematically identical to the direct geometric mean of price relatives:

$$J_{s,t}^{\text{direct}} = \left( \prod_{i \in M_{s,t}} \frac{p_{i,t}}{p_{i,t-1}} \right)^{1/N} = \exp\left( \frac{1}{N} \sum_{i \in M_{s,t}} \ln\left(\frac{p_{i,t}}{p_{i,t-1}}\right) \right) = \exp\left( \frac{1}{N} \sum_{i \in M_{s,t}} (\ln p_{i,t} - \ln p_{i,t-1}) \right)$$

In the APIx engine, both formulas are executed simultaneously. The maximum verified delta on production test data is bounded at $|\Delta| < 1.11 \times 10^{-15}$ (machine epsilon), guaranteeing zero numerical drift.

---

## 4. Advance-Purchase Architecture & Weighting System

`[PROVISIONAL ASSUMPTION]` / `[MO SPI REQUIREMENT / PRACTICE]`

### 4.1 Advance-Purchase Horizons
The index tracks six forward-looking advance purchase classes:

| Horizon | Lead Days | Methodological Role | Benchmark Weight ($w_L$) | Official Status |
| :---: | :---: | :--- | :---: | :--- |
| **$T+1$** | 1 day | Last-minute emergency / business travel; peak volatility | $1/6 \approx 0.166667$ | Analytical Stratum |
| **$T+7$** | 7 days | Short-horizon discretionary booking window | $1/6 \approx 0.166667$ | Analytical Stratum |
| **$T+15$** | 15 days | Standard domestic forward booking window | $1/6 \approx 0.166667$ | Analytical Stratum |
| **$T+21$** | 21 days | **MoSPI Domestic Airfare Reference Checkpoint** | $1/6 \approx 0.166667$ | **Official MoSPI CPI 2024 Checkpoint** |
| **$T+30$** | 30 days | Leisure vacation booking baseline | $1/6 \approx 0.166666$ | Analytical Stratum |
| **$T+45$** | 45 days | Maximum domestic forward planning anchor | $1/6 \approx 0.166666$ | Analytical Stratum |
| **Total** | — | — | **1.000000 (100%)** | Strict Unity Invariant |

> [!IMPORTANT]
> **T+21 Isolation Rule:** As stipulated in the MoSPI CPI 2024 Expert Group documentation, 21 days prior to departure is the domestic airfare collection reference. However, per Phase 29 instructions, $T+21$ receives **no artificial statistical bias** ($w_{T+21} = 1/6$). The weights are formally labeled `PROVISIONAL EQUAL LEAD-TIME WEIGHTS` until empirical airline booking-share transaction data can be integrated.

### 4.2 Lead-Time Aggregation Formula
For route $r$ in period $t$:
$$I_{r,t} = \sum_{l \in L} w_l \cdot I_{r,l,t} \quad \text{where } \sum_{l \in L} w_l = 1.000000$$

---

## 5. Replacement and Quality Adjustment Framework

`[EUROSTAT METHODOLOGICAL REFERENCE — HICP Practical Web Scraping Guidelines 2020 §5.2]`

When a monitored base flight becomes unavailable in period $t$, the system triggers the four-step replacement protocol:

```text
Base Flight Disappears
          ↓
Determine Status: TEMPORARILY_MISSING vs PERMANENTLY_MISSING vs SOLD_OUT
          ↓
Search Candidate Replacements within Identical Stratum
          ↓
Evaluate 14 Quality Characteristics & Compute Comparability Score C ∈ [0, 1]
          ↓
Select Treatment Protocol:
  ├─ C ≥ 0.95 & Net Adj = 0   → DIRECT_COMPARISON
  ├─ 0.70 ≤ C < 0.95          → QUALITY_ADJUSTED_REPLACEMENT (p* = p_cand - ΔQ)
  ├─ Imputation Justified     → IMPUTATION_STRATUM_MEAN
  └─ C < 0.70                 → SPLICED_NON_COMPARABLE (Introduced via Chain Splice)
```

### 5.1 14 Tracked Airfare Quality Characteristics:
1. Origin Airport
2. Destination Airport
3. Airline / Carrier
4. Flight Number
5. Scheduled Departure Time
6. Scheduled Arrival Time
7. Total Duration (Minutes)
8. Number of Stops
9. Cabin Class (Economy)
10. Fare Family
11. Check-in Baggage Allowance (kg)
12. Cabin Baggage Allowance (kg)
13. Refundability Terms
14. Date Changeability Terms

### 5.2 Quality Adjustment Formulation:
If candidate replacement $j$ is superior to missing product $i$ by quality difference $\Delta Q > 0$ (e.g. $+5\text{ kg}$ checked baggage valued at ₹500):

$$p_{j,t}^* = p_{j,t} - \Delta Q$$

$$\text{Price Relative} = \frac{p_{j,t}^*}{p_{i,t-1}}$$

This adjustment guarantees that only **pure inflationary price change** is reflected in the index, preventing service upgrades from being recorded as price inflation.

---

## 6. Route Aggregation vs CPI Integration Layer

`[MO SPI REQUIREMENT / PRACTICE]` / `[PROJECT DESIGN CHOICE]`

To prevent systemic error, APIx maintains a strict separation between market passenger traffic proxies and macroeconomic household expenditure weights:

| Parameter | Identifier | Value | Economic Meaning | Source Document |
| :--- | :---: | :---: | :--- | :--- |
| **Route Weight** | $W_r$ | $1.000000$ | Share of domestic air traffic on route $r$ | DGCA Monthly Domestic Traffic Report |
| **Urban CPI Airfare Weight** | $W_{\text{cpi}}^{\text{urban}}$ | $0.003500$ | Share of urban household budget spent on airfare (~0.35%) | MoSPI HCES 2023-24 / CPI 2024 Basket |
| **Rural CPI Airfare Weight** | $W_{\text{cpi}}^{\text{rural}}$ | $0.000450$ | Share of rural household budget spent on airfare (~0.045%) | MoSPI HCES 2023-24 / CPI 2024 Basket |
| **Combined CPI Airfare Weight** | $W_{\text{cpi}}^{\text{combined}}$ | $0.001850$ | Share of all-India household budget spent on airfare (~0.185%) | MoSPI HCES 2023-24 / CPI 2024 Basket |

$$\text{Headline CPI Impact (percentage points)} = \frac{W_{\text{cpi}}^{\text{combined}}}{100} \times \text{APIx Inflation Rate (\%)} = 0.0000185 \times \Delta \text{APIx}$$

---

## 7. Retained Prototype Median Indicator

`[PROJECT DESIGN CHOICE]`

Per Phase 29 instructions, the earlier unweighted median-based indicator is preserved as an explicit diagnostic indicator:

$$\text{DEL\_BOM\_PROTOTYPE\_MEDIAN\_INDICATOR} = \frac{\sum_{l \in L} w_l \cdot \text{Median}(p_{r,l,t})}{P_{\text{project},\text{reference}}} \times 100$$

- **Current Evaluation Value:** `103.7380` (representative price ₹6,880.60 vs project reference ₹6,632.67).
- **Official Headline Jevons Value:** `102.6407`.
- **Divergence:** $1.0973$ index points ($1.07\%$).
- **Methodological Role:** The median indicator remains accessible in API outputs strictly as a diagnostic benchmark to observe how unstratified price medians diverge from pure matched-basket Jevons inflation.
- **Institutional Boundary Note:** The reference denominator $P_{\text{project},\text{reference}} = ₹6,632.67$ is strictly the `PROVISIONAL_PROJECT_REFERENCE` from the first complete production run (2026-09-26); it is **never** to be confused with the MoSPI calendar-year 2024 price reference.

---

## 8. Multi-Source Diagnostic Architecture

`[PROJECT DESIGN CHOICE]` / `[EUROSTAT METHODOLOGICAL REFERENCE]`

1. **Google Flights Diagnostic Index:** `103.51` (30 observations).
2. **EaseMyTrip Diagnostic Index:** `104.65` (38 observations).
3. **Cross-Source Divergence:** `1.14` index points ($1.14\%$).
4. **Non-Weighting Rule:** Scraper row counts are **never** utilized as weights. Source divergence is audited continuously to monitor aggregator convenience fees and inventory latency.

---

## 9. Formal Claims Classification Matrix

Every methodological rule in the APIx Phase 29 architecture is classified below:

| Methodological Rule | Claim Category | Official Citation / Regulatory Source |
| :--- | :--- | :--- |
| **COICOP 2018 Classification (07.3.3.1)** | `[MO SPI REQUIREMENT / PRACTICE]` | MoSPI CPI 2024 National Metadata Structure; UN COICOP 2018 |
| **21-day domestic advance booking checkpoint ($T+21$)** | `[MO SPI REQUIREMENT / PRACTICE]` | MoSPI CPI 2024 Expert Group Report, Section on Service Prices |
| **Base reference normalization ($2024 = 100$)** | `[MO SPI REQUIREMENT / PRACTICE]` | MoSPI CPI 2024 Press Release and Metadata Structure |
| **Short-chain Jevons formula at elementary level** | `[MO SPI REQUIREMENT / PRACTICE]` | MoSPI CPI 2024 Expert Group Report, Elementary Aggregates |
| **Young / Modified Laspeyres weighted aggregation** | `[MO SPI REQUIREMENT / PRACTICE]` | MoSPI CPI 2024 Manual on Higher-Level Index Aggregation |
| **Online airfare price collection methodology** | `[MO SPI REQUIREMENT / PRACTICE]` | MoSPI Alternative Data Sources & E-Commerce Web Scraping Framework |
| **Product-offer level observation tracking** | `[EUROSTAT METHODOLOGICAL REFERENCE]` | Eurostat Practical guidelines on web scraping for the HICP (2020 §3.2) |
| **Short-chain recursive linking ($I_t = I_{t-1} \times J_t$)** | `[EUROSTAT METHODOLOGICAL REFERENCE]` | Eurostat HICP Methodological Manual (2024 Chapter 3) |
| **Four-treatment replacement hierarchy** | `[EUROSTAT METHODOLOGICAL REFERENCE]` | Eurostat HICP Methodological Manual (2024 Chapter 7) |
| **14 airfare quality characteristics retention** | `[EUROSTAT METHODOLOGICAL REFERENCE]` | Eurostat HICP Methodological Manual (2024 Chapter 12: Passenger Air Transport) |
| **Strict non-zero axiom for missing/sold-out fares** | `[EUROSTAT METHODOLOGICAL REFERENCE]` | Eurostat HICP Practical Guidelines (2020 §4.1) |
| **Frozen Headline Product Definition (MIN offer per itin)** | `[PROJECT DESIGN CHOICE]` | APIx Product Definition v2.0 (Phase 29 Design Specification) |
| **Provisional equal lead-time weights ($w_L = 1/6$)** | `[PROVISIONAL ASSUMPTION]` | Adopted pending empirical domestic booking distribution release |
| **DGCA passenger traffic shares as route proxy** | `[PROVISIONAL ASSUMPTION]` | DGCA Monthly Domestic Air Transport Traffic Reports |
| **Hedonic valuation benchmarks for baggage / time slots** | `[UNRESOLVED METHODOLOGICAL QUESTION]` | Subject to econometric hedonic regression modeling across all 60 city pairs |
| **Cross-aggregator convenience fee harmonization** | `[UNRESOLVED METHODOLOGICAL QUESTION]` | Dependent on payment-gateway fee disclosures across OTAs |

---

## 10. Audit Trail Summary

| Field | Production Audit Value |
| :--- | :--- |
| **Collection Run ID (Base)** | `825fa969-5811-49c8-9854-40637fd438a2` |
| **Collection Run ID (Eval)** | `925fa969-5811-49c8-9854-40637fd438b3` |
| **Methodology Version** | `APIx v2.0 (MoSPI CPI 2024 + Eurostat HICP Aligned)` |
| **Product Definition Version** | `APIx_PRODUCT_DEF_v2.0_FROZEN` |
| **Weight Version** | `2026.09` (`PROVISIONAL EQUAL LEAD-TIME WEIGHTS`) |
| **Quality Adjustment Version** | `EUROSTAT_HICP_2024_QA_v1.0` |
| **Timestamp UTC** | `2026-09-27T14:41:09Z` |
| **Primary Route Tested** | `DEL-BOM` |
| **Total Automated Tests Passing** | `14/14` (Phase 29 Suite) | `49/50` (Full Repository Core Suite) |
