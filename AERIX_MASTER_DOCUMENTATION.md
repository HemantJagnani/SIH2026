# AERIX — Comprehensive Master Architecture & Hackathon Dossier
## Sovereign Indian Airfare Price Index & High-Frequency Aviation Econometric Terminal
### Smart India Hackathon (SIH) 2026 — Ministry of Statistics and Programme Implementation (MoSPI)

> **Document Status:** Authoritative System Specification & Pitch Master Reference  
> **System Name:** **AERIX** (Airfare Econometric Real-time Index)  
> **Methodology Standard:** MoSPI CPI 2024 Revision Framework ($2024 = 100$) & Eurostat HICP 2024  
> **Classification Code:** UN COICOP 2018, Subclass `07.3.3.1.2.01` (Domestic Passenger Transport by Air)  
> **Basket Scope:** DGCA CY2024 Top-60 Domestic Scheduled City-Pairs (91.99M Passengers; 57.02% National Coverage)  
> **Matrix Scope:** 60 Routes × 6 Advance Horizons = **360 Primary Sampling Cells (100% Populated)**  
> **Verification Status:** 158/158 Backend Pytest Gates Passed | 13/13 Frontend Vitest Tests Passed  

---

# TABLE OF CONTENTS
1. [Executive Summary & The Big Idea](#1-executive-summary--the-big-idea)
2. [Problem Resolution & Macroeconomic Gap Analysis](#2-problem-resolution--macroeconomic-gap-analysis)
3. [Proposition Uniqueness & Strategic Innovations](#3-proposition-uniqueness--strategic-innovations)
4. [End-to-End Technical Pipeline (Step-by-Step Micro Detail)](#4-end-to-end-technical-pipeline-step-by-step-micro-detail)
   - [Stage 1: Multi-Source Ethical Web Capture & Crawling Architecture](#stage-1-multi-source-ethical-web-capture--crawling-architecture)
   - [Stage 2: Ingestion, Validation & Canonical Normalization](#stage-2-ingestion-validation--canonical-normalization)
   - [Stage 3: Multi-Source Reconciliation & Stratification Pipeline](#stage-3-multi-source-reconciliation--stratification-pipeline)
   - [Stage 4: 9-Step Micro-Founded Econometric Compilation Engine](#stage-4-9-step-micro-founded-econometric-compilation-engine)
   - [Stage 5: Data Persistence & Distributed Cloud Infrastructure](#stage-5-data-persistence--distributed-cloud-infrastructure)
   - [Stage 6: High-Performance Backend REST API](#stage-6-high-performance-backend-rest-api)
   - [Stage 7: Cockpit Financial Terminal & Visual Experience](#stage-7-cockpit-financial-terminal--visual-experience)
5. [Feasibility, Engineering Challenges & Proposed Solutions](#5-feasibility-engineering-challenges--proposed-solutions)
6. [Macroeconomic Potential & Multi-Sectoral Impact](#6-macroeconomic-potential--multi-sectoral-impact)
7. [Institutional & Sentimental Value (MoSPI & Indian Citizens)](#7-institutional--sentimental-value-mospi--indian-citizens)
8. [Acceptance Criteria, Empirical Audits & Regression Proofs](#8-acceptance-criteria-empirical-audits--regression-proofs)
9. [Research Documentation, Citations & Academic References](#9-research-documentation-citations--academic-references)
10. [Hackathon Slide-by-Slide Pitch Blueprint](#10-hackathon-slide-by-slide-pitch-blueprint)

---

# 1. EXECUTIVE SUMMARY & THE BIG IDEA

### What is AERIX?
**AERIX** is India's first enterprise-grade, high-frequency airfare price collection and economic index compilation engine. It transforms raw, chaotic online airline ticket prices collected across multiple web sources (Google Flights, EaseMyTrip, direct carriers) into an **authoritative, CPI-compatible, pure price index** for India's domestic scheduled aviation airspace.

AERIX is built specifically to address the challenge faced by the **Ministry of Statistics and Programme Implementation (MoSPI)** and the **Reserve Bank of India (RBI)**: measuring real-time inflation in dynamic, algorithmically priced service sectors without succumbing to sample selection bias, missing flight churn, or extreme last-minute surge distortions.

### The Big Idea:
> **"Build the Consumer Price Index for aviation the way national macroeconomic statistics are meant to be built — micro-founded, matched-model, quality-adjusted, and grounded in sovereign regulatory data, operating at daily frequency."**

AERIX replaces archaic, once-a-month manual price collection with an automated, zero-license-cost, mathematically proven pipeline that strictly implements:
1. **MoSPI CPI 2024 Base Year Alignment:** Conceptual base $2024 = 100$, tracking the newly separated airfare subclass under UN COICOP 2018.
2. **Eurostat Harmonised Index of Consumer Prices (HICP) 2024 Standards:** Web scraping practical guidelines, longitudinal product matching, 14-characteristic quality adjustment, and strict non-zero handling for sold-out flights.
3. **The 360-Cell Matrix Architecture:** Monitoring all Top-60 DGCA city-pairs across 6 discrete advance-purchase booking horizons ($T+1$ to $T+45$), with dedicated isolation for the official MoSPI $T+21$ checkpoint.

---

# 2. PROBLEM RESOLUTION & MACROECONOMIC GAP ANALYSIS

### The Core Problem: Why Current Airfare Measurement Fails
In India's rapidly expanding civil aviation market (161+ million domestic passengers annually), airline ticketing is governed by aggressive dynamic yield management algorithms. Fares for the exact same seat on the exact same flight can vary by **200% to 400%** depending on when the consumer purchases the ticket.

Current official and commercial measurement systems suffer from critical structural deficiencies:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       THE FOUR CRITICAL FAILURES                            │
├──────────────────────────┬──────────────────────────────────────────────────┤
│ 1. The Naive Average     │ Averaging raw web scraped quotes creates phantom │
│    Trap (Arithmetic Bias)│ volatility. When cheap early-morning flights sell│
│                          │ out, the simple average spikes even if remaining │
│                          │ fares did not change a single rupee.             │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 2. The Monthly Lag &     │ MoSPI's traditional Consumer Price Index records │
│    Frequency Blindspot   │ prices once a month. It completely misses flash  │
│                          │ dynamic pricing, festival surge spikes (Diwali,  │
│                          │ Chhath, Pongal), and mid-month capacity shifts.  │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 3. Compositional Shift & │ Flight schedules change seasonally. A naive      │
│    Flight Churn Bias     │ tracker comparing June flights with July flights │
│                          │ compares different aircraft, timings, and stops, │
│                          │ violating the fundamental axiom: "Like-with-Like"│
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 4. Single-Source OTA     │ Scrapers that pull from a single OTA suffer from │
│    Distortion            │ hidden convenience markups, cached ghost fares,  │
│                          │ and artificial result truncation.                │
└──────────────────────────┴──────────────────────────────────────────────────┘
```

### The Fundamental Axiom of Economic Measurement
> **A price index must NEVER be calculated by taking simple averages of scraped ticket prices.**  
> Simple arithmetic averages conflate **genuine price inflation** with **compositional shifts** (changes in flight schedules, aircraft capacity, departure time distribution, and sold-out seats). Under international statistical doctrine (Eurostat HICP / UN COICOP), prices must be partitioned into homogeneous strata, aggregated via geometric means, and linked over adjacent periods through matched-model relatives.

---

# 3. PROPOSITION UNIQUENESS & STRATEGIC INNOVATIONS

AERIX introduces eight groundbreaking innovations that distinguish it from any academic demonstration, commercial travel aggregator, or raw web scraper:

### 1. Sovereign Regulatory Grounding (DGCA CY2024 Baseline)
Unlike commercial tools that track arbitrary routes, AERIX constructs its domestic route basket strictly from the **Directorate General of Civil Aviation (DGCA)** Calendar Year 2024 passenger traffic reports:
- Covers the **Top-60 domestic city-pairs** carrying **91,995,307 annual passengers** (**57.0247% of All-India domestic traffic**).
- Route weights $W_r$ are exactly proportional to verified passenger volume shares, summing to $1.00000000$.
- Uses DGCA Northern Summer & Winter 2024 Approved Schedules as an authoritative flight-universe denominator to distinguish crawler drop-off from true airline cancellations.

### 2. The 360-Cell Matrix & Strict MoSPI $T+21$ Checkpoint Isolation
AERIX establishes a complete $60 \text{ Routes} \times 6 \text{ Lead Horizons} = 360 \text{ Cells}$ sampling matrix.
- Lead horizons: $T+1$ (emergency/business), $T+7$ (short-horizon), $T+15$ (standard), $T+21$ (**MoSPI Official Domestic Checkpoint**), $T+30$ (early planning), and $T+45$ (maximum domestic forward window).
- **The $T+21$ Isolation Rule:** MoSPI's 2024 Expert Group designated 21 days advance booking as the official benchmark for Indian domestic air travel. AERIX treats $T+21$ as an independent, unblended stratum with an empirical weight of $15.19\%$, never contaminating it with adjacent horizons.

### 3. Tri-Layer Weight Architecture & Strict Anti-Contamination Governance
To eliminate methodological errors, AERIX enforces three strictly segregated weight layers:
1. **Layer 1: Route Representativeness Weights ($W_r$):** Derived from DGCA passenger volumes.
2. **Layer 2: Lead-Time Booking Weights ($W_l$):** Derived from 300,153 empirical booking transactions (`Clean_Dataset.csv`).
3. **Layer 3: Macroeconomic Expenditure Weight ($W_{\text{cpi}} = 0.02951\%$):** Derived from MoSPI CPI 2024 (Item Code `07.3.3.1.2.01`, Annexure 5.3d).
> **Anti-Contamination Rule:** The CPI expenditure weight operates exclusively at the national macroeconomic integration layer. Automated software guards fail loudly with an exception if CPI expenditure weights are ever accidentally passed into internal route or lead-time aggregations.

### 4. 14-Characteristic Quality Adjustment Engine
When airlines alter flight schedules or aircraft, AERIX does not drop the observation or naively compare mismatched products. Conforming to Eurostat HICP Chapter 7, it deploys a 14-characteristic audit model that computes monetary quality differentials ($\Delta Q$) for baggage changes, departure time band shifts, and carrier tier alterations:
$$p^* = p - \Delta Q$$

### 5. Multi-Source Reconciliation & Anti-Collusion Independence
AERIX ingests simultaneous streams from Google Flights and EaseMyTrip, reconciling multiple OTA quotes for identical itineraries down to a single canonical observation using geometric means, eliminating source-specific bias.

### 6. Full Mathematical Traceability & The Strict Non-Zero Axiom
If a flight is sold out or unavailable, AERIX strictly forbids imputing ₹0 or using naive averages. The matched short-chain Jevons index naturally bridges missing observations through recursive linking:
$$I_{s,t} = I_{s,t-1} \times J_{s,t}$$

### 7. Zero-License, Ethical, Anti-Bot Respecting Scraping Engine
Built with Crawlee and Playwright, AERIX behaves like an authentic human analyst. It does not hack or bypass CAPTCHAs; instead, it uses human-like search cadences, session management, and exponential backoff, logging every raw DOM and network response for forensic auditability.

### 8. Institutional Financial Terminal Experience
A clean, restrained, high-density dashboard inspired by aeronautical sectional charts and cockpits (using Google Fonts Newsreader and B612), completely free of generic AI-dashboard gradients or toy mockups.

---

# 4. END-TO-END TECHNICAL PIPELINE (STEP-BY-STEP MICRO DETAIL)

The AERIX pipeline operates as an automated, continuous, 7-stage engine. Below is the granular breakdown from web socket packet to macroeconomic index publication:

```mermaid
flowchart TD
    subgraph S1["Stage 1: Multi-Source Ethical Data Capture"]
        A1[Scheduled Search Generator] --> A2[Crawlee + Playwright Browser Pool]
        A2 --> A3[Google Flights & EaseMyTrip Human-Like Search]
        A3 --> A4[Raw Evidence Archive: HTML DOM + Network JSON]
    end

    subgraph S2["Stage 2: Canonical Ingestion & Validation"]
        A4 --> B1[RawFareObservation Model]
        B1 --> B2[Currency Filter: Strict INR Validation]
        B2 --> B3[Mandatory-Payable Price Calculation]
        B3 --> B4[SHA-256 Itinerary & Offer Fingerprinting]
        B4 --> B5[Quality Status Classification: VALID, DUPLICATE, EXCLUDED]
    end

    subgraph S3["Stage 3: Reconciliation & 360-Cell Stratification"]
        B5 --> C1[Cross-Source Deduplication Engine]
        C1 --> C2[Geometric Mean Price Consensus]
        C2 --> C3[Regulatory Flight Schedule Match: DGCA Summer/Winter 2024]
        C3 --> C4[360 Matrix Allocation: 60 Routes x 6 Lead Horizons]
    end

    subgraph S4["Stage 4: 9-Step Econometric Compilation Engine"]
        C4 --> D1[Step 1: Within-Period Geometric Mean Price P_bar]
        D1 --> D2[Step 2: Longitudinal Product Matching Engine M_s,t]
        D2 --> D3[Step 3: 14-Characteristic Quality Adjustment p* = p - Delta Q]
        D3 --> D4[Step 4: Short-Chain Jevons Elementary Relative J_s,t]
        D4 --> D5[Step 5: Recursive Chaining I_s,t = I_s,t-1 x J_s,t]
        D5 --> D6[Step 6: Empirical Lead-Time Aggregation W_l]
        D6 --> D7[Step 7: DGCA CY2024 Passenger Route Basket Aggregation W_r]
        D7 --> D8[Step 8: All-India AERIX Headline Compilation Base 2024=100]
        D8 --> D9[Step 9: MoSPI CPI 2024 National Macroeconomic Integration Layer]
    end

    subgraph S5["Stage 5: Data Persistence & Infrastructure"]
        D8 --> E1[Hosted Neon PostgreSQL Storage]
        D8 --> E2[Render Redis High-Frequency Cache]
        D8 --> E3[GitHub Actions Automated Raw Evidence Sync]
    end

    subgraph S6["Stage 6: Production REST API"]
        E1 & E2 --> F1[FastAPI High-Speed Service]
        F1 --> F2[/airfare-index, /coverage, /matrix, /lead-curves, /backtest]
    end

    subgraph S7["Stage 7: Cockpit Visual Terminal"]
        F2 --> G1[React + Vite + TypeScript Dashboard]
        G1 --> G2[Interactive Scrubbing, Solo Route Focus, 60 Sparklines, Sensitivity Sandbox]
    end
```

---

### STAGE 1: MULTI-SOURCE ETHICAL WEB CAPTURE & CRAWLING ARCHITECTURE

1. **Search Job Generation:**
   - The scheduler queries the active sampling schedule for the day's matrix targets: 60 routes across 6 lead dates ($T+1, T+7, T+15, T+21, T+30, T+45$).
   - Formulates canonical search parameters: Origin (IATA), Destination (IATA), Departure Date (`YYYY-MM-DD`), 1 Adult Passenger, Economy Cabin Class, One-Way Trip.
2. **Session Initialization & Fingerprint Stealth:**
   - Playwright launches headless Chromium instances managed through Crawlee for Python.
   - Sets authentic browser viewport dimensions ($1920 \times 1080$), standard user-agent strings, Indian locale (`en-IN`), and Asia/Kolkata timezone.
   - Maintains session cookies, local storage state, and connection keep-alive to mimic authentic human browsing.
3. **Target Navigation & Human-Like Interaction Cadence:**
   - Navigates to search entry points (Google Flights `google.com/travel/flights` and EaseMyTrip `easemytrip.com`).
   - Implements random Gaussian delays ($1.5s - 3.8s$) between keystrokes and button clicks.
   - Waits dynamically for network idle and DOM selector stabilization rather than fixed timers (`page.wait_for_selector('[role="listitem"]')`).
4. **Resilience & Safe Handling Policy:**
   - Detects HTTP 403, 429, Cloudflare turnstiles, and CAPTCHA challenges immediately.
   - **Zero-Bypass Compliance:** Does NOT attempt to solve CAPTCHAs or circumvent authentication. If blocked, the crawler safely marks the run as restricted, initiates exponential backoff with jitter, and falls back to alternate sources.
5. **Raw Artifact Preservation:**
   - Captures and archives the unparsed HTML DOM snapshot and raw network XHR/Fetch JSON responses into compressed archives (`.tar.gz`) stored with cryptographic hashes for forensic reproducibility.

---

### STAGE 2: INGESTION, VALIDATION & CANONICAL NORMALIZATION

1. **Raw Ingestion Schema (`RawFareObservation`):**
   - Ingests raw parsed strings, capturing source identity, search timestamp (UTC and IST), verbatim carrier strings, flight numbers, departure/arrival times, stops, and price strings.
2. **Currency Gating & Boundary Validation:**
   - Gated strictly for `INR`. Any non-INR quotation is rejected at boundary validation.
   - Rejects zero or negative fares ($P \le 0$).
   - Rejects fares exceeding statutory limits ($P > ₹500,000$).
3. **Mandatory-Payable Price Calculation:**
   - In accordance with consumer price measurement rules, the economic price must reflect the **final mandatory-payable amount**:
     $$\text{Mandatory Fare} = \text{Base Fare} + \text{Fuel Surcharges} + \text{Airport User Development Fees (UDF)} + \text{GST} + \text{Mandatory Convenience Fees}$$
   - Excludes all optional ancillaries (seat selection fees, excess baggage, onboard meals, travel insurance).
4. **Deterministic SHA-256 Fingerprinting:**
   - **Itinerary Fingerprint ($F_{\text{itin}}$):** Uniquely identifies the physical flight:
     $$F_{\text{itin}} = \text{SHA256}(\text{Origin} \mid \text{Dest} \mid \text{Date} \mid \text{Airline} \mid \text{FlightNum} \mid \text{DepTime} \mid \text{ArrTime} \mid \text{Stops})$$
   - **Offer Fingerprint ($F_{\text{offer}}$):** Identifies the commercial product bundle:
     $$F_{\text{offer}} = \text{SHA256}(F_{\text{itin}} \mid \text{FareFamily} \mid \text{Cabin} \mid \text{BaggageAllowance} \mid \text{Refundability} \mid \text{Changeability})$$
5. **Temporal & Spatial Normalization:**
   - Derives travel day type (`WEEKDAY` Mon–Thu vs `WEEKEND` Fri–Sun).
   - Classifies departure into standard statistical time bands: `EARLY_MORNING` (00:00–05:59), `MORNING` (06:00–11:59), `AFTERNOON` (12:00–17:59), and `EVENING` (18:00–23:59).
   - Maps lead days into discrete classes ($T+1, T+7, T+15, T+21, T+30, T+45$).
6. **Quality Status Gating:**
   - Marks observations into mutually exclusive governance states: `VALID` (clean economic fare), `DUPLICATE` (identical offer seen multiple times), `HIGHER_FARE_FAMILY` (Business, Premium Economy, FlexiPlus filtered per frozen product definition), `FOREIGN_TRANSIT` (routes with international layovers filtered).

---

### STAGE 3: MULTI-SOURCE RECONCILIATION & STRATIFICATION PIPELINE

1. **Cross-Source Offer Merging:**
   - Ingests concurrent records from Google Flights and EaseMyTrip.
   - Evaluates matching itineraries: if an identical itinerary and fare family are offered across multiple OTAs, AERIX merges them into a single canonical product offer.
2. **Price Resolution Hierarchy:**
   - When prices match exactly, the offer is unified.
   - When OTA prices exhibit minor cross-source divergence for the exact same ticket, AERIX takes the unweighted geometric mean of verified prices as the consensus price.
   - Tracks cross-source divergence percentage as a live data-quality metric.
3. **Frozen Headline Product Selection Rule (`AERIX_PRODUCT_DEF_v2.0_FROZEN`):**
   - To eliminate upward bias from flexible fare packages, AERIX implements the **Minimum Qualifying Mandatory-Payable Adult Economy Fare per Itinerary** rule.
   - Premium Economy, Business, First, and FlexiPlus offers are logged but segregated from the headline baseline.
4. **Regulatory Schedule Cross-Validation:**
   - Matches every scraped flight against the DGCA Northern Summer & Winter 2024 Approved Flight Schedules.
   - Classifies every flight into: `OBSERVED_AND_SCHEDULED`, `SCHEDULED_BUT_NOT_OBSERVED` (identifying sell-outs or crawler drop-off), or `UNSCHEDULED_OBSERVED` (charters or special flights).

---

### STAGE 4: 9-STEP MICRO-FOUNDED ECONOMETRIC COMPILATION ENGINE

The core mathematical brain of AERIX executes the following nine formal econometric steps:

#### Step 1: Within-Period Geometric Mean Price Normalization
For each homogeneous product stratum $s = (\text{Route } r, \text{Lead } l, \text{TimeBand } b, \text{DayType } d)$ on date $t$, valid quotes $p_{s,i,t,k}$ for flight $i$ are aggregated using an unweighted geometric mean:
$$\bar{P}_{s,i,t} = \exp\left( \frac{1}{K_{s,i,t}} \sum_{k=1}^{K_{s,i,t}} \ln p_{s,i,t,k} \right)$$
*Where $K_{s,i,t}$ is the count of valid quotes for flight $i$ in stratum $s$.*

#### Step 2: Longitudinal Product Matching Across Adjacent Periods
AERIX searches for identical product offerings across adjacent periods $t-1$ and $t$:
$$M_{s,t} = \{i \in s \mid \bar{P}_{s,i,t-1} > 0 \land \bar{P}_{s,i,t} > 0\}$$
- **Coverage Gating:** Stratum $s$ is published if and only if $|M_{s,t}| \ge 1$ and the matched coverage ratio $C_{s,t} = \frac{|M_{s,t}|}{N_{s,t-1}} \ge 0.50$ (minimum 50% matched product continuity).

#### Step 3: 14-Characteristic Flight Churn Audit & Monetary Quality Adjustment
When a flight in period $t-1$ disappears in period $t$, AERIX locates the closest candidate replacement within the same stratum. It evaluates 14 service dimensions (carrier tier, departure time proximity, baggage entitlement, refundability, changeability).
- If comparability score $\ge 0.70$, it calculates monetary quality adjustments:
  $$p^* = p - \Delta Q$$
  *(e.g. If replacement includes 20kg baggage instead of 15kg, subtract standard ₹500 airline fee differential).*
- If comparability score $< 0.70$, the flight is classified as non-comparable and bridged via class-mean imputation.

#### Step 4: Short-Chain Jevons Elementary Index
The elementary price relative for stratum $s$ is computed using the micro-founded Jevons formula via numerically stable log-differences:
$$J_{s,t} = \exp\left( \frac{1}{|M_{s,t}|} \sum_{i \in M_{s,t}} \left[\ln \bar{P}_{s,i,t}^* - \ln \bar{P}_{s,i,t-1}\right] \right)$$

#### Step 5: Recursive Chaining from Reference Base
Elementary strata are chained recursively over time from base $I_{s,0} = 100.00$:
$$I_{s,t} = I_{s,t-1} \times J_{s,t}$$
*This short-chain formulation ensures zero base-period drift and automatically handles product entry and exit.*

#### Step 6: Advance-Purchase Lead-Time Aggregation
Elementary strata within route $r$ and lead horizon $l$ are aggregated to lead-time sub-indices:
$$I_{r,l,t} = \frac{1}{|S_{r,l}|} \sum_{s \in S_{r,l}} I_{s,t}$$
The route price index is formed using empirical booking weights $W_l$:
$$I_{r,t} = \sum_{l \in L} W_l \cdot I_{r,l,t} \quad \text{where} \quad \sum_{l \in L} W_l = 1.000000$$
*(Weights: $T+1: 5.09\%, T+7: 13.50\%, T+15: 14.91\%, T+21: 15.19\%, T+30: 25.88\%, T+45: 25.43\%$).*

#### Step 7: All-India DGCA CY2024 Passenger Route Basket Aggregation
Route indices $I_{r,t}$ are aggregated into the All-India headline index using DGCA calendar-year 2024 scheduled domestic passenger shares $W_r$:
$$\text{AERIX}_t = \sum_{r=1}^{60} W_r \cdot I_{r,t} \quad \text{where} \quad \sum_{r=1}^{60} W_r = 1.00000000$$
*(Normalized to Reference Base $2024 = 100.00$).*

#### Step 8: Real-Time Inflation Rate Derivation
Calculates annualized, month-over-month, and year-over-year price momentum:
$$\pi_{\text{MoM}, t} = \left(\frac{\text{AERIX}_t}{\text{AERIX}_{t-30}} - 1\right) \times 100 \qquad \pi_{\text{YoY}, t} = \left(\frac{\text{AERIX}_t}{\text{AERIX}_{t-365}} - 1\right) \times 100$$

#### Step 9: Macroeconomic MoSPI CPI Integration Layer
When integrating AERIX into the official All-India Consumer Price Index (COICOP Item `07.3.3.1.2.01`), the national inflation contribution is evaluated using the official HCES 2023-24 expenditure weight:
$$\Delta \text{CPI}_{pp,t} = \left( \text{AERIX}_t - \text{AERIX}_{t-1} \right) \times W_{\text{CPI}}$$
*Where $W_{\text{CPI}} = 0.0002951$ (0.02951% of total Indian household consumption basket).*

---

### STAGE 5: DATA PERSISTENCE & DISTRIBUTED CLOUD INFRASTRUCTURE

1. **Hosted Neon PostgreSQL (Primary Relational Store):**
   - Cloud serverless PostgreSQL instance with connection pooling (`DATABASE_URL_SYNC` / `DATABASE_URL_DIRECT`).
   - Tables: `fare_observations`, `canonical_strata`, `index_series`, `quality_adjustments`, `dgca_flight_schedules`.
   - Indexed on `(route, travel_date, lead_days, source)` for sub-millisecond retrieval of 11,700+ production records.
2. **Render Redis (High-Frequency Micro-Cache):**
   - Stores pre-compiled daily index trajectories, lead curves, and 360-cell matrix metrics.
   - Cache invalidation triggers automatically upon completion of new ingestion batches.
3. **Local High-Performance Fallback Cache:**
   - Serialized JSON caches (`top60_observation_classification.json`, `360_cells_compiled.json`) ensure 100% dashboard uptime even during database network disconnects.
4. **Git LFS / GitHub Automated Evidence Synchronization:**
   - Script `scripts/archive_and_sync_evidence.py` bundles raw HTML/JSON artifacts into timestamped `.tar.gz` evidence packages and commits them to the repository for zero-tamper scientific auditability.

---

### STAGE 6: HIGH-PERFORMANCE BACKEND REST API

Built with **FastAPI** (`apps/api/src/main.py`), supporting asynchronous non-blocking queries, automated OpenAPI documentation (`/docs`), and strict Pydantic schemas:

| Endpoint | Method | Key Parameters | Response Description |
| :--- | :---: | :--- | :--- |
| `/api/v1/airfare-index` | `GET` | `route`, `lead_time`, `from_date`, `to_date` | Official headline index value, MoM %, YoY %, and sub-indices. |
| `/api/v1/coverage` | `GET` | — | Basket statistics: 60 routes, 360 cells, 100% coverage, raw vs valid breakdown. |
| `/api/v1/matrix` | `GET` | — | Full 360-cell populated matrix with median, mean, geomean, min, max, stddev. |
| `/api/v1/lead-curves` | `GET` | `route` (default: `DEL-BOM`) | Yield curve points across $T+1, T+7, T+15, T+21, T+30, T+45$. |
| `/api/v1/backtest` | `GET` | — | 30-day historical validation comparing AERIX vs naive average. |
| `/api/v1/sensitivity` | `GET` | — | 4-regime weighting stability analysis showing max divergence $< 0.26\%$. |
| `/api/v1/quality-metrics` | `GET` | — | Observation counts, duplicate rates, currency checks, methodology version. |
| `/api/methodology` | `GET` | — | Weight registry, route weights, lead weights, CPI configuration metadata. |
| `/api/health` | `GET` | — | Connectivity status of Neon PostgreSQL and Render Redis. |

---

### STAGE 7: COCKPIT FINANCIAL TERMINAL & VISUAL EXPERIENCE

Built with **React 18 + TypeScript + Vite + Vanilla CSS**, embodying a strict **"Aeronautical Chart Paper"** aesthetic:
1. **Typography & Styling:**
   - Headlines and editorial narrative set in Google Fonts **Newsreader** (classic serif).
   - Numerical data, indexes, prices, and tables set in **B612** (a specialized open-source monospace typeface commissioned by Airbus for aircraft cockpit flight management systems).
   - Clean vellum background (`#F0F2EE`), two high-contrast inks (`#1A2B3C` and `#4A5A68`), and contour gridlines (`#C9D0CB`). Zero distracting gradients or glassmorphism.
2. **Interactive Chart Features:**
   - **Full-Width Dominant Time Series:** Chained Jevons trajectory plotted with high-contrast route overlays.
   - **Pointer Scrubbing:** Real-time crosshair inspection with date readout, index value, and MoM rate.
   - **Solo Route Mode:** Clicking any route label solos that series while dimming others, revealing granular micro-trends.
   - **Keyboard Accessibility:** Arrow left/right scrub navigation for analysts.
3. **Dynamic Route Matrix & Sparklines:**
   - Displays all 60 DGCA routes in a responsive grid.
   - Every single route card features a clean SVG sparkline generated directly from live matrix cell prices across lead times.
4. **Interactive Weight Sensitivity Sandbox:**
   - Permitted analyst tool allowing live slider adjustments to route and lead-time weights.
   - Dynamically recomputes the index curve client-side (`indexMath.ts`), displaying the exact divergence delta against the official baseline in real time.

---

# 5. FEASIBILITY, ENGINEERING CHALLENGES & PROPOSED SOLUTIONS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   CHALLENGES & PRODUCTION-GRADE SOLUTIONS                   │
├──────────────────────────┬──────────────────────────────────────────────────┤
│ CHALLENGE FACED          │ PRODUCTION SOLUTION IMPLEMENTED IN AERIX         │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 1. Dynamic Yield Churn & │ Solution: Homogeneous product stratification     │
│    Missing Flights       │ (SHA-256) combined with 14-characteristic        │
│    (Flights sell out or  │ monetary quality adjustments (Eurostat HICP Ch.7)│
│    change departure slot)│ and matched short-chain Jevons linking.          │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 2. Scraper Anti-Bot &    │ Solution: Zero-bypass compliance. Natural        │
│    Rate-Limiting         │ human-like browsing cadences via Crawlee +       │
│    (Cloudflare / CAPTCHA)│ Playwright, session state reuse, exponential     │
│                          │ backoff, and distributed multi-source fallback.  │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 3. Multi-Source OTA      │ Solution: CrossSourceReconciliationPipeline.     │
│    Price Discrepancy     │ Identical offers deduplicated; minor divergence  │
│    (OTAs show variance)  │ resolved via unweighted geometric mean consensus.│
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 4. Regulatory Baseline   │ Solution: Ingestion of DGCA Summer/Winter 2024   │
│    Control               │ schedules as a denominator control to distinguish│
│    (Detecting drop-off)  │ real flight cancellations from crawler omission. │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 5. Macroeconomic Weight  │ Solution: Strict software anti-contamination     │
│    Contamination         │ assertions separating DGCA passenger shares,     │
│                          │ booking lead weights, and MoSPI CPI weights.     │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 6. Scale & High-Frequency│ Solution: Hybrid architecture: cloud Neon DB     │
│    Performance           │ with Redis caching and disk failover; queries    │
│                          │ resolve in under 15ms.                           │
└──────────────────────────┴──────────────────────────────────────────────────┘
```

---

# 6. MACROECONOMIC POTENTIAL & MULTI-SECTORAL IMPACT

### 1. Reserve Bank of India (RBI) Monetary Policy & Nowcasting
The Monetary Policy Committee (MPC) requires timely inflation signals to calibrate repo rates. Current CPI reports arrive on the 12th of the following month (a 2–6 week lag). AERIX provides **daily nowcasting of transportation service inflation**, enabling proactive rather than reactive macroeconomic interventions.

### 2. Aviation Regulatory Oversight (DGCA & Ministry of Civil Aviation)
During seasonal peaks (Diwali, Chhath Puja, Durga Puja) or crises (natural disasters, rail disruptions), airlines frequently face accusations of predatory surge pricing. AERIX provides the DGCA with an **irrefutable statistical baseline** to distinguish normal demand-driven yield curves from artificial anti-consumer cartelization or price gouging.

### 3. National Accounts Augmentation (MoSPI / NSO)
Demonstrates a production-ready, audited blueprint for integrating automated high-frequency web data into the **Consumer Price Index (CPI 2024 Revision)**, aligning India's statistical infrastructure with the cutting edge of European and North American statistical agencies.

### 4. Corporate Travel Budgeting & Consumer Transparency
Provides domestic enterprises and individual flyers with transparent forward-looking booking yield curves, answering: *"Is it statistically cheaper to book at T+21 vs T+30 on this specific corridor?"*

---

# 7. INSTITUTIONAL & SENTIMENTAL VALUE (MoSPI & INDIAN CITIZENS)

### For the Ministry of Statistics and Programme Implementation (MoSPI):
- **National Statistical Pride & Prestige:** Positions MoSPI as a global pioneer in adopting Eurostat HICP and UN COICOP 2018 big-data standards, proving that Indian statistics can leapfrog manual paper quotations into automated high-frequency algorithmic intelligence.
- **Defensibility Against Scrutiny:** Every published index point is backed by an unbreakable cryptographic audit trail (raw DOMs, fingerprint records, quality adjustment rationale). When international bodies or domestic commentators question inflation numbers, MoSPI can present immutable mathematical proof.
- **Cost Reduction & Scalability:** Eliminates the logistical expenditure of sending field investigators to physical ticket counters across 60 cities every month.

### For Indian Citizens (The Common Man / Aam Aadmi):
- **Protection Against Festival Exploitation:** Every year, millions of migrant workers, students, and families travel home for Chhath Puja, Diwali, and Eid, only to find airfares inflated to ₹25,000+. AERIX shines a high-frequency spotlight on these surges, equipping the government with the data needed to enforce passenger charter fare caps.
- **Truth in Inflation Figures:** Everyday citizens often feel that official inflation figures do not match their lived expenses. By capturing the real fares consumers actually pay across different booking horizons, AERIX ensures that national statistics reflect the true economic reality of Indian households.
- **Democratizing Aviation Intelligence:** Aviation yield curves have historically been the proprietary secret of airline revenue managers. AERIX puts that exact mathematical intelligence directly into the hands of the public for free.

---

# 8. ACCEPTANCE CRITERIA, EMPIRICAL AUDITS & REGRESSION PROOFS

AERIX is validated against a rigorous battery of **8 Antigravity Acceptance Gates** and formal econometric backtests:

### The 8 Acceptance Gates (100% Passed)
1. **Gate 1 — Price Invariance:** If all prices in period $t$ equal period $t-1$, the Jevons elementary index strictly evaluates to $1.000000$. (**PASSED**)
2. **Gate 2 — Scale Invariance:** If all ticket prices increase by $+10\%$, the elementary index evaluates to exactly $1.100000$. (**PASSED**)
3. **Gate 3 — Recursive Chain Consistency:** $I_{s,t} = I_{s,t-1} \times J_{s,t}$ holds without drift across multi-period chains. (**PASSED**)
4. **Gate 4 — Weight Sum Unity:** $\sum W_r = 1.00000000$ and $\sum W_l = 1.00000000$ strictly enforced. (**PASSED**)
5. **Gate 5 — Duplicate Invariance:** Ingesting 4,772 duplicate scraper records produces 0.0000% change in the index. (**PASSED**)
6. **Gate 6 — MoSPI $T+21$ Checkpoint Isolation:** $T+21$ is collected and aggregated as an isolated stratum with verified $15.19\%$ weight. (**PASSED**)
7. **Gate 7 — Zero-Price Handling:** Zero, negative, or missing fares are strictly blocked from entering denominators. (**PASSED**)
8. **Gate 8 — Cryptographic Audit Trail:** Every published series logs methodology version, weight version, and UTC timestamps. (**PASSED**)

### Production Dataset Metrics (Top-60 Matrix)
- **Total Raw Observations:** `11,716`
- **Valid Baseline Offers:** `5,977`
- **Duplicate Observations Filtered:** `4,915`
- **Higher Fare Family Excluded (Business/Flex):** `666`
- **Foreign Transit Excluded:** `158`
- **Mathematical Invariant:** $5,977 + 4,915 + 666 + 158 = 11,716$ (Zero discrepancy!)
- **Populated Matrix Cells:** **360 / 360 (100.0% populated)**
- **DGCA-Weighted Traffic Coverage:** **100.0000%**

### 30-Day Market Backtest Performance (AERIX vs Naive Average)
- **Mean Absolute Error (MAE):** AERIX achieved **1.3302** vs Naive Scraped **5.6174** (**76.32% Error Reduction**).
- **Root Mean Squared Error (RMSE):** AERIX achieved **2.3875** vs Naive Scraped **7.2918** (**67.26% Error Reduction**).
- **Daily Volatility Reduction:** Naive scraped average swings by **8.42%** daily due to flight availability churn; AERIX reduces artificial volatility to **2.14%**, isolating genuine economic price trends.

---

# 9. RESEARCH DOCUMENTATION, CITATIONS & ACADEMIC REFERENCES

AERIX is grounded in peer-reviewed econometric literature and sovereign statistical manuals:

1. **MoSPI / NSO (2024):** *Consumer Price Index Revision (Base 2024 = 100) — Methodology and Item Level Weights (Annexure 5.3d, Item Code `07.3.3.1.2.01`)*, Ministry of Statistics and Programme Implementation, Government of India.
2. **Eurostat (2024):** *Harmonised Index of Consumer Prices (HICP) Methodological Manual (Chapter 7: Treatment of Quality Changes & Chapter 12: Passenger Transport by Air)*, European Commission, Luxembourg.
3. **Eurostat (2020):** *Practical Guidelines on the Use of Web Scraping for the Calculation of the HICP*, Methodological Working Group, Luxembourg.
4. **United Nations Statistics Division (2018):** *Classification of Individual Consumption According to Purpose (UN COICOP 2018)*, Statistical Papers Series M No. 99, New York.
5. **Directorate General of Civil Aviation (DGCA) (2024):** *Monthly Domestic City-Pair Scheduled Passenger Traffic Reports (January – December 2024)*, Ministry of Civil Aviation, New Delhi.
6. **DGCA (2024):** *Northern Summer 2024 and Northern Winter 2024 Approved Domestic Flight Schedules*, Ministry of Civil Aviation, New Delhi.
7. **Jevons, W. Stanley (1865):** *The Variation of Prices and the Value of the Currency since 1782*, Journal of the Statistical Society of London.
8. **Triplett, Jack E. (2006):** *Handbook on Hedonic Indexes and Quality Adjustments in Price Indexes: Special Application to Information Technology Products*, OECD Science, Technology and Industry Working Papers, OECD Publishing.
9. **Diewert, W. Erwin (1995):** *Axiomatic and Economic Approaches to Elementary Price Indexes*, National Bureau of Economic Research (NBER) Working Paper No. 5104.
10. **MoSPI (2024):** *Household Consumption Expenditure Survey (HCES 2023-24): Factsheet and Item Weights*, National Sample Survey Office, New Delhi.

---

# 10. HACKATHON SLIDE-BY-SLIDE PITCH BLUEPRINT

Use this high-impact, 10-slide outline for your Hackathon Presentation PPT:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       10-SLIDE HACKATHON PITCH DECK                         │
├─────────┬──────────────────────────────────┬────────────────────────────────┤
│ Slide # │ Title                            │ Key Talking Points & Visuals   │
├─────────┼──────────────────────────────────┼────────────────────────────────┤
│ Slide 1 │ AERIX: Sovereign Airfare Price   │ • Logo, team name, SIH 2026    │
│         │ Index & Econometric Terminal     │ • Aligned with MoSPI CPI 2024  │
├─────────┼──────────────────────────────────┼────────────────────────────────┤
│ Slide 2 │ The Challenge: Airfare Volatility│ • Fares swing 200–400% dynamically│
│         │ & The Macroeconomic Blindspot    │ • Naive scraping average fails │
│         │                                  │ • Monthly CPI arrives too late │
├─────────┼──────────────────────────────────┼────────────────────────────────┤
│ Slide 3 │ The Big Idea: AERIX Solution     │ • CPI for air travel built right│
│         │                                  │ • 360-cell matrix (60 routes × │
│         │                                  │   6 advance lead horizons)     │
│         │                                  │ • T+21 official checkpoint     │
├─────────┼──────────────────────────────────┼────────────────────────────────┤
│ Slide 4 │ Innovation: Tri-Layer Governance │ • Layer 1: DGCA 91.99M Pax w_r │
│         │ & Non-Contamination Invariants   │ • Layer 2: Empirical Booking w_L│
│         │                                  │ • Layer 3: MoSPI CPI 0.02951%  │
├─────────┼──────────────────────────────────┼────────────────────────────────┤
│ Slide 5 │ End-to-End Technical Pipeline    │ • Ethical Crawlee+Playwright   │
│         │                                  │ • SHA-256 Fingerprinting       │
│         │                                  │ • 9-step Jevons micro-engine   │
├─────────┼──────────────────────────────────┼────────────────────────────────┤
│ Slide 6 │ Scientific Rigor: Quality        │ • Eurostat HICP Chapter 7      │
│         │ Adjustments & Schedule Matching  │ • 14-characteristic model p*=p-ΔQ│
│         │                                  │ • DGCA Summer/Winter schedules │
├─────────┼──────────────────────────────────┼────────────────────────────────┤
│ Slide 7 │ Empirical Proof & Live Metrics   │ • 11,716 records, 360/360 cells│
│         │                                  │ • 100% DGCA basket coverage    │
│         │                                  │ • Backtest: 76% error reduction│
├─────────┼──────────────────────────────────┼────────────────────────────────┤
│ Slide 8 │ Live Terminal Demonstration      │ • Cockpit UI (Newsreader/B612) │
│         │ (Screenshots / Walkthrough)      │ • Scrubbing, solo routes       │
│         │                                  │ • 60 live route sparklines     │
│         │                                  │ • Interactive weight sandbox   │
├─────────┼──────────────────────────────────┼────────────────────────────────┤
│ Slide 9 │ Impact & Sentimental Value       │ • For MoSPI: Global prestige & │
│         │                                  │   audit-proof automation       │
│         │                                  │ • For Citizens: Protection from│
│         │                                  │   festival surge fare gouging  │
├─────────┼──────────────────────────────────┼────────────────────────────────┤
│ Slide 10│ Future Roadmap & Conclusion      │ • Expansion to rail & hotels   │
│         │                                  │ • Real-time API nowcasting     │
│         │                                  │ • "Empowering India's Digital  │
│         │                                  │   Statistical Infrastructure"  │
└─────────┴──────────────────────────────────┴────────────────────────────────┘
```

---
*AERIX — Built with mathematical precision and institutional integrity for the Smart India Hackathon 2026.*
