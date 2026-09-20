# Airfare Price Index (APIx) — Master POC Build Specification

## 0. Purpose of this document

This document is the **master implementation specification for an AI coding agent (Antigravity)**.

The goal is to build a polished, production-oriented **Proof of Concept (POC)** for the proposed:

> **Real-time Airfare Price Index for India through Automated Web Collection of Airline and Online Travel Aggregator Prices for Augmentation of CPI**

This is **not yet the final statistical methodology** and **not the final production scraper**.

The POC must prove the complete vertical flow:

```text
Airfare observations
        ↓
Ingestion
        ↓
Raw data storage
        ↓
Validation + cleaning
        ↓
Normalisation
        ↓
Route / lead-time aggregation
        ↓
Route price relatives
        ↓
Weighted Airfare Price Index (APIx)
        ↓
Daily time series
        ↓
REST API
        ↓
Professional web dashboard
```

The POC should use **realistic synthetic/mock airfare data**, but the software architecture must be designed so that the mock ingestion layer can later be replaced by compliant airline/OTA collectors without redesigning the statistical, API, database, or frontend layers.

---

# 1. Critical instructions for Antigravity

## 1.1 Build the actual application, not a notebook-only demo

Do NOT build this as only:

- Jupyter notebooks
- a single Python script
- Streamlit
- a static HTML mockup
- hard-coded dashboard numbers

Build a real full-stack application with:

- backend API
- relational database
- ingestion pipeline
- statistical/index engine
- frontend dashboard
- tests
- Docker setup
- documentation

The POC can use synthetic data, but all calculations must be performed programmatically from stored observations.

---

## 1.2 Do not present POC assumptions as official Indian CPI methodology

This is critical.

The following values are **illustrative POC assumptions only**:

- route weights
- lead-time weights
- selected routes
- selected airlines
- base-period prices
- outlier thresholds
- aggregation choices

Every relevant place in the UI/documentation should make this clear.

Use wording such as:

> "Illustrative POC methodology — subject to validation against MoSPI, DGCA and international price-index standards."

Do NOT claim that the POC formula is the official Indian CPI formula.

The production methodology will later be aligned with:

- MoSPI CPI methodology
- DGCA traffic/route data
- international CPI/index-number standards
- airfare-specific statistical methodology
- actual consumer booking behaviour
- the final challenge specification

---

# 2. Recommended production-oriented technology stack

Use a proper modern stack because this POC is intended to evolve into the final system.

## Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui or an equivalent polished component system
- Recharts or Apache ECharts for charts
- TanStack Query for API state/data fetching
- Zod for frontend validation where useful

The frontend should be a proper responsive dashboard.

---

## Backend

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL

Use a clean service-oriented backend structure.

---

## Data/statistical processing

Prefer:

- Polars for high-performance dataframe processing
- NumPy
- SciPy where useful
- Pandas only where a specific library requires it

Keep the statistical/index engine independent from the API layer.

The index engine must be unit-testable without running the web server.

---

## Ingestion/scheduling

For the POC:

- mock/synthetic ingestion service
- deterministic data generator

Architecture should support later:

- Playwright
- Scrapy where appropriate
- scheduled collection
- source-specific adapters

For asynchronous jobs:

- Redis
- Celery

Do not implement CAPTCHA bypassing or anti-bot circumvention.

The future production collector must be compliant with source terms, robots.txt where applicable, rate limits, and other access restrictions.

---

## Infrastructure

Use:

- Docker
- Docker Compose

Local services:

```text
frontend
backend
postgres
redis
worker
```

Optionally include a scheduler/beat service if needed.

---

## Testing

Backend:

- pytest
- pytest-asyncio where required
- HTTPX/FastAPI test client

Frontend:

- Vitest
- React Testing Library

End-to-end:

- Playwright

---

## Code quality

Use:

- Ruff
- Black
- mypy where practical
- ESLint
- Prettier

---

# 3. POC scope

Keep the POC intentionally small but complete.

## Routes

Use these three routes:

```text
DEL-BOM
DEL-BLR
BOM-BLR
```

Interpretation:

- DEL = Delhi
- BOM = Mumbai
- BLR = Bengaluru

## Airlines

Use:

```text
IndiGo
Air India
```

## Lead-time windows

For the POC use:

```text
T+1
T+7
T+30
```

The eventual challenge specification includes:

```text
T+1
T+7
T+15
T+30
T+45
```

The POC architecture must support arbitrary lead-time windows so these can be added through configuration rather than code changes.

## Sources

Use synthetic source identifiers such as:

```text
airline_direct
ota_mock
```

Do not scrape live airline/OTA websites for this POC.

The ingestion architecture must nevertheless use a source-adapter interface so real collectors can be plugged in later.

---

# 4. POC statistical assumptions

## 4.1 Price concept

For this POC:

> Use the **total consumer-facing payable fare** as the primary price.

Store separately:

- base fare
- taxes
- airport/UDF-type charges
- convenience fee
- total fare

The index uses:

```text
total_fare
```

The UI should allow the user to inspect the components.

---

## 4.2 Passenger assumptions

For every POC observation:

```text
1 adult
1 one-way ticket
economy class
domestic route
INR
```

These must be explicit fields/configuration, not hidden assumptions.

---

## 4.3 Base period

Use the first POC date as the base period.

For example:

```text
2026-09-01
```

Set:

```text
APIx(base) = 100
```

The actual date can be configured.

---

## 4.4 Illustrative route weights

Use:

| Route | Weight |
|---|---:|
| DEL-BOM | 0.50 |
| DEL-BLR | 0.30 |
| BOM-BLR | 0.20 |

Validation:

```text
0.50 + 0.30 + 0.20 = 1.00
```

These are NOT official weights.

Display:

> "Illustrative POC weights."

The production system must later replace them with documented DGCA/challenge-specified weights.

---

## 4.5 Illustrative lead-time weights

For the POC:

| Lead time | Weight |
|---|---:|
| T+1 | 1/3 |
| T+7 | 1/3 |
| T+30 | 1/3 |

These are also illustrative.

Make them configuration-driven.

---

# 5. POC index methodology

The goal is to make the mathematical chain transparent.

## Step 1 — Observation

Each observation contains:

```text
observation
    source
    airline
    origin
    destination
    search_timestamp
    travel_date
    lead_days
    fare_class
    base_fare
    taxes
    airport_charges
    convenience_fee
    total_fare
    availability
```

---

## Step 2 — Data cleaning

For the POC:

### Invalid observations

Reject/flag records when:

- total fare is negative
- currency is not INR
- origin/destination is missing
- travel date is invalid
- lead_days is inconsistent
- fare class is outside scope
- availability is sold_out with a non-null price, unless source semantics explicitly allow it

---

## Step 3 — Duplicate handling

Define a canonical observation key approximately as:

```text
source
airline
origin
destination
travel_date
lead_days
fare_class
```

The implementation must also preserve the raw observation ID.

Do not blindly treat all cross-OTA observations as duplicates in the production methodology.

For the POC, duplicate synthetic records may be removed using the canonical key plus source-specific rules.

---

## Step 4 — Outlier detection

For the POC, implement a transparent robust rule.

For each:

```text
date + route + lead_days
```

calculate the median valid fare.

Flag an observation as a potential outlier if:

```text
price > 3 × group median
```

Do not silently delete outliers.

Store:

```text
outlier_flag
outlier_reason
```

and preserve the raw record.

This is a POC quality-control rule, NOT an official statistical standard.

---

# 6. Route-level price calculation

For each:

```text
date + route + lead_days
```

calculate the median valid total fare.

Example:

```text
DEL-BOM
T+30

IndiGo = 4900
Air India = 5100
```

Median:

```text
5000
```

If there are more observations:

```text
4900
5000
5100
```

median =:

```text
5000
```

If all observations are unavailable, return a missing value rather than zero.

---

# 7. Combine lead-time windows

For the POC:

```text
Route price =
sum(
    lead_time_weight × lead_time_median_price
)
```

Because each lead-time weight is 1/3:

```text
Route price =
(T+1 price + T+7 price + T+30 price) / 3
```

Example:

```text
DEL-BOM

T+1  = ₹8,500
T+7  = ₹6,250
T+30 = ₹5,000
```

Therefore:

```text
Route price =
(8500 + 6250 + 5000) / 3

= ₹6,583.33
```

---

# 8. Base-period route prices

For the POC, configure these illustrative base prices:

| Route | Base price |
|---|---:|
| DEL-BOM | ₹6,000 |
| DEL-BLR | ₹5,500 |
| BOM-BLR | ₹5,000 |

These produce:

```text
DEL-BOM base index = 100
DEL-BLR base index = 100
BOM-BLR base index = 100
```

The actual production system should calculate/define base-period values according to the finalized methodology rather than hard-code them.

---

# 9. Route index formula

For route r on date t:

```text
RouteIndex(r,t)
=
(CurrentRoutePrice(r,t) / BaseRoutePrice(r))
× 100
```

Example:

```text
Current DEL-BOM price = ₹6,583.33
Base DEL-BOM price    = ₹6,000
```

Therefore:

```text
RouteIndex
=
6583.33 / 6000 × 100

= 109.72
```

---

# 10. Overall APIx formula

For the POC:

```text
APIx(t)
=
Σ [
    route_weight(r)
    × RouteIndex(r,t)
]
```

For our three routes:

```text
APIx
=
0.50 × DEL-BOM index
+
0.30 × DEL-BLR index
+
0.20 × BOM-BLR index
```

Example:

```text
DEL-BOM = 109.72
DEL-BLR = 112.42
BOM-BLR = 105.00
```

Calculation:

```text
0.50 × 109.72 = 54.86
0.30 × 112.42 = 33.726
0.20 × 105.00 = 21.00

APIx = 109.586

Rounded:
APIx = 109.59
```

---

# 11. Daily percentage change

For date t:

```text
DailyChangePct
=
(
APIx(t) - APIx(t-1)
)
/
APIx(t-1)
× 100
```

Example:

```text
Yesterday = 109.59
Today     = 114.33
```

Therefore:

```text
(114.33 - 109.59) / 109.59 × 100
= 4.33%
```

---

# 12. Monthly aggregation

For the POC, calculate the monthly APIx as:

```text
mean of valid daily APIx observations
```

Clearly label this as a POC aggregation rule.

Example:

```text
September daily APIx average = 116.20
```

If August = 112.00:

```text
MoM =
(116.20 - 112.00) / 112.00 × 100
= 3.75%
```

---

# 13. Year-on-year calculation

If:

```text
September 2025 = 104.00
September 2026 = 116.20
```

then:

```text
YoY =
(116.20 - 104.00) / 104.00 × 100
= 11.73%
```

---

# 14. Synthetic dataset requirements

Generate at least:

```text
10–30 days
3 routes
2 airlines
3 lead times
```

This should produce enough observations for a meaningful time series.

Target approximately:

```text
10 days × 3 routes × 2 airlines × 3 lead times
= 180 base observations
```

Add synthetic OTA observations if useful.

Include realistic patterns:

### T+1

Generally expensive.

### T+7

Moderately expensive.

### T+30

Generally cheaper.

But do NOT make prices perfectly monotonic every day. Introduce realistic volatility.

Example:

```text
DEL-BOM
T+1:  ₹7,800–₹10,500
T+7:  ₹5,800–₹7,500
T+30: ₹4,500–₹5,800
```

These ranges are examples, not real market statistics.

---

# 15. Synthetic anomalies to include

The dataset must intentionally contain:

1. At least 2 duplicate observations.
2. At least 3 missing prices.
3. At least 2 sold-out observations.
4. At least 2 extreme/outlier observations.
5. At least 1 source-specific price difference.
6. At least 1 day with a noticeable airfare surge.
7. At least 1 day with a price decline.

The dashboard should expose data-quality statistics.

---

# 16. Database design

Use PostgreSQL.

Suggested tables:

## `routes`

```text
id
origin
destination
route_code
weight
active
created_at
updated_at
```

---

## `airlines`

```text
id
name
code
active
created_at
```

---

## `sources`

```text
id
name
source_type
active
created_at
```

Examples:

```text
IndiGo Direct
Air India Direct
Mock OTA
```

---

## `fare_observations`

Fields:

```text
id
source_id
airline_id
route_id
search_timestamp
travel_date
lead_days
fare_class
passenger_count
base_fare
taxes
airport_charges
convenience_fee
total_fare
currency
availability
raw_payload
quality_status
outlier_flag
outlier_reason
duplicate_group_id
created_at
```

`raw_payload` may be JSONB.

---

## `route_daily_prices`

```text
id
date
route_id
lead_days
representative_price
observation_count
valid_observation_count
missing_count
outlier_count
created_at
```

---

## `route_indices`

```text
id
date
route_id
base_price
current_price
route_index
route_weight
contribution
created_at
```

---

## `airfare_indices`

```text
id
date
index_value
daily_change_pct
weekly_change_pct
monthly_change_pct
observation_count
coverage_pct
created_at
```

---

# 17. Backend architecture

Use:

```text
backend/
    app/
        main.py
        core/
            config.py
            logging.py
        db/
            session.py
            models/
        schemas/
        api/
            routes/
            observations/
            indices/
            health.py
        services/
            ingestion/
            cleaning/
            aggregation/
            index_engine/
            analytics/
        repositories/
        workers/
        tests/
```

Keep business logic out of FastAPI route handlers.

For example:

```text
API route
    ↓
service
    ↓
repository
    ↓
database
```

---

# 18. Index engine architecture

The index engine should be a standalone Python module.

Suggested interface:

```python
calculate_route_price(
    observations,
    lead_time_weights
)

calculate_route_index(
    current_price,
    base_price
)

calculate_airfare_index(
    route_indices,
    route_weights
)

calculate_daily_change(
    current_index,
    previous_index
)
```

These functions must be deterministic and independently unit tested.

---

# 19. API endpoints

Implement at least:

## Health

```http
GET /api/v1/health
```

---

## Current index

```http
GET /api/v1/index/current
```

Response:

```json
{
  "date": "2026-09-20",
  "index": 114.33,
  "daily_change_pct": 4.33
}
```

---

## Index history

```http
GET /api/v1/index/history?start_date=2026-09-01&end_date=2026-09-20
```

Return:

```json
{
  "data": [
    {
      "date": "2026-09-01",
      "index": 100.0
    }
  ]
}
```

---

## Route indices

```http
GET /api/v1/routes
```

---

## Individual route

```http
GET /api/v1/routes/DEL-BOM
```

Return:

- current route index
- base price
- current price
- weight
- lead-time prices
- historical route index

---

## Observations

```http
GET /api/v1/observations
```

Support filters:

```text
date
route
airline
source
lead_days
availability
quality_status
```

---

## Data quality

```http
GET /api/v1/data-quality
```

Return:

- total observations
- valid
- invalid
- missing
- sold out
- outliers
- duplicates
- coverage %

---

# 20. Frontend dashboard

The frontend should look like a professional analytics product.

## Overall visual style

Use:

- clean light theme
- professional government/statistics dashboard aesthetic
- restrained colors
- clear typography
- responsive layout
- accessible charts
- no excessive animations

Do not make it look like a generic SaaS landing page.

---

# 21. Dashboard layout

## Header

Title:

> India Airfare Price Index

Subtitle:

> Real-time experimental airfare price monitoring and index analytics

Include a badge:

> POC — Illustrative Methodology

---

## KPI cards

Display:

### Current APIx

Example:

```text
114.33
```

### Daily change

```text
+4.33%
```

### Monthly change

```text
+3.75%
```

### YoY change

```text
+11.73%
```

---

# 22. Main trend chart

Large line chart:

```text
Airfare Price Index — Daily
```

X axis:

```text
Date
```

Y axis:

```text
Index
```

Base line:

```text
100
```

Hover tooltip:

```text
Date
APIx
Daily change
```

---

# 23. Route heatmap/table

Show:

| Route | Index | Weight | Contribution | Change |
|---|---:|---:|---:|---:|
| DEL-BOM | 115.00 | 50% | 57.50 | +5.0% |
| DEL-BLR | 116.97 | 30% | 35.09 | +4.1% |
| BOM-BLR | 108.67 | 20% | 21.73 | +3.5% |

Use conditional formatting carefully.

Do not imply official weights.

---

# 24. Route drill-down

Provide route selector.

Example:

```text
DEL-BOM
```

Then show:

```text
Current route index
Current representative price
Base price
Route weight
```

and a historical chart.

---

# 25. Lead-time analysis

For selected route:

```text
T+1
T+7
T+30
```

Show:

- median fare
- observation count
- change from previous day

Graph:

```text
Lead time vs fare
```

Use a line chart.

---

# 26. Data quality panel

Display:

```text
Total observations     180
Valid                  170
Missing                  3
Sold out                 4
Outliers                 2
Duplicates               1
Coverage               94.4%
```

Clicking a metric should filter the observations table.

---

# 27. Observation explorer

Build a table with:

```text
Date
Source
Airline
Route
Lead time
Base fare
Taxes
Fees
Total
Availability
Quality status
Outlier flag
```

Add filters.

This demonstrates that the index is traceable back to source observations.

---

# 28. Methodology panel

The dashboard must contain a visible methodology section.

Explain:

```text
Base period:
POC first observation date

Price concept:
Total payable one-way economy fare

Routes:
3 illustrative routes

Lead-time windows:
T+1, T+7, T+30

Lead-time weights:
Equal for POC

Route weights:
Illustrative 50/30/20

Aggregation:
Median at route/lead-time level

Index:
Weighted arithmetic aggregation of route price relatives

Status:
Experimental POC
```

This is important for transparency.

---

# 29. POC architecture for future live scraping

Create an ingestion interface such as:

```python
class FareSourceAdapter(Protocol):
    async def collect(
        self,
        route: Route,
        travel_date: date,
        passengers: int,
        cabin: str,
    ) -> list[FareObservation]:
        ...
```

Then implement:

```text
MockFareSourceAdapter
```

for the POC.

Later:

```text
IndigoAdapter
AirIndiaAdapter
OTAAdapter
...
```

can implement the same interface.

Do NOT implement security bypasses.

---

# 30. Mock ingestion should behave like a real collector

Do not simply load the CSV directly into the database from the dashboard.

Create a proper ingestion flow:

```text
POST /api/v1/ingestion/run
        ↓
mock source adapter
        ↓
raw observations
        ↓
validation
        ↓
cleaning
        ↓
database
        ↓
index recalculation
```

This makes the architecture credible.

---

# 31. Job processing

Use Redis + Celery for the architecture.

Jobs:

```text
generate_mock_observations
clean_observations
calculate_route_prices
calculate_route_indices
calculate_airfare_index
```

For the POC, jobs may run sequentially.

But keep them as independently callable tasks.

---

# 32. Reproducibility

The synthetic data generator must use a fixed random seed.

Example:

```text
seed = 42
```

This ensures that:

> The same input configuration produces the same POC results.

This is important for testing and demos.

---

# 33. Testing requirements

At minimum:

## Unit tests

Test:

1. route weights sum to 1
2. lead-time weights sum to 1
3. median aggregation
4. outlier detection
5. missing-price handling
6. route index formula
7. overall APIx formula
8. daily change
9. monthly change
10. base-period behaviour

---

# 34. Golden calculation test

Create a test with known values.

Input:

```text
DEL-BOM = 109.72
DEL-BLR = 112.42
BOM-BLR = 105.00

weights:
0.50
0.30
0.20
```

Expected:

```text
109.586
```

Rounded:

```text
109.59
```

The test should assert this.

This guarantees that future refactoring does not silently break the index.

---

# 35. Integration tests

Test:

```text
mock ingestion
    ↓
database
    ↓
cleaning
    ↓
index engine
    ↓
API endpoint
```

Verify that `/api/v1/index/current` returns the expected index.

---

# 36. Frontend tests

Test that:

- dashboard loads
- APIx is rendered
- route selector works
- historical chart receives data
- methodology section is visible
- data-quality panel renders
- observation filters work

---

# 37. End-to-end test

Use Playwright.

Scenario:

```text
Open dashboard
    ↓
Verify APIx card
    ↓
Select DEL-BOM
    ↓
Verify route data
    ↓
Open observations
    ↓
Filter T+30
    ↓
Verify records
```

---

# 38. Docker setup

Create:

```text
docker-compose.yml
```

Services:

```text
frontend
backend
postgres
redis
worker
```

The project should start with something conceptually equivalent to:

```bash
docker compose up --build
```

The README must document exact commands.

---

# 39. Environment variables

Create:

```text
.env.example
```

Include:

```text
DATABASE_URL=
REDIS_URL=
API_BASE_URL=
NEXT_PUBLIC_API_BASE_URL=
APP_ENV=
LOG_LEVEL=
```

Never commit secrets.

---

# 40. Logging

Backend logs should include:

```text
ingestion started
observations collected
observations rejected
outliers detected
index calculation started
index calculation completed
```

Use structured logging where practical.

---

# 41. Error handling

The API should return consistent errors.

Example:

```json
{
  "error": {
    "code": "ROUTE_NOT_FOUND",
    "message": "Route DEL-XYZ does not exist."
  }
}
```

Do not expose stack traces to the frontend.

---

# 42. Important data-quality design principle

Never destroy raw observations.

Use:

```text
raw observation
      ↓
quality assessment
      ↓
analytical observation
```

Keep:

```text
raw_payload
quality_status
outlier_flag
outlier_reason
```

This is essential for statistical auditability.

---

# 43. README requirements

Create a high-quality root `README.md`.

It must contain:

## Project title

> India Airfare Price Index — APIx

## Problem statement

Explain the motivation in simple language.

## POC disclaimer

Clearly state that:

- the POC uses synthetic data
- weights are illustrative
- methodology is experimental
- it is not an official CPI index
- final methodology requires validation against MoSPI/DGCA/international standards

## Architecture

Include a Mermaid architecture diagram.

## Technology stack

Explain:

- Next.js
- FastAPI
- PostgreSQL
- Redis
- Celery
- Playwright-ready ingestion architecture
- Docker
- testing tools

## Data flow

Explain the full pipeline.

## Mathematical methodology

Document every formula.

## POC assumptions

Use a table.

## Database schema

Explain the main tables.

## API documentation

List endpoints with examples.

## Frontend

Explain dashboard pages/components.

## Running locally

Give exact commands.

## Docker

Give exact commands.

## Testing

Give commands.

## Project structure

Explain directories.

## Synthetic data generation

Explain how it works.

## Future production roadmap

Include:

```text
POC
 ↓
Real source adapters
 ↓
DGCA route basket
 ↓
Official methodology alignment
 ↓
More airlines/OTAs
 ↓
30+ day historical validation
 ↓
Production deployment
```

## Statistical methodology references

Include official/reputable references such as:

- MoSPI CPI methodology
- DGCA traffic data
- ILO/IMF/OECD/UN CPI Manual
- Eurostat HICP Methodological Manual
- Eurostat web-scraping guidance

Do not claim these sources prescribe the exact POC methodology unless they actually do.

---

# 44. README should include an example calculation

Include this exact illustrative example:

```text
DEL-BOM current representative price = ₹6,583.33
DEL-BOM base price = ₹6,000

Route index:
6583.33 / 6000 × 100
= 109.72
```

Then:

```text
DEL-BOM = 109.72, weight 0.50
DEL-BLR = 112.42, weight 0.30
BOM-BLR = 105.00, weight 0.20

APIx:
0.50(109.72)
+ 0.30(112.42)
+ 0.20(105.00)

= 109.586
≈ 109.59
```

---

# 45. README should include screenshots

After implementing the frontend, capture screenshots of:

1. Overview dashboard
2. Route analysis
3. Lead-time analysis
4. Observation explorer
5. Data quality

Add them to the README if practical.

---

# 46. README should explain what is NOT implemented yet

Be explicit:

```text
Not yet implemented:
- live airline/OTA scraping
- production source authentication
- CAPTCHA handling
- source-specific parsing
- official DGCA weights
- final MoSPI-compatible methodology
- production CPI integration
- official validation
```

Do not hide limitations.

---

# 47. Future scraping architecture

The final production design should look like:

```text
                SOURCE ADAPTERS
        ┌──────────┼──────────┐
        ↓          ↓          ↓
    Airline A  Airline B   OTA A
        │          │          │
        └──────────┼──────────┘
                   ↓
             Adapter Layer
                   ↓
             Raw Observation
                   ↓
             Validation
                   ↓
             Normalisation
                   ↓
             Deduplication
                   ↓
             Quality Engine
                   ↓
             Index Engine
```

Every source adapter should be isolated so a website change does not break the entire system.

---

# 48. Do not implement anti-bot bypassing

The challenge may mention CAPTCHAs, IP rotation and anti-bot measures.

For this POC:

- do not bypass CAPTCHAs
- do not circumvent access controls
- do not implement credential/session theft
- do not use stealth techniques intended to defeat security controls

Instead, implement an explicit source status:

```text
AVAILABLE
RATE_LIMITED
BLOCKED
SOURCE_UNAVAILABLE
```

The production system can use permitted APIs or compliant collection mechanisms where available.

---

# 49. Future statistical methodology layer

Do not hard-code the assumption that the POC methodology is final.

Design configuration such as:

```yaml
index_method:
  route_aggregation: median
  lead_time_weights:
    1: 0.333333
    7: 0.333333
    30: 0.333333
  route_weights:
    DEL-BOM: 0.50
    DEL-BLR: 0.30
    BOM-BLR: 0.20
```

This makes it easy to replace the methodology later.

---

# 50. Production methodology roadmap

After the POC, investigate and document:

1. MoSPI CPI methodology
2. current CPI revision methodology
3. DGCA passenger traffic by route
4. official route weights
5. actual booking-window distribution
6. fare-class treatment
7. flight substitution
8. new/removed flights
9. missing prices
10. sold-out flights
11. quality adjustment
12. elementary index formula
13. fixed-base vs chain-linked approach
14. annual weight updates
15. seasonal effects
16. source coverage
17. OTA duplication
18. validation against DGCA/reference data
19. revision policy
20. statistical quality metrics

The POC should make these future changes possible without rewriting the application.

---

# 51. Suggested project milestones

## Milestone 1 — Skeleton

Create:

```text
frontend
backend
database
redis
worker
docker
```

Verify everything starts.

---

## Milestone 2 — Data

Implement:

```text
synthetic data generator
database models
seed command
```

---

## Milestone 3 — Cleaning

Implement:

```text
validation
normalisation
duplicates
outliers
availability
quality status
```

---

## Milestone 4 — Index engine

Implement:

```text
lead-time aggregation
route prices
route indices
APIx
daily changes
monthly changes
```

---

## Milestone 5 — API

Implement all REST endpoints.

---

## Milestone 6 — Dashboard

Build:

```text
Overview
Route analysis
Lead-time analysis
Observation explorer
Data quality
Methodology
```

---

## Milestone 7 — Testing

Implement unit/integration/E2E tests.

---

## Milestone 8 — Documentation

Write polished README and methodology notes.

---

# 52. Definition of done for the POC

The POC is complete only when:

- [ ] `docker compose up --build` works
- [ ] database migrations work
- [ ] synthetic data can be generated
- [ ] observations are persisted
- [ ] cleaning pipeline runs
- [ ] outliers are flagged
- [ ] sold-out records are handled
- [ ] duplicates are handled
- [ ] route prices are calculated
- [ ] route indices are calculated
- [ ] APIx is calculated
- [ ] historical APIx series exists
- [ ] API endpoints work
- [ ] frontend dashboard works
- [ ] route drill-down works
- [ ] lead-time chart works
- [ ] data-quality metrics work
- [ ] methodology disclaimer is visible
- [ ] unit tests pass
- [ ] integration tests pass
- [ ] README is complete
- [ ] no official/statistical claims are made for illustrative POC assumptions

---

# 53. Expected final user experience

When a mentor opens the application, they should immediately see:

```text
INDIA AIRFARE PRICE INDEX
Experimental POC

APIx
114.33

Daily Change
+4.33%

Monthly Change
+3.75%

YoY
+11.73%

-------------------------------------

Airfare Index Trend

[interactive line chart]

-------------------------------------

Route Analysis

DEL-BOM     115.00
DEL-BLR     116.97
BOM-BLR     108.67

-------------------------------------

Lead-Time Pricing

T+1    ₹9,000
T+7    ₹6,500
T+30   ₹5,200

-------------------------------------

Data Quality

180 observations
170 valid
3 missing
4 sold out
2 outliers
1 duplicate

-------------------------------------

Methodology

Illustrative POC methodology.
Not an official CPI index.
```

The exact values will be generated by the application and must not be hard-coded into the frontend.

---

# 54. Mentor demo flow

The application should support this 5-minute demo:

### Step 1

Show the overview dashboard.

Explain:

> "This is the experimental Airfare Price Index."

### Step 2

Show the time-series chart.

Explain:

> "The index is generated from daily airfare observations."

### Step 3

Select `DEL-BOM`.

Explain:

> "We can drill down from the national index to the route."

### Step 4

Show T+1/T+7/T+30.

Explain:

> "This captures the lead-time dimension of dynamic airfare pricing."

### Step 5

Open observation explorer.

Show:

> "Every index value is traceable to underlying observations."

### Step 6

Show the calculation/methodology.

Explain:

> "For the POC, these weights and aggregation rules are illustrative. The production methodology will be aligned with official statistical standards."

### Step 7

Show API response.

Explain:

> "The same index can be consumed programmatically by downstream government analytics systems."

---

# 55. Important engineering principles

## Principle 1 — Configuration over hard-coding

Routes, weights and lead times must be configurable.

## Principle 2 — Raw data is immutable

Never destroy original observations.

## Principle 3 — Statistical calculations are isolated

The index engine must not depend on FastAPI or React.

## Principle 4 — Every derived number must be traceable

APIx → route contribution → route price → observations.

## Principle 5 — POC assumptions must be visible

Never hide assumptions.

## Principle 6 — Production architecture, POC data

Use a production-quality stack while keeping data synthetic.

## Principle 7 — No fake "live scraping"

The UI should explicitly say the current data is synthetic/mock POC data.

---

# 56. Deliverables

Antigravity must produce:

```text
1. Working full-stack application
2. Docker Compose setup
3. PostgreSQL schema/migrations
4. Synthetic data generator
5. Cleaning pipeline
6. Index engine
7. FastAPI REST API
8. Next.js dashboard
9. Automated tests
10. README.md
11. .env.example
12. Architecture documentation
13. Methodology documentation
14. API examples
15. Sample screenshots
```

---

# 57. Final instruction to Antigravity

Build this as a **serious statistical-data product POC**, not as a toy dashboard.

Prioritise:

1. correctness of calculations
2. traceability of data
3. clean architecture
4. professional UX
5. reproducibility
6. documentation
7. extensibility toward real airline/OTA data

Do not spend disproportionate time implementing live scraping in the POC.

The most important demonstration is:

```text
OBSERVATION
    ↓
QUALITY CONTROL
    ↓
REPRESENTATIVE ROUTE PRICE
    ↓
ROUTE PRICE RELATIVE
    ↓
WEIGHTED APIx
    ↓
TIME SERIES
    ↓
API
    ↓
DASHBOARD
```

The POC must make this pipeline visible and understandable to a non-technical mentor.

