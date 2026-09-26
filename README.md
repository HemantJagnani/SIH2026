# India Airfare Price Index (APIx) — SIH 2026

Welcome to the **Indian Airfare Price Index (APIx)** repository! This project implements an official, production-grade statistical price index system for tracking, normalizing, and compiling domestic airfares across India in accordance with the **MoSPI CPI 2024 revision guidelines ($2024 = 100$)** and **Eurostat HICP airfare web scraping standards**.

---

## ⚡ Quick Start (One-Click Launch)

To start both the FastAPI backend and the React frontend simultaneously and launch the dashboard in your default browser:

```bat
start.bat
```

Or run manually:
1. **Backend (FastAPI):**
   ```powershell
   $env:PYTHONPATH="apps/scraper/src;apps/api/src"
   python -m uvicorn apps.api.src.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **Frontend (Vite React):**
   ```powershell
   cd web
   npm run dev
   ```
3. Open your browser at `http://localhost:5173` (or `http://localhost:5174`). API documentation is available at `http://localhost:8000/docs`.

---

## 🏗️ System Architecture & Statistical Hierarchy

Unlike naive web scrapers that compute unstable arithmetic averages of ticket search results, APIx implements a mathematically rigorous calculation hierarchy:

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

## 📅 Advance-Purchase Horizons & MoSPI Alignment

APIx captures ticket quotes across six calibrated domestic booking horizons:
- **$T+1$:** Last-minute booking (high dynamic elasticity) — Weight: $15\%$
- **$T+7$:** Short-horizon discretionary booking — Weight: $30\%$
- **$T+15$:** Intermediate domestic booking window — Weight: $20\%$
- **$T+21$:** **Official MoSPI CPI 2024 Alignment Checkpoint** — Weight: $15\%$
- **$T+30$:** Standard advance vacation booking — Weight: $12\%$
- **$T+45$:** Forward planning baseline anchor — Weight: $8\%$

> **Note on $T+21$:** The MoSPI CPI 2024 Expert Group specifically designated **21 days prior to departure** as the standard advance-purchase specification for domestic air travel. $T+21$ is collected and aggregated as an independent, isolated stratum.

---

## 🌐 Production REST API Endpoints

The FastAPI backend exposes official CPI-compatible endpoints:

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/v1/airfare-index` | `GET` | Official APIx index series, MoM inflation rate, and sub-indices |
| `/api/v1/quality-metrics` | `GET` | Null/duplicate rates, valid observations count, and stratum coverage |
| `/api/v1/lead-curves` | `GET` | Route-specific advance purchase yield curve points ($T+1 \dots T+45$) |
| `/api/v1/backtest` | `GET` | 30-day historical backtest results and tracking error statistics |
| `/api/v1/sensitivity` | `GET` | 4-variant weighting sensitivity matrix and divergence bounds |
| `/api/methodology` | `GET` | Formal methodology metadata, formulas, and weight configuration |
| `/api/observations` | `GET` | Filterable list of raw and normalized fare observations |

---

## 📊 Verification & Empirical Reports

- [`METHODOLOGY.md`](file:///c:/sih%202026/apix/METHODOLOGY.md): Comprehensive mathematical specification and regulatory alignment.
- [`BACKTEST_REPORT.md`](file:///c:/sih%202026/apix/BACKTEST_REPORT.md): 30-day historical backtest evaluating short-chain Jevons tracking fidelity ($\text{MAE} = 1.3302$, $\text{RMSE} = 2.3875$) and proving volatility dampening vs naive scraper churn.
- [`SENSITIVITY_REPORT.md`](file:///c:/sih%202026/apix/SENSITIVITY_REPORT.md): Robustness evaluation across 4 weighting regimes (DGCA Passenger Share, Route Expenditure, Equal Route, Equal Lead Time) confirming maximum divergence bounded at **$0.2625$ index points ($0.255\%$)**.
- [`DATA_QUALITY_REPORT.md`](file:///c:/sih%202026/apix/DATA_QUALITY_REPORT.md): Phase 1 audit of scraped datasets.
- [`PROGRESS.md`](file:///c:/sih%202026/apix/PROGRESS.md): Detailed task completion tracking.

---

## 🧪 Automated Test Suite

APIx includes an extensive test suite verifying all 8 Antigravity acceptance gates:

```powershell
python -m pytest apps/scraper/tests/models/ -v
```

All 70 unit and integration tests pass with 100% success rate.
