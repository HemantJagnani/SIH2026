# AERIX — Official 5-Minute Demonstration Video Script

**Target Duration:** Exactly 5:00 Minutes (300 Seconds)  
**Tone:** Confident, professional, clear, and government-grade  
**Pacing:** ~135 words per minute (Total: ~680 spoken words)

---

## ⏱️ Timeline & Scene Overview

| Time | Duration | Section | Visual Focus |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:45** | 45 sec | **1. The Problem & AERIX Overview** | Overview Page, Sovereign Badges, DGCA Coverage |
| **0:45 – 1:40** | 55 sec | **2. Index Dashboard & Route Audit** | Index Page, Route Soloing, Inspect Data Modal |
| **1:40 – 2:20** | 40 sec | **3. Advance Booking Curves & T+21** | Booking Curves Page, Lead-time dispersion |
| **2:20 – 3:05** | 45 sec | **4. Empirical Backtesting & Validation** | Backtest Page, 199K+ flights, 3.52% MAPE |
| **3:05 – 3:50** | 45 sec | **5. How It Works (9-Step Pipeline)** | Flow Page, Interactive Steps, Quality Gates |
| **3:50 – 4:35** | 45 sec | **6. Government APIs & Methodology** | Overview API Feeds, Live Test, Method Specs |
| **4:35 – 5:00** | 25 sec | **7. Summary & Sovereign Impact** | S1/S2 Keepalive, Conclusion |

---

## 🎬 Detailed Scene-by-Scene Script

### [0:00 – 0:45] Scene 1: The Problem & AERIX Overview
**Visual on Screen:**
- Start on the **Overview** page (`/`).
- Show the headline *"A daily airfare price index for Indian domestic routes, built the way the CPI is built."*
- Slowly scroll past the **MoSPI**, **DGCA**, and **Eurostat** official badges.
- Highlight the **Production Data & Basket Status** counter: `Routes scraped (60/60)`, `Coverage (57.02% of national passengers)`.

**Voiceover (Word-for-Word):**
> "In India, dynamic pricing causes the exact same flight seat to fluctuate by two to four hundred percent depending on when you book. Traditional CPI compilation averages raw quotes, which introduces severe dynamic pricing bias and misses holiday surges.
> 
> Welcome to **AERIX** — the first econometric, high-frequency Airfare Price Index engineered specifically for the Ministry of Statistics and Programme Implementation.
> 
> AERIX conforms strictly to the **MoSPI CPI 2024 base**, the **Eurostat HICP standards**, and tracks the official **DGCA Top-60 domestic route basket**, representing over 91 million passengers and 57% of India's commercial aviation traffic."

---

### [0:45 – 1:40] Scene 2: Index Dashboard, DGCA Top-60 Basket & Multi-Period Aggregation (55 sec)
**Visual on Screen:**
- Arrive on the **"Index"** page.
- Point cursor to the Headline Index (`100.00` Base 2024 = 100) and All-India Weighted Fare.
- Scroll down to the **Basket Routes** cards showing the **Top-60 routes** with official DGCA passenger weights and percentage changes.
- Click **"Inspect Data"** on a route card (e.g., `DEL-BOM`):
  - Briefly display the modal with raw flight quotes, EaseMyTrip & Google Flights sources, IndiGo & Air India logos, flight numbers, and `VALID_BASELINE` quality flag.
- Click **"Close"** to dismiss the modal and bring the focus back to the main index graph:
  - Toggle between **Daily** and **Monthly** trend views on the chart.
  - Gesture towards the continuous timeline.

**Voiceover (Word-for-Word — 55 Seconds):**
> "On the **Index Dashboard**, our index is anchored to **Base 2024 = 100** because MoSPI is currently revising the national CPI base year to 2024. Using official **DGCA CY2024 passenger statistics as our reference benchmark**, we established our **Top-60 domestic route basket**, capturing 57% of India's passenger volume.
> 
> Across these corridors, we scraped real live flight data from Google Flights and EaseMyTrip. Clicking **Inspect Data**, we see the transparent raw quotes—carrier identities, flight numbers, base fares, and our fourteen-point quality validation checks.
> 
> Returning to the graph, because airline portals never provide retroactive past-date fare archives, we utilized calibrated synthetic data for August to test our index pipeline. This demonstrates seamless weekly and monthly aggregation. And with our automated five AM pipeline now scraping live data every day, AERIX will continuously accumulate genuine real-time weekly and monthly series going forward."

---

### [1:35 – 2:20] Scene 3: Booking Curves & The T+21 Checkpoint
**Visual on Screen:**
- Click the **"Booking curves"** tab.
- Hover over the curve points from **T+1** (last-minute booking) down to **T+45** (early planning).
- Highlight the marked **T+21 MoSPI Checkpoint**.
- Toggle between different route selections to show how curve shapes differ between business routes and leisure sectors.

**Voiceover (Word-for-Word):**
> "The heart of our econometric innovation lies in our **Booking Curves**. 
> 
> Airlines do not sell one price; they sell across a dynamic horizon. AERIX samples six standardized lead-time buckets: T+1, T+7, T+15, T+21, T+30, and T+45, creating a full 360-cell matrix every morning.
> 
> Crucially, we isolate the **T+21 advance purchase horizon**. This matches the official MoSPI CPI pricing checkpoint window, ensuring that inflation reflects genuine economic price movements rather than last-minute seat scarcity."

---

### [2:20 – 3:05] Scene 4: Empirical Backtesting & Model Validation
**Visual on Screen:**
- Click the **"Backtest / Validation"** tab.
- Show the benchmark comparison chart: **AERIX Econometric Index** vs **Raw Scraped Average** vs **Official DGCA TMU Actuals**.
- Highlight the error statistics box: **MAPE 3.52%** and **MAE 1.33 pt** vs Raw Average Error of **5.09 pt**.
- Scroll to the 4-regime Weight Sensitivity table.

**Voiceover (Word-for-Word):**
> "A sovereign index must be empirically proven. Under **Backtest & Validation**, we benchmarked AERIX against 199,672 real commercial flight observations across March 2022.
> 
> The results are definitive: while simple averaging generates massive volatility with a 5.09-point error, AERIX matches actual DGCA benchmark yields with a **Mean Absolute Error of just 1.33 points and 3.52% MAPE**. 
> 
> Our sensitivity analysis confirms that index trajectory remains stable within 0.26 index points across four distinct weighting regimes."

---

### [3:05 – 3:50] Scene 5: How It Works — The 9-Step Pipeline
**Visual on Screen:**
- Click the **"How It Works"** tab.
- Walk through the interactive visual flowchart:
  - Step 1: Automated 5 AM Dual-Channel Ingestion & Rotating Residential IPs.
  - Step 2: Quality Gates & Outlier Filtering.
  - Step 3: Matched-Model Axiom.
  - Step 4: Jevons Geometric Mean relatives.
  - Step 5: Young Higher-Level Aggregation with DGCA weights.
- Click on a step box to reveal its formula and implementation notes.

**Voiceover (Word-for-Word):**
> "In the **How It Works** section, we visualize the complete nine-step pipeline.
> 
> Every day at **5:00 AM IST**, automated workers trigger Crawlee and Playwright scrapers through **rotating Indian residential IPs**, collecting prices across all 360 matrix cells without bot blocks or rate limits.
> 
> Observations pass through strict deduplication and quality gates. Next, following international Eurostat HICP standards, elementary price relatives are compiled using the **Jevons geometric mean**, and aggregated into the All-India Index using the **MoSPI Young formulation** under COICOP category 07.3.3.1.2.01."

---

### [3:50 – 4:35] Scene 6: Government API Integration & Method
**Visual on Screen:**
- Navigate back to **Overview** and scroll down to the **Institutional Data Ingestion Feeds** section.
- Point out the **MoSPI CPI Feed** (`/api/v1/nso/cpi-feed`) and **RBI Nowcast Feed** (`/api/v1/rbi/nowcast`).
- Click **"⚡ Test Live Response"** on the MoSPI feed — show the instant HTTP 200 response drawer with JSON payload and <15ms latency.
- Click the **"Interactive Swagger UI (/docs)"** button to quickly show the FastAPI docs in a tab, then switch to the **"Method"** tab to show the LaTeX math blocks.

**Voiceover (Word-for-Word):**
> "To serve government stakeholders seamlessly, AERIX provides direct, read-only institutional data feeds.
> 
> On our Overview page, officials can access dedicated endpoints: the **MoSPI NSO CPI Feed** in both JSON and CSV formats, and the **RBI Nowcasting Feed** for high-frequency monetary surveillance.
> 
> With one click, officials can test live responses—delivering sub-15ms cached responses powered by Neon PostgreSQL and Redis. Full interactive Swagger UI documentation and comprehensive econometric specifications in the **Method** tab ensure zero implementation friction."

---

### [4:35 – 5:00] Scene 7: Architecture, Keepalive & Conclusion
**Visual on Screen:**
- Briefly show terminal or browser tab with the `/api/heartbeat` diagnostic output showing `Service S1 (API)` and `Service S2 (Scraper)` both healthy with hundreds of consecutive successful keepalives.
- Return to the clean AERIX header on the web dashboard.

**Voiceover (Word-for-Word):**
> "Behind the scenes, our cloud infrastructure maintains a resilient two-service mutual heartbeat loop, ensuring continuous 24/7 worker uptime.
> 
> AERIX bridges the gap between modern dynamic airline pricing and national statistical rigor — providing India with an accurate, tamper-proof, and automated sovereign airfare price index.
> 
> Thank you."
