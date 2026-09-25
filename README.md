# India Airfare Price Index (SIH 2026)

Welcome to the **India Airfare Price Index**! This repository contains a production-grade data-acquisition pipeline and visualization dashboard for tracking, normalizing, and analyzing Indian domestic airfares.

---

## 🏗️ System Architecture & Pipeline Overview

The project is built as a complete end-to-end data pipeline, consisting of four primary components:

### 1. Data Collection & Scraping Engine (`apps/scraper/`)
The scraper engine is responsible for fetching real flight data. It is designed to be highly modular and resilient, supporting multiple source adapters:
- **Ignav API Adapter:** Integrates directly with the Ignav API to pull pristine fare data.
- **EaseMyTrip Browser Adapter:** Employs a robust DOM parsing approach to extract flight data directly from EaseMyTrip search result pages using raw DOM node structures, bypassing blocks.
- **Validation Pipeline:** Every single flight observation passes through `AirfareValidationPipeline`. It normalizes currencies, standardizes timestamps, ensures base/tax sums match the total fare, and flags anomalies.

### 2. Relational Storage System (`apps/scraper/src/storage/`)
- Backed by **PostgreSQL** and **Redis** (managed locally via Docker Compose).
- Utilizes asynchronous **SQLAlchemy** models to track scraping jobs, batch runs, and raw observations.
- Data structures allow for complex indexing on attributes like `route`, `lead_days`, `fare_family`, and `collection_mode` (API vs. BROWSER).

### 3. FastAPI Backend (`apps/api/`)
- A fast, async Python backend built on **FastAPI**.
- Exposes API endpoints (e.g., `/api/observations`) to the frontend.
- Currently processes a local static JSON dump of EaseMyTrip parsing (`easemytrip_parsed_data.json`) to bypass active database constraints for development speed, formatting it cleanly for consumption by the React dashboard.

### 4. React Frontend Dashboard (`web/`)
- A modern Single Page Application (SPA) built with **React**, **TypeScript**, and **Vite**.
- Fetches live/indexed data from the FastAPI backend and provides dynamic insights into fare structures.
- Visualizes key metrics including Total Fare, Lead Days, Price Status, and the Path/Source of the scrape.

---

## 📂 Project Structure

```text
SIH2026/
├── apps/
│   ├── api/                  # FastAPI backend server
│   │   └── src/main.py       # API endpoints and CORS config
│   └── scraper/              # Data collection pipeline
│       └── src/
│           ├── adapters/     # Source adapters (Ignav, EaseMyTrip)
│           ├── scripts/      # Execution scripts (run_ignav.py, etc.)
│           ├── storage/      # SQLAlchemy DB models and sessions
│           └── validation/   # Normalization and quality gates
├── web/                      # React Frontend application
│   ├── src/                  # React components and views
│   ├── package.json          # Node.js dependencies
│   └── vite.config.ts        # Vite configuration
├── docker-compose.yml        # PostgreSQL & Redis infrastructure
└── easemytrip_parsed_data.json # Local dump of captured DOM data
```

---

## 🚀 How to Run the Project Locally

### 1. Database Infrastructure (Docker)
Ensure Docker Desktop is running, then start the database services:
```bash
docker-compose up -d
```

### 2. Start the Backend API (FastAPI)
The FastAPI backend serves the flight data to the dashboard. 
*Note: Make sure port 8000 on your machine is not hijacked by other background services. If it is, kill the hijacking process or change the port below to 8001.*

Open a PowerShell terminal at the root of the project:
```powershell
# Set the Python path to include the scraper modules
$env:PYTHONPATH="apps/scraper/src"

# Run the backend on port 8000
uvicorn apps.api.src.main:app --host 0.0.0.0 --port 8000
```
*The API will be available at `http://localhost:8000/api/observations`.*

### 3. Start the Frontend Dashboard (React + Vite)
Open a *new* terminal window, navigate to the `web` directory, and start the development server:
```powershell
cd web
npm install
npm run dev
```
*The dashboard will be available in your browser at `http://localhost:5173/`.*

---

## 🛠️ Modifying the API Port
If you encounter **CORS** or **Authentication Failed** errors on the frontend, it usually means your local port `8000` is hijacked by another hidden application.

**To fix this:**
1. Start your backend on port `8001` instead:
   ```powershell
   uvicorn apps.api.src.main:app --host 0.0.0.0 --port 8001
   ```
2. Open `web/src/api.ts` and change the `BASE` constant to point to `8001`:
   ```typescript
   const BASE = 'http://localhost:8001/api';
   ```
3. Vite will hot-reload automatically, and your frontend will connect successfully!

---

## 📊 Pipeline Status
Currently, the `main` branch includes the full transition to the **React frontend** and the successful extraction logic for **EaseMyTrip**. The frontend correctly identifies records scraped via DOM navigation (`BROWSER`) vs clean endpoints (`API`).
