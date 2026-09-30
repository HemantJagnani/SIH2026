# AERIX — Official 5-Minute Demonstration Video Script

**Target Duration:** Exactly 5:00 Minutes (300 Seconds)  
**Tone:** Confident, professional, clear, and government-grade  
**Pacing:** ~135 words per minute (Total: ~680 spoken words)

---

## ⏱️ Timeline & Scene Overview

| Time | Duration | Section | Visual Focus |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:45** | 45 sec | **1. The Problem & AERIX Overview** | Overview Page, Sovereign Badges, DGCA Coverage |
| **0:45 – 1:55** | 70 sec | **2. Index Dashboard, Basket & Synthetic Baseline** | Index Page, Route Audit Modal, August Rationale |
| **1:55 – 2:35** | 40 sec | **3. Advance Booking Curves & T+21** | Booking Curves Page, Lead-time dispersion |
| **2:35 – 3:20** | 45 sec | **4. How It Works (5-Level Data Flow)** | Flow Page, Level 1 to Level 5 Cards |
| **3:20 – 3:55** | 35 sec | **5. Empirical Backtesting & Validation** | Backtest Page, 199K+ flights, 3.52% MAPE |
| **3:55 – 4:35** | 40 sec | **6. Government APIs & Methodology** | Overview API Feeds, Live Test, Method Specs |
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
> Welcome to **AERIX** — an econometric, high-frequency Airfare Price Index engineered specifically for the Ministry of Statistics and Programme Implementation.
> 
> AERIX conforms strictly to the **MoSPI CPI 2024 base**, the **Eurostat HICP standards**, and tracks the official **DGCA Top-60 domestic route basket**, representing over 91 million passengers and 57% of India's commercial aviation traffic."

---

### [0:45 – 1:55] Scene 2: Index Dashboard, DGCA Basket & The Rationale for Synthetic Data (70 sec)
**Visual on Screen:**
- Arrive on the **"Index"** page.
- Point cursor to the Headline Index (`100.00` Base 2024 = 100) and All-India Weighted Fare (`₹6,520`).
- Scroll down to the **Basket Routes** cards showing the **Top-60 routes** with official DGCA passenger weights and percentage changes.
- Click **"Inspect Data"** on a route card (e.g., `DEL-BOM`):
  - Briefly display the modal with raw flight quotes, EaseMyTrip & Google Flights sources, IndiGo & Air India logos, flight numbers, and `VALID_BASELINE` quality flag.
- Click **"Close"** to dismiss the modal and bring the focus back to the main index graph:
  - Toggle between **Daily** and **Monthly** trend views on the chart.
  - Hover over the 1 Aug to 31 Aug historical timeline.

**Voiceover (Word-for-Word — 70 Seconds):**
> "On the **Index Dashboard**, our index is anchored to **Base 2024 = 100** because MoSPI is currently revising the national CPI base year to 2024. Using official **DGCA CY2024 passenger statistics as our reference benchmark**, we established our **Top-60 domestic route basket**, capturing 57% of India's commercial passenger volume.
> 
> Across these corridors, we scraped real live flight data from Google Flights and EaseMyTrip. Clicking **Inspect Data**, we see the transparent raw quotes—carrier identities, flight numbers, base fares, and our fourteen-point quality validation checks.
> 
> Returning to the graph, you might ask: **why did we use synthetic data for August?** 
> Airline OTAs only display current and forward booking dates—the moment a flight takes off, past ticket prices are permanently erased from public APIs. To thoroughly stress-test our 360-cell matrix, weekly trend curves, and monthly chaining formulas across a full 31-day calendar month without waiting months for live accumulation, we generated realistic synthetic data calibrated to official DGCA tariff distributions.
> 
> This proves our monthly compilation works with zero errors. And with our automated five AM pipeline now continuously scraping live fares every morning, AERIX will seamlessly accumulate genuine real-time weekly and monthly series going forward."

---

### [1:55 – 2:35] Scene 3: Booking Curves & The T+21 Checkpoint (40 sec)
**Visual on Screen:**
- Click the **"Booking curves"** tab.
- Hover over the curve points from **T+1** (last-minute booking) down to **T+45** (early planning).
- Highlight the marked **T+21 MoSPI Checkpoint**.
- Toggle between different route selections to show how curve shapes differ between business routes and leisure sectors.

**Voiceover (Word-for-Word — 40 Seconds):**
> "The heart of our econometric innovation lies in our **Booking Curves**. 
> 
> Airlines do not sell one price; they sell across a dynamic horizon. AERIX samples six standardized lead-time buckets: T+1, T+7, T+15, T+21, T+30, and T+45, creating a full 360-cell matrix every morning.
> 
> Instead of simple averaging, we assigned empirical weights to every lead-time horizon based on real passenger booking patterns. And we isolate the **T+21 advance purchase horizon** to match the official MoSPI CPI pricing checkpoint, ensuring inflation reflects genuine economic price movements rather than last-minute seat scarcity."

---

### [2:35 – 3:20] Scene 4: How It Works — The 5-Level Calculation Flow (45 sec)
**Visual on Screen:**
- Click the **"How It Works"** tab.
- Show the interactive controller at the top (Pick Path: `DEL-BOM`, Timeframe: `T+21`).
- Scroll smoothly down through the 5 stacked levels on the visual flowchart:
  - **Level 1**: Multiple Providers &rarr; Single Flight Price (average across OTAs).
  - **Level 2**: All Flights in a Horizon &rarr; Geometric Mean (Jevons).
  - **Level 3**: 6 Timeframes &rarr; Weighted Route Fare.
  - **Level 4**: 60 Routes &rarr; All-India National Airfare (DGCA weights).
  - **Level 5**: Final Formula: $\text{Current National Fare} / \text{Base Fare} \times 100$.

**Voiceover (Word-for-Word — 45 Seconds):**
> "Under **How It Works**, we visualize the exact mathematical data flow.
> 
> Our automated scrapers use rotating Indian residential IPs and human-like delays to avoid rate limits and bot blocks entirely. Once ingested, the data flows through five transparent levels:
> 
> First, we harmonize multiple OTA quotes for each flight by taking their consensus average. 
> Second, for a particular route and lead time, we compute the **Geometric Mean** across all flights using the Jevons formula. 
> Third, we compute a single route fare by taking the **weighted average across all six lead times** using our empirical weights. 
> Fourth, we aggregate across all sixty sectors using **official DGCA passenger volume weights** to calculate the All-India national airfare. 
> Finally, we divide the current national fare by the 2024 reference base and multiply by one hundred to produce the official headline CPI index."

---

### [3:20 – 3:55] Scene 5: Empirical Backtesting & Model Validation (35 sec)
**Visual on Screen:**
- Click the **"Backtest / Validation"** tab.
- Show the benchmark comparison chart: **AERIX Econometric Index** vs **Raw Scraped Average** vs **Official DGCA TMU Actuals**.
- Highlight the error statistics box: **MAPE 3.52%** and **MAE 1.33 pt** vs Raw Average Error of **5.09 pt**.
- Scroll to the 4-regime Weight Sensitivity table.

**Voiceover (Word-for-Word — 35 Seconds):**
> "Under **Backtest & Validation**, to prove our formulas work in the real world, we tested AERIX against nearly two lakh real flights from March 2022.
> 
> Look at the chart: if you just take simple averages of scraped ticket prices, you get huge errors and fake price spikes. But AERIX closely matches the official government DGCA numbers with over 96% accuracy and an error of barely 1.3 points.
> 
> This proves our index is dependable, robust, and ready for official government use."

---

### [3:55 – 4:35] Scene 6: Government API Integration & Method (40 sec)
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
