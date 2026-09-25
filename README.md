# ✈️ India Airfare Price Index (APIx)

> Production-grade data acquisition, normalization, validation, and index calculation pipeline for Indian domestic airfares.

---

## 📐 System Architecture Overview

The **India Airfare Price Index (APIx)** is built as a multi-tier, decoupled data pipeline that ingests raw flight fares from multiple sources (Direct Airline APIs, Web Scrapers, OTAs), normalizes and validates data against strict quality gates, stores clean records in a relational database, and computes weighted airfare index series accessible via a FastAPI backend and interactive frontend dashboard.

```mermaid
flowchart TD
    subgraph Data Sources Layer
        A1[Ignav API Adapter]
        A2[EaseMyTrip Playwright Scraper]
        A3[IndiGo Direct Adapter]
    end

    subgraph Acquisition & Orchestration
        B1[Collection Run Orchestrator]
        B2[Raw Payloads Storage]
    end

    subgraph Validation & Normalization Engine
        C1[Schema & Quality Validator]
        C2[Fare Normalizer]
        C3[Lead Time Calculator T+1..T+45]
    end

    subgraph Persistence Layer
        D1[(PostgreSQL / SQLite Database)]
        D2[Fare Observation Records]
        D3[Quality Flags & Audit Logs]
    end

    subgraph Backend API Layer
        E1[FastAPI Server - Uvicorn]
        E2[/api/observations Endpoint]
    end

    subgraph Presentation & Dashboard Layer
        F1[Web Server - HTTP]
        F2[Vanilla JS & Chart.js Dashboard]
        F3[Interactive Weight Slider Component]
    end

    A1 -->|Raw JSON| B1
    A2 -->|DOM Extract / Capture| B1
    A3 -->|Direct Feed| B1
    B1 --> B2
    B2 --> C1
    C1 -->|Validated| C2
    C2 --> C3
    C3 -->|Structured Record| D1
    D1 --- D2
    D1 --- D3
    D1 --> E1
    E1 --> E2
    E2 -->|JSON API| F2
    F1 --> F2
    F3 --> F2
```

---

## 🧩 Core Subsystem Breakdown

### 1. Data Acquisition Layer (`apps/scraper/src/adapters`, `sources/`)
* **Ignav API Adapter (`ignav.py`):** Connects to external API endpoints for real-time fares across primary Indian trunk routes (DEL→BOM, DEL→BLR, BOM→BLR).
* **EaseMyTrip Scraper (`run_easemytrip.py`, `easemytrip.py`):** Playwright browser automation with headless chromium, intercepting network payloads and parsing DOM structures for flight times, baggage tiers, fare families, and total pricing.
* **IndiGo Adapter (`run_indigo.py`):** Direct adapter capturing airline-native pricing feeds.

### 2. Validation & Normalization Pipeline (`apps/scraper/src/validation`, `normalization/`)
* **Sanity & Quality Gating:** Filters zero-fare observations, negative taxes, invalid airport IATA codes, and extreme outlier spikes.
* **Lead Time Categorization:** Automatically maps observation timestamps against travel timestamps into standardized lead-day buckets ($T+1, T+7, T+15, T+30, T+45$).
* **Currency & Monetary Precision:** Normalizes base fares, taxes, and total pricing into `NUMERIC(10,2)` (Decimal) precision to eliminate floating-point drift.

### 3. Storage & Persistence Layer (`apps/scraper/src/storage/models.py`)
Relational PostgreSQL schema managed via async SQLAlchemy:
* **`sources`**: Metadata registry of active data sources and collection methods (API vs WEB).
* **`collection_runs` & `collection_jobs`**: Job tracking, execution timestamps, and collection status lifecycle (`IN_PROGRESS`, `COMPLETED`, `FAILED`).
* **`raw_observations`**: Unmodified JSON response payloads for auditability.
* **`fare_observations`**: Cleaned, normalized fare records containing airline, flight number, departure/arrival times, lead days, base fare, taxes, and total fare.
* **`quality_flags`**: Log entries for failed validation rules or suspicious price movements.

### 4. API Backend (`apps/api/src/main.py`)
* Built with **FastAPI** and **Uvicorn**.
* Provides CORS-enabled endpoints (`/api/observations`) fetching recent fare observations joined with collection metadata.

### 5. Web Dashboard (`web/`)
* **Tech Stack:** HTML5, Vanilla CSS3 (custom design system), JavaScript ES6+, Chart.js.
* **Views & Features:**
  * **Live Fares:** Tabular list of active fares with route filters and search.
  * **Route Analysis:** Trend charts across DEL–BOM, DEL–BLR, BOM–BLR.
  * **Interactive Weight Sliders:** Dynamically adjust lead-time weights ($T+1, T+7, T+15, T+30, T+45$) to recompute price index formulas in real-time.
  * **Source Quality Monitor:** Tracking error rates and collection freshness.

---

## 🧮 Airfare Price Index Methodology

The overall index is computed using a weighted aggregation across lead-time buckets $k \in \{T+1, T+7, T+15, T+30, T+45\}$:

$$I_t = \sum_{k} w_k \cdot \left( \frac{P_{t, k}}{P_{0, k}} \right) \times 100$$

Where:
* $P_{t, k}$ is the average fare at time $t$ for lead-time window $k$.
* $P_{0, k}$ is the base period fare reference.
* $w_k$ is the assigned weight for lead-time bucket $k$ (default: $T+1$: 15%, $T+7$: 35%, $T+15$: 25%, $T+30$: 15%, $T+45$: 10%).

---

## 📁 Repository Directory Structure

```
apix/
├── apps/
│   ├── api/
│   │   └── src/
│   │       └── main.py                 # FastAPI Backend Entrypoint
│   └── scraper/
│       └── src/
│           ├── adapters/               # Ignav API & Base Adapters
│           ├── core/                   # Shared pipeline utilities
│           ├── models/                 # Domain Enums & Schemas
│           ├── normalization/          # Data conversion & lead-time logic
│           ├── scripts/                # Scraper execution scripts
│           ├── storage/                # SQLAlchemy models & DB connection
│           └── validation/             # Sanity & quality gate checks
├── web/                                # Web Dashboard Frontend
│   ├── index.html                      # Dashboard HTML layout
│   ├── dashboard.css                   # Custom CSS design system
│   └── dashboard.js                    # Chart.js integration & API fetch
├── data/                               # Database storage directory
├── docs/                               # Architecture specs & design documents
├── start.bat                           # One-click Windows launcher script
├── docker-compose.yml                  # PostgreSQL & Redis infrastructure
├── requirements.txt                    # Python dependencies
├── config.yaml                         # Scraper & pipeline configuration
└── README.md                           # System documentation
```

---

## 🚀 Quick Start Guide

### Option 1: One-Click Launcher (Windows)
Double-click [`start.bat`](file:///c:/sih%202026/apix/start.bat) or run in terminal:
```cmd
.\start.bat
```
This script will:
1. Start the FastAPI backend on `http://127.0.0.1:8000`
2. Start the web dashboard server on `http://127.0.0.1:8080`
3. Automatically launch your default browser to `http://localhost:8080/index.html`

### Option 2: Manual Setup

1. **Start Infrastructure (Optional PostgreSQL & Redis):**
   ```bash
   docker-compose up -d
   ```

2. **Run Data Collection Scraper:**
   ```bash
   # Windows PowerShell
   $env:PYTHONPATH="apps/scraper/src"
   python apps/scraper/src/scripts/run_ignav.py
   ```

3. **Start API Backend:**
   ```bash
   $env:PYTHONPATH="apps/scraper/src"
   python -m uvicorn apps.api.src.main:app --port 8000
   ```

4. **Start Web Server:**
   ```bash
   python -m http.server 8080 --directory web
   ```
   Open `http://localhost:8080/index.html` in your browser.

---

## ⚙️ Environment Configuration (`.env`)

Create a `.env` file in the root directory (based on `.env.example`):

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:15432/airfare_index

# API Keys
IGNAV_API_KEY=your_ignav_api_key_here

# Pipeline Settings
LOG_LEVEL=INFO
COLLECTION_TIMEOUT_SECONDS=60
```
