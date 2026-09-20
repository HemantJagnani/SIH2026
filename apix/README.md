# APIx - India Domestic Airfare Price Index

APIx is a highly robust, full-stack application designed to monitor and index domestic airfare prices in India. Built as a prototype for SIH 2026, the platform aggregates, cleans, and standardizes flight fare data across major routes to produce a single, unified inflation index (APIx) similar to consumer price indices.

## Core Features

- **Automated Data Pipeline**: Ingests, cleans, and structures raw flight data.
- **Outlier & Anomaly Detection**: Automatically flags missing data, sold-out flights, duplicates, and statistical outliers (fares outside 3 standard deviations of a route's 30-day median).
- **Intelligent Indexing**: Computes an aggregate airfare index by weighting prices across different lead times (T+1, T+7, T+30) and traffic volumes (DGCA data) for specific routes.
- **Premium Dashboard**: A clean, modern light-theme Next.js frontend built with TailwindCSS, Recharts, and Glassmorphism design principles. Includes detailed route breakdowns and data quality health metrics.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.13)
- **Database**: PostgreSQL (managed via SQLAlchemy & Alembic)
- **Background Tasks**: FastAPI BackgroundTasks (Zero-dependency async processing, no Redis/Celery required)

### Frontend
- **Framework**: Next.js 14 (React)
- **Styling**: TailwindCSS
- **Data Fetching**: TanStack React Query
- **Visualization**: Recharts

## Getting Started

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- PostgreSQL (running locally on port 5433 for the prototype)

### Backend Setup
1. Navigate to the `apix/backend` directory.
2. Install dependencies globally or in a virtual environment:
   ```bash
   pip install -r requirements.txt
   ```
3. Run Alembic migrations to setup the database schema:
   ```bash
   alembic upgrade head
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup
1. Navigate to the `apix/frontend` directory.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
4. The dashboard will be available at `http://localhost:3000` (or `3001`).

## Methodology

The index is calculated using a robust, multi-step statistical methodology:
1. **Lead-Time Aggregation**: Calculates the median valid fare for specific booking horizons (T+1, T+7, T+30) and weights them equally.
2. **Route Weighting**: Determines route contribution based on DGCA traffic volumes (e.g., DEL-BOM is weighted at 50%).
3. **Index Calculation**: A weighted arithmetic mean of all route indices, compared against a fixed base period (June 1, 2026 = 100).
