# Official Methodology: Indian Airfare Price Index (APIx)
## CPI 2024-Compatible Statistical Index Compilation Framework

> **Document Status:** Official Production Specification  
> **Methodology Version:** `APIx v1.0`  
> **Weight Version:** `2026.09`  
> **Indian Benchmark:** MoSPI / NSO Consumer Price Index (CPI 2024 Base: $2024 = 100$)  
> **International Benchmark:** Eurostat HICP Airfare Standards & Web Scraping Practical Guidelines (2024)  
> **Classification Standard:** UN COICOP 2018, Subclass 07.3.3.1 (Passenger Air Transport)  

---

## 1. Executive Summary & Institutional Alignment

The **Indian Airfare Price Index (APIx)** is an experimental, analytical price index designed to measure temporal changes in consumer-facing passenger airfares across India's domestic aviation network. 

Traditional unweighted arithmetic averages of scraped ticket prices fail basic statistical tests: they are susceptible to phantom inflation from flight availability churn, scraper result truncation, and extreme last-minute outlier fares. In accordance with MoSPI CPI 2024 and Eurostat HICP standards, APIx enforces a strict micro-founded calculation hierarchy:

```text
Scraped Raw Observations (DOM / API)
                ↓
Legal, Source, & Currency Validation (INR only)
                ↓
Price Normalization & Deduplication (Itinerary & Offer Fingerprints)
                ↓
Homogeneous Product Stratification (SHA-256 Composite Strata)
                ↓
Monthly Geometric Product Pricing (P̄_(i,t) = exp(1/D ∑ ln P))
                ↓
Adjacent-Period Product Matching Engine (M_(s,t), C ≥ 0.50)
                ↓
Short-Chain Jevons Elementary Index (J_(s,t) = exp(1/N ∑ Δ ln P))
                ↓
Recursive Chaining (I_(s,t) = I_(s,t-1) × J_(s,t))
                ↓
Lead-Time Aggregation (I_(r,l,t) via Booking Weights W_l)
                ↓
Route Aggregation (I_(r,t) via DGCA Passenger Weights W_r)
                ↓
All-India Airfare Price Index (APIx_t = ∑ W_r I_(r,t))
```

---

## 2. Temporal & Lead-Time Architecture

Air travel pricing is characterized by dynamic yield management: ticket prices escalate as the departure date approaches. APIx monitors six advance-purchase horizons:

| Horizon | Days to Departure | Analytical Role | Benchmark Weight ($W_l$) |
| :---: | :---: | :--- | :---: |
| **$T+1$** | 1 day | Last-minute business & emergency travel; peak price volatility | 0.1500 (15%) |
| **$T+7$** | 7 days | Short-horizon discretionary booking window | 0.3000 (30%) |
| **$T+15$** | 15 days | Standard domestic advance booking window | 0.2000 (20%) |
| **$T+21$** | 21 days | **MoSPI CPI 2024 Official Alignment Checkpoint** | 0.1500 (15%) |
| **$T+30$** | 30 days | Early booking vacation/leisure baseline | 0.1200 (12%) |
| **$T+45$** | 45 days | Maximum domestic forward planning anchor | 0.0800 (8%) |
| **Total** | — | — | **1.0000 (100%)** |

> [!IMPORTANT]
> **$T+21$ MoSPI Alignment Rule:** The MoSPI CPI 2024 Expert Group specifically designated **21 days prior to departure** as the standard advance-purchase specification for domestic air travel. In APIx, $T+21$ is scheduled, captured, normalized, and aggregated as an **independent, isolated stratum**, preventing artificial blending with $T+15$ or $T+30$.

---

## 3. Product Stratification & Deterministic Fingerprints

To satisfy the axiom of comparing "like with like", observations are stratified into homogeneous product groups.

### 3.1 Composite Stratum Definition
A stratum $s$ represents an invariant quality bundle:
$$\text{stratum\_id} = \text{SHA256}(\text{Origin} \mid \text{Dest} \mid \text{DayType} \mid \text{TimeBand} \mid \text{Cabin} \mid \text{FareFamily} \mid \text{Baggage} \mid \text{Stops} \mid \text{PaxType} \mid \text{LeadClass})$$

- **Travel Day Type:** `WEEKDAY` (Monday–Thursday) vs `WEEKEND` (Friday–Sunday).
- **Departure Time Bands:**
  - `EARLY_MORNING`: 00:00 – 05:59
  - `MORNING`: 06:00 – 11:59
  - `AFTERNOON`: 12:00 – 17:59
  - `EVENING`: 18:00 – 23:59
- **Stop Category:** `NONSTOP` (0 stops), `ONE_STOP` (1 stop), `MULTI_STOP` (2+ stops).

### 3.2 Fingerprinting & Cross-Period Identity
- **Itinerary Fingerprint ($F_{\text{itinerary}}$):**
  $$F_{\text{itinerary}} = \text{SHA256}(\text{Origin} \mid \text{Dest} \mid \text{TravelDate} \mid \text{Airline} \mid \text{FlightNum} \mid \text{DepTime} \mid \text{ArrTime} \mid \text{Stops})$$
- **Offer Fingerprint ($F_{\text{offer}}$):**
  $$F_{\text{offer}} = \text{SHA256}(F_{\text{itinerary}} \mid \text{FareFamily} \mid \text{Cabin} \mid \text{Baggage} \mid \text{Refundability} \mid \text{Changeability})$$
- **Cross-Period Matching Key ($K_{\text{prod}}$):**
  $$K_{\text{prod}} = \text{stratum\_id} : \text{airline} : \text{flight\_number}$$

---

## 4. Mathematical Formulation

### 4.1 Monthly Geometric Product Price
Within calendar month $t$, let $D_{i,t}$ be the valid daily observations for product $i$. The monthly representative product price $\bar{P}_{i,t}$ is evaluated using a numerically stable logarithmic formulation:
$$\bar{P}_{i,t} = \exp\left(\frac{1}{|D_{i,t}|} \sum_{\tau \in D_{i,t}} \ln P_{i,\tau}\right)$$

### 4.2 Matched Product Set & Coverage Gating
For stratum $s$, let $M_{s,t}$ be the set of products present in both periods $t-1$ and $t$:
$$M_{s,t} = \{i \in s \mid \bar{P}_{i,t-1} > 0 \land \bar{P}_{i,t} > 0\}$$
Let $N_{s,t-1}$ be the total eligible products in period $t-1$. The coverage ratio is:
$$C_{s,t} = \frac{|M_{s,t}|}{N_{s,t-1}}$$
A stratum index is published if and only if:
$$|M_{s,t}| \ge 1 \quad \text{and} \quad C_{s,t} \ge 0.50 \quad (50\% \text{ coverage})$$

### 4.3 Short-Chain Jevons Elementary Index
The elementary price relative for stratum $s$ is the geometric mean of price relatives:
$$J_{s,t} = \exp\left( \frac{1}{|M_{s,t}|} \sum_{i \in M_{s,t}} \left[\ln \bar{P}_{i,t} - \ln \bar{P}_{i,t-1}\right] \right)$$

Elementary indices are chained recursively from the reference period ($I_{s,0} = 100.00$):
$$I_{s,t} = I_{s,t-1} \times J_{s,t}$$

### 4.4 Higher-Level Weighted Aggregation
1. **Lead-Time Sub-Index ($I_{r,l,t}$):**
   $$I_{r,l,t} = \frac{1}{|S_{r,l}|} \sum_{s \in S_{r,l}} I_{s,t}$$
2. **Route Index ($I_{r,t}$):**
   $$I_{r,t} = \sum_{l \in L} W_l \cdot I_{r,l,t} \quad \text{where} \quad \sum_l W_l = 1.0000$$
3. **All-India APIx ($APIx_t$):**
   $$APIx_t = \sum_{r \in R} W_r \cdot I_{r,t} \quad \text{where} \quad \sum_r W_r = 1.0000$$

### 4.5 Inflation Metrics
$$\text{MoM Inflation (\%)} = \left(\frac{APIx_t}{APIx_{t-1}} - 1\right) \times 100$$
$$\text{YoY Inflation (\%)} = \left(\frac{APIx_t}{APIx_{t-12}} - 1\right) \times 100$$

---

## 5. Non-Negotiable Methodological Rules

1. **Never average raw scraped ticket prices directly:** Compositional shifts in scraper output create false volatility.
2. **Never weight by scraper record counts:** Web crawling artifacts cannot proxy economic consumption.
3. **Never treat sold-out or missing flights as ₹0:** Missing products are handled via matched longitudinal chains.
4. **Never manufacture artificial base-fare vs tax splits:** Use total consumer-payable fare when OTA splits are missing.
5. **Never use flight number alone as product identity:** Product identity requires the complete multidimensional stratum bundle.
6. **Never discard genuine market price surges:** Extreme surges during festival/peak demand are real price signals.
7. **Always preserve raw payload artifacts:** Full DOM captures and raw JSON payloads must be archived for auditability.
8. **Always use high-precision Decimal arithmetic:** Zero float rounding error in monetary calculations.

---

## 6. Antigravity Acceptance Criteria Compliance

| Gate | Acceptance Rule | Test Requirement | Verification Result |
| :---: | :--- | :--- | :---: |
| **Gate 1** | **Price Invariance** | Unchanged prices $\implies J_{s,t} = 1.0000$ | **PASSED** |
| **Gate 2** | **Scale Invariance** | All prices $+10\% \implies J_{s,t} = 1.1000$ | **PASSED** |
| **Gate 3** | **Recursive Chain Consistency** | $I_{s,t} = I_{s,t-1} \times J_{s,t}$ exactly | **PASSED** |
| **Gate 4** | **Weight Sum Unity** | $\sum W_r = 1.0000$ and $\sum W_l = 1.0000$ | **PASSED** |
| **Gate 5** | **Duplicate Invariance** | Scraped duplicates yield 0 change in index | **PASSED** |
| **Gate 6** | **MoSPI T+21 Isolation** | T+21 isolated as official checkpoint | **PASSED** |
| **Gate 7** | **Zero-Price Handling** | Zero/negative fares rejected by validation | **PASSED** |
| **Gate 8** | **Audit Trail Metadata** | Version and timestamps logged in every publication | **PASSED** |

---

## 7. Summary of Empirical Validation

- **30-Day Historical Backtest:** Confirmed that the matched short-chain Jevons index dampens scraper churn volatility by eliminating spurious compositional spikes, achieving an **MAE of 1.3302** and **RMSE of 2.3875** against underlying market drift ([`BACKTEST_REPORT.md`](file:///c:/sih%202026/apix/BACKTEST_REPORT.md)).
- **Sensitivity Analysis across 4 Regimes:** Confirmed robust invariance to weighting specifications, with a maximum divergence across all 4 regimes bounded at **0.2625 index points (0.255%)** ([`SENSITIVITY_REPORT.md`](file:///c:/sih%202026/apix/SENSITIVITY_REPORT.md)).
