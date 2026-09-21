# India Airfare Price Index

Welcome to the India Airfare Price Index! This repository contains the production data-acquisition pipeline for tracking, normalizing, and validating Indian domestic airfares.

## Features

- **Live Data Collection:** Integrates with the Ignav API to fetch real-time airfare data across multiple Indian domestic routes (e.g., DEL→BOM, DEL→BLR).
- **Robust Pipeline:** Employs a strict validation and normalization engine to ensure all incoming data conforms to a standard schema before it hits the database.
- **Relational Storage:** Backed by PostgreSQL using SQLAlchemy (async) with a clean schema for tracking Collection Runs, Jobs, and individual Fare Observations.
- **Real-time Dashboard:** A FastAPI backend paired with a vanilla JS/HTML dashboard to instantly visualize fare trends, pipeline health, and data quality metrics.

## Project Structure

- `apps/scraper/src/adapters/`: API Adapters (currently Ignav)
- `apps/scraper/src/scripts/`: Orchestration scripts (e.g., `run_ignav.py`)
- `apps/scraper/src/storage/`: Database models and SQLAlchemy config
- `apps/scraper/src/validation/`: Data normalization and quality gating
- `apps/api/src/`: FastAPI backend serving the observations
- `web/`: Frontend dashboard (HTML/CSS/JS)
- `docker-compose.yml`: Local infrastructure (PostgreSQL & Redis)

## Quick Start

1. **Start the infrastructure:**
   ```bash
   docker-compose up -d
   ```

2. **Run the data collection scraper:**
   ```bash
   # Set your IGNAV_API_KEY in .env first
   $env:PYTHONPATH="apps/scraper/src"
   python apps/scraper/src/scripts/run_ignav.py
   ```

3. **Start the API & Dashboard:**
   ```bash
   # Terminal 1: API Server
   $env:PYTHONPATH="apps/scraper/src"
   python -m uvicorn apps.api.src.main:app --port 8000
   
   # Terminal 2: Web Server
   python -m http.server 8080
   ```

Navigate to `http://localhost:8080/index.html` to see the live data dashboard!

## Branch: Prototype 2

This branch (`prototype2`) introduces the full end-to-end integration with the Ignav API, replacing mock data and fragile web scrapers with a reliable data feed. It includes full database persistence, validation gates, and a dynamic frontend showcasing real flight times and fare structures.
