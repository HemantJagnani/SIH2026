# India Airfare Price Index — Scraping, Normalisation & Validation Pipeline
## Detailed implementation specification for Antigravity

**Purpose:** Build the production-oriented data-acquisition pipeline for the India Airfare Price Index project. This specification covers source discovery, API-vs-web collection, source adapters, raw evidence, deterministic normalisation, Pydantic validation, AI-assisted exception resolution, data-quality monitoring, PostgreSQL storage, Airflow orchestration, testing, and source-specific implementation strategy.

**Important:** This is a statistical data-collection system, not a bot-evasion system. Use only permitted/authorized access. Do not bypass CAPTCHA, authentication, paywalls, access controls, robots exclusions, rate limits, or other technical restrictions.

---

# 1. Architecture

```text
                         AIRLINE / OTA SOURCES
                                  |
                    +-------------+-------------+
                    |                           |
              Authorized API                Web source
                    |                           |
               API Adapter               Web Collection
                    |                    +------+------+
                    |                    |             |
                    |                  HTTP        Browser
                    |                 httpx       Playwright
                    |                    |             |
                    |                  Crawlee       Crawlee
                    |                    |             |
                    +----------+---------+-------------+
                               |
                         SOURCE ADAPTER
                               |
                         RAW OBSERVATION
                               |
                  DETERMINISTIC NORMALISATION
                               |
                    +----------+-----------+
                    |                      |
                 SUCCESS                 UNKNOWN
                    |                      |
                    |                 AI EXCEPTION
                    |                   FALLBACK
                    |                      |
                    |              +-------+-------+
                    |              |               |
                    |          Candidate        Uncertain
                    |              |               |
                    |         Validate         Quarantine
                    |              |
                    +------+-------+
                           |
                      PYDANTIC SCHEMA
                       VALIDATION
                           |
                    DATA QUALITY ENGINE
                           |
             +-------------+-------------+
             |                           |
        PostgreSQL                  Object storage
       structured data           raw HTML/JSON/screenshots
             |
             v
       INDEX ENGINE
             |
             v
           API
             |
             v
        DASHBOARD

                     AIRFLOW
           schedules/orchestrates runs
```

---

# 2. Methodological principles from Eurostat

The uploaded Eurostat *Practical guidelines on web scraping for the HICP* should be treated as a key reference.

The document says, among other things:

- investigate API/direct data access before scraping because APIs can be more stable than websites;
- begin gradually and use targeted scraping before moving to bulk scraping;
- preserve collection timestamp, source, item/offer identity and metadata;
- continuously monitor the scraping process because website changes can silently damage data;
- automate checks for duplicates, suspicious values, outliers, missing/zero values and observation counts;
- document/version scrapers and make collection parameters configurable;
- treat frequency and timing as methodological choices, especially for volatile prices;
- separate data collection from index compilation.

Relevant pages: Eurostat pp. 3–8, 10–20, especially the sections on technology, sampling, validation, and index compilation. The guidance explicitly notes that transport prices can require anticipation-date treatment and that similar strategies may be needed for airfares.

---

# 3. API-first / scraping-second decision

For every source, create a `source_registry` record containing:

- source name
- source type: airline / OTA
- API availability
- API access status: public / partner / authorized / unavailable
- web collection status
- terms/robots/policy review status
- permitted collection method
- rate-limit/concurrency policy
- fare concept supported
- metadata supported
- last verification date
- source owner/contact
- adapter implementation status

Decision tree:

```text
Is an appropriate authorized API available?
        |
        +-- YES --> API adapter
        |
        +-- NO --> Is web collection permitted/authorized?
                       |
                       +-- YES --> Web adapter
                       |
                       +-- NO --> Do not collect
```

Never infer permission merely because a webpage is publicly visible.

---

# 4. Current source strategy

This is a **research snapshot** and must be re-verified before production because partner/API programs can change.

## 4.1 IndiGo

**Preferred:** official IndiGo NDC API, if authorized access is obtained.

IndiGo's developer portal documents NDC AirShopping for flight search, registration/API credentials, authentication, and production certification/approval.

Adapter:

```text
IndigoNdcAdapter
```

Flow:

```text
FareSearchRequest
    ↓
NDC authentication
    ↓
AirShopping
    ↓
NDC response
    ↓
Indigo parser
    ↓
canonical FareObservation
```

Tasks:
- authentication/token handling;
- secure secret storage;
- AirShopping request builder;
- route/date/passenger/cabin parameters;
- XML/JSON parser;
- offer/segment mapping;
- fare/tax/currency extraction;
- availability mapping;
- raw response storage;
- request/response correlation;
- retry/error handling;
- fixture and contract tests.

Do not use the public consumer webpage as a workaround for unavailable authorized NDC access.

---

## 4.2 Air India

**Preferred:** official Air India NDC, if authorized access is obtained.

Air India's NDC FAQ describes direct NDC, GDS and authorized non-GDS access and eligibility controls.

Adapter:

```text
AirIndiaNdcAdapter
```

Flow:

```text
FareSearchRequest
    ↓
Air India NDC
    ↓
AirShopping / offer response
    ↓
parser
    ↓
canonical FareObservation
```

If authorized access is unavailable, document the limitation and use another permitted source rather than bypassing access controls.

---

## 4.3 Cleartrip

**Preferred:** official Cleartrip Flight API.

Cleartrip has documented domestic flight search API endpoints, sandbox/production paths, authentication headers and fare-result documentation. Its FAQ describes total price as involving Base + Tax + Markup/service/convenience/gateway fee.

Adapter:

```text
CleartripFlightApiAdapter
```

Tasks:
- sandbox integration;
- production credentials via secrets;
- origin/destination/date;
- passenger/cabin/trip type;
- flight/segment parsing;
- base/tax/markup extraction;
- total fare;
- airline/flight number;
- availability;
- raw response storage;
- fixture tests.

Important methodology decision: explicitly define whether the project target is base fare, fare+taxes, total consumer-payable amount, or another price concept. Do not mix concepts between sources.

---

## 4.4 Yatra

**Preferred:** Yatra Air API if partner access is obtained.

Yatra's official partner/API page advertises an Air API with real-time data, GDS/LCC/NDC fares and multi-source inventory.

Adapter:

```text
YatraAirApiAdapter
```

Tasks:
- partner onboarding;
- authentication;
- search request;
- response parsing;
- fare/tax/fee extraction;
- airline/flight/segment mapping;
- availability;
- raw response storage.

Do not invent undocumented endpoints.

---

## 4.5 MakeMyTrip

Current public material found includes a myBiz Travel Request API, but that is for corporate travel-request submission and is **not a documented public flight-fare search API for this project**.

Do not classify that API as a fare-search API.

Preferred:
1. authorized partner fare API if granted;
2. otherwise permitted web collection;
3. otherwise exclude.

Adapters:

```text
MakeMyTripFlightApiAdapter   # only if authorized fare API exists
MakeMyTripWebAdapter         # only if web collection is permitted
```

---

## 4.6 Goibibo

No current public flight-fare search API was confirmed during this review.

Preferred:
1. authorized partner API if obtained;
2. permitted web collection if authorized;
3. otherwise exclude.

Adapter names:

```text
GoibiboFlightApiAdapter
GoibiboWebAdapter
```

Do not treat an undocumented internal request as an authorized API.

---

## 4.7 EaseMyTrip

Public corporate material indicates API/B2B integrations exist, but a current public fare-search API specification sufficient to implement this project was not confirmed.

Status:

```text
PARTNER_API_POSSIBLE
PUBLIC_FARE_API_NOT_CONFIRMED
```

Use `EaseMyTripFlightApiAdapter` only when partner documentation/credentials are supplied. Otherwise use a permitted web adapter or exclude.

---

## 4.8 ixigo

Corporate disclosures reference API services/backend travel-information integrations, but a current public flight-fare search API suitable for this project was not confirmed.

Status:

```text
PARTNER_API_POSSIBLE
PUBLIC_FARE_API_NOT_CONFIRMED
```

Use `IxigoFlightApiAdapter` only with authorized API documentation. Otherwise permitted web collection or exclude.

---

## 4.9 Akasa Air

Public flight search is available, but no public fare-search developer/NDC API was confirmed during this review.

Status:

```text
PUBLIC_API_NOT_CONFIRMED
```

Use `AkasaWebAdapter` only if automated web collection is permitted/authorized.

---

## 4.10 SpiceJet

The public website is JavaScript-driven and supports flight search, but no public fare-search developer/NDC API was confirmed during this review.

Status:

```text
PUBLIC_API_NOT_CONFIRMED
```

Use `SpiceJetWebAdapter` only if permitted/authorized.

---

## 4.11 Air India Express

No public fare-search API was confirmed during this review.

Status:

```text
PUBLIC_API_NOT_CONFIRMED
```

Use `AirIndiaExpressWebAdapter` only if permitted/authorized.

---

# 5. Never confuse an internal browser request with an API

A website may make an internal JSON/XHR/fetch request while a browser is open.

Do not automatically call this an API.

```text
Official/authorized API
        !=
undocumented internal website request
```

Use an internal endpoint only if the source explicitly authorizes/documentates its use for your integration.

---

# 6. Common collection request

All API and web adapters must accept the same logical request:

```yaml
request_id: UUID
source: string
origin: IATA_AIRPORT_CODE
destination: IATA_AIRPORT_CODE
travel_date: YYYY-MM-DD
lead_days: integer
trip_type: ONE_WAY | ROUND_TRIP
passenger_count:
  adults: integer
  children: integer
  infants: integer
cabin: ECONOMY
currency: INR
collection_mode: API | HTTP | BROWSER
```

Initial project defaults:

```yaml
adults: 1
children: 0
infants: 0
cabin: ECONOMY
trip_type: ONE_WAY
currency: INR
```

Keep these configurable.

---

# 7. Lead-time generation

The project currently targets:

```text
T+1
T+7
T+15
T+30
T+45
```

For collection date `D`:

```text
travel_date = D + lead_days
```

Example for 2026-09-21:

```text
T+1  -> 2026-09-22
T+7  -> 2026-09-28
T+15 -> 2026-10-06
T+30 -> 2026-10-21
T+45 -> 2026-11-05
```

These are configurable research parameters, not values to hardcode inside source adapters.

---

# 8. Route configuration

Initial POC:

```yaml
routes:
  - origin: DEL
    destination: BOM
  - origin: DEL
    destination: BLR
  - origin: BOM
    destination: BLR
```

Production route selection should eventually use documented statistical/traffic criteria such as route relevance, traffic volume, consumption relevance and data availability.

---

# 9. Source adapter interface

Conceptually:

```python
class FareSourceAdapter:
    async def collect(
        self,
        request: FareSearchRequest
    ) -> CollectionResult:
        ...
```

Adapter responsibilities:

1. receive common request;
2. communicate with source;
3. obtain raw data;
4. parse source-specific response;
5. map source fields to canonical fields;
6. return observations and collection status;
7. preserve evidence and diagnostics.

Adapter must NOT:
- calculate the index;
- apply route weights;
- calculate CPI;
- silently discard records;
- call an LLM for every observation.

---

# 10. Recommended adapter decomposition

Use:

```text
Adapter
  |
  +-- Client
  |     API / HTTP / browser
  |
  +-- Parser
  |     XML / JSON / HTML -> source model
  |
  +-- Mapper
        source model -> canonical model
```

Example:

```text
IndiGo NDC XML
    ↓
NDC parser
    ↓
Indigo source model
    ↓
canonical FareObservation
```

This isolates website/API changes.

---

# 11. Raw evidence

For every collection attempt preserve:

```yaml
collection_run_id
request_id
source
collection_timestamp
request_parameters
collection_method
source_url_or_endpoint_reference
http_status
response_time_ms
raw_evidence_uri
content_type
parser_version
adapter_version
```

Object storage should hold, as appropriate:

- raw JSON
- raw XML
- raw HTML
- screenshots for browser collection
- sanitized response metadata

PostgreSQL should hold structured operational data, not large raw payloads.

Never store secrets or unnecessary PII.

---

# 12. Collection status

Every job must have an explicit result:

```text
SUCCESS
NO_RESULTS
SOLD_OUT
NOT_FOUND
SOURCE_ERROR
TIMEOUT
RATE_LIMITED
ACCESS_RESTRICTED
CAPTCHA_PRESENT
PARSER_ERROR
VALIDATION_ERROR
NORMALIZATION_ERROR
UNKNOWN_ERROR
```

Do not turn every failure into `price = NULL`.

---

# 13. Canonical FareObservation

Minimum schema:

```yaml
observation_id: UUID

collection_run_id: UUID
source: string
source_offer_id: string | null

collected_at: datetime
travel_date: date
lead_days: integer

origin: IATA
destination: IATA

airline: string
airline_code: string | null
flight_number: string | null

trip_type: ONE_WAY | ROUND_TRIP
cabin: ECONOMY | PREMIUM_ECONOMY | BUSINESS | FIRST | UNKNOWN
passenger_count: integer

departure_time: datetime | null
arrival_time: datetime | null
stops: integer | null

fare_family: string | null
fare_class: string | null

base_fare: decimal | null
taxes: decimal | null
fees: decimal | null
discount: decimal | null
total_fare: decimal | null
currency: string

availability: AVAILABLE | SOLD_OUT | NOT_FOUND | UNKNOWN

raw_value_reference: string | null
raw_evidence_uri: string | null

adapter_version: string
normalizer_version: string
schema_version: string
```

Add fields when a source provides them.

---

# 14. Normalisation

Normalization is deterministic by default.

```text
RAW SOURCE DATA
      ↓
field extraction
      ↓
type parsing
      ↓
mapping
      ↓
canonical representation
```

Examples:

```text
"₹5,240" / "INR 5,240" / "5,240 INR"
                    ↓
              5240.00 INR
```

```text
"Indigo" / "INDIGO" / "6E"
                    ↓
                 IndiGo
```

```text
"Delhi" / "Delhi Airport" / "Indira Gandhi International"
                    ↓
                   DEL
```

```text
"One Way" / "ONEWAY" / "one-way"
                    ↓
                 ONE_WAY
```

Keep normalization separate from scraping.

---

# 15. Preserve raw + normalized values

Never overwrite the source value.

Example:

```yaml
raw_airline: "INDIGO"
normalized_airline: "IndiGo"

raw_price: "₹5,240"
normalized_price: 5240.00

raw_origin: "Delhi Airport"
normalized_origin: "DEL"
```

This is the audit trail.

---

# 16. Mapping tables

Mappings should live in configuration/database tables rather than being scattered throughout scraper code.

Example:

```yaml
airline_aliases:
  "indigo": "IndiGo"
  "INDIGO": "IndiGo"
  "6E": "IndiGo"

airport_aliases:
  "Delhi": "DEL"
  "Delhi Airport": "DEL"
  "Indira Gandhi International Airport": "DEL"
```

Production should maintain versioned mappings with:

```text
mapping_id
entity_type
source
raw_value
canonical_value
confidence
approval_status
created_at
approved_at
effective_from
effective_to
version
```

---

# 17. AI-assisted normalization fallback

AI is an exception mechanism, not the primary normalizer.

```text
Deterministic normalizer
        |
        +-- recognized -> continue
        |
        +-- unknown -> AI exception resolver
```

Example:

```text
raw airline = "6E"
rules = unknown

AI candidate:
IndiGo
confidence:
0.98
```

Do not immediately mutate the master mapping.

Use:

```text
AI candidate
    ↓
Pydantic validation
    ↓
business-rule checks
    ↓
candidate mapping
    ↓
approval policy
    ↓
permanent deterministic mapping
```

If unresolved:

```text
QUARANTINE
```

---

# 18. AI fallback guardrails

The AI resolver must:

- receive only necessary context;
- never receive credentials;
- never receive passenger PII;
- return structured JSON;
- return candidate value;
- return confidence;
- return reason;
- return `needs_review`;
- have timeout/retry limits;
- have cost/rate limits;
- log model/version;
- log prompt/template version;
- never silently rewrite historical observations.

Example response:

```json
{
  "field": "airline",
  "raw_value": "6E",
  "candidate_value": "IndiGo",
  "confidence": 0.98,
  "needs_review": false,
  "reason": "Recognized airline designator"
}
```

The AI output itself must pass Pydantic validation and business checks.

---

# 19. Pydantic validation

Pydantic is the schema/type gatekeeper.

It should validate:

- required fields;
- types;
- dates;
- decimals;
- enums;
- basic constraints.

Pipeline:

```text
Normalized candidate
       ↓
Pydantic
       |
       +-- valid --> quality checks
       |
       +-- invalid --> validation exception
```

Do not put every domain normalization rule inside Pydantic.

Keep:
- normalization = deterministic transformations;
- Pydantic = structure/types;
- quality engine = plausibility/collection health.

---

# 20. Business validation

After schema validation, apply airfare-specific rules.

### Route

```text
origin exists
destination exists
origin != destination
```

### Date

```text
travel_date >= collection_date
lead_days = travel_date - collection_date
```

### Price

```text
total_fare >= 0
```

### Passenger

```text
passenger_count >= 1
```

### Fare arithmetic

When all components exist:

```text
base_fare + taxes + fees - discount ≈ total_fare
```

Use a configured rounding tolerance.

### Availability

Never interpret sold-out as zero price.

---

# 21. Data-quality layer

Validation asks:

> Is the record structurally valid?

Quality asks:

> Does the record and the collection run look plausible?

Run-level metrics:

- total requests
- successful
- failed
- no results
- access restricted
- CAPTCHA
- observations extracted
- valid observations
- invalid observations
- normalization failures
- AI fallback count
- AI unresolved count
- duplicate count
- response-time p50/p95

Field-level metrics:

- missing rate
- unique count
- numeric rate
- min/max
- category distribution
- distribution changes

Statistical checks:

- outliers
- sudden price jumps
- zero-price records
- implausibly high fares
- abnormal route observation counts

Do not automatically delete an extreme price merely because it is extreme. Flag first.

---

# 22. Website-change detection

Maintain historical source baselines:

```text
source
run_date
requests
success_rate
observations
unique_airlines
unique_flights
missing_total_fare_pct
missing_flight_number_pct
median_fare
min_fare
max_fare
```

Examples:

```text
Previous observations: 150
Current observations: 2
=> extraction anomaly
```

```text
Previous total_fare missing: 1%
Current: 87%
=> schema/parser anomaly
```

```text
Previous airline unique count: 8
Current: 1
=> possible parser failure
```

A scraper can technically "succeed" while producing bad data. Detect both runtime failures and silent extraction failures.

---

# 23. Source health

Do not create an opaque single score. Store explicit metrics:

```yaml
success_rate
observation_yield
parser_error_rate
validation_error_rate
normalization_error_rate
response_time_p50
response_time_p95
rate_limit_count
access_restriction_count
last_success_at
last_schema_change_detected_at
```

---

# 24. Deduplication

Use levels.

### Exact technical duplicate

Same:

```text
source
request_id
source_offer_id
collected_at
```

Likely duplicate.

### Logical duplicate

Same source, route, travel date, airline, flight and fare inside a configured time window.

Flag or remove according to explicit policy.

### Cross-source duplicate

Do NOT automatically remove. The same flight/fare appearing on an airline and OTA may be legitimate observations from different channels.

---

# 25. Fare concept

The system must support:

```text
base_fare
taxes
fees
discount
total_fare
```

The methodology must explicitly choose the target price concept.

For an initial POC, one possible operational definition is:

> total consumer-facing payable one-way economy fare for one adult, excluding optional ancillary purchases.

This is a project assumption until aligned with the intended CPI methodology.

Never mix base fare from one source with total fare from another without documentation.

---

# 26. Preserve more fare metadata than the index immediately needs

Where available, capture:

```text
airline
flight_number
origin
destination
travel_date
collection_time
departure_time
arrival_time
stops
cabin
fare_family
fare_class
baggage
base_fare
taxes
fees
discount
total_fare
currency
availability
source
source_offer_id
```

Eurostat emphasizes collecting useful metadata because it helps classification, homogeneity and statistical processing.

---

# 27. HTTP vs browser

Use:

### HTTP/httpx/Crawlee HTTP

When structured data can be collected directly and permitted.

Advantages:
- faster
- cheaper
- fewer browser resources
- easier scaling

### Playwright/Crawlee Playwright

When browser execution is genuinely required.

Use it for:
- JavaScript-rendered results
- form interaction
- date picker/search flows
- dynamic result loading

Do not force Playwright onto every source.

---

# 28. Browser extraction strategy

Prefer:

1. official API;
2. permitted structured data;
3. stable semantic/accessibility attributes;
4. stable data attributes;
5. DOM relationships;
6. CSS selectors;
7. XPath only where useful.

Avoid fragile selectors based on:
- generated class names;
- deep DOM positions;
- visual styling.

---

# 29. Rate limiting

Per-source configuration:

```yaml
max_concurrency
requests_per_minute
delay_between_requests
retry_limit
backoff
```

Respect:
- API rate limits;
- website policies;
- robots exclusions where applicable;
- terms;
- contractual restrictions.

If CAPTCHA, 403, bot challenge or access restriction occurs:
- record it;
- pause/stop the relevant job;
- follow the source's permitted path.

Do not bypass it.

Do not design IP rotation as an evasion mechanism.

---

# 30. Retry strategy

Retry transient failures:

```text
timeout
temporary network error
502
503
504
```

Do not blindly retry:

```text
401
403
CAPTCHA
access denied
invalid credentials
parser failure
validation failure
```

Use exponential backoff with jitter.

---

# 31. PostgreSQL model

At minimum:

```text
sources
collection_runs
collection_jobs
raw_observations
fare_observations
entity_mappings
normalization_exceptions
validation_errors
quality_metrics
source_health
schema_versions
adapter_versions
```

Meaning:

```text
collection_jobs
    = what we intended to collect

raw_observations
    = what source returned

fare_observations
    = canonical records

quality_metrics
    = how healthy the collection was
```

---

# 32. Object storage

Suggested:

```text
/raw/{source}/{date}/{collection_run_id}/
    response_001.json
    response_002.xml
    page_001.html
    screenshot_001.png
```

Use lifecycle policies to control storage growth.

---

# 33. Airflow role

Airflow orchestrates the workflow; it should not contain individual scraping selectors.

Example DAG:

```text
daily_airfare_collection
        |
        +-- load route config
        |
        +-- generate lead-time jobs
        |
        +-- generate source jobs
        |
        +-- submit collection jobs
        |
        +-- wait for collection
        |
        +-- normalize
        |
        +-- validate
        |
        +-- quality checks
        |
        +-- publish valid observations
        |
        +-- update source health
        |
        +-- alert on anomalies
        |
        +-- trigger index pipeline
```

---

# 34. Redis role

Redis may support:
- job queues;
- short-lived coordination;
- worker state;
- caching where appropriate.

It is not the system of record.

PostgreSQL is authoritative for structured observations.

---

# 35. Crawlee role

Crawlee is the crawling-management layer:

- request queues;
- concurrency;
- retries;
- HTTP/browser crawler integration;
- crawler state.

Playwright is the browser-control layer.

They are complementary, not substitutes.

---

# 36. Observability

Every job should carry:

```text
trace_id
run_id
job_id
source
route
travel_date
lead_days
adapter_version
```

Metrics:

```text
collection_success_total
collection_failure_total
observations_extracted_total
observations_valid_total
normalization_exception_total
validation_failure_total
source_restriction_total
parser_error_total
collection_duration_seconds
```

Use structured JSON logs.

---

# 37. Testing

## Unit tests

Test:
- price parsing;
- currency;
- airport mapping;
- airline mapping;
- date/time;
- fare arithmetic;
- validation;
- deduplication.

## Fixture tests

Store sanitized source responses:

```text
fixtures/
  indigo/
  airindia/
  cleartrip/
  yatra/
  ...
```

Run parsers against fixtures without hitting websites.

## API contract tests

Use API sandbox environments where available.

## Adapter contract tests

Every adapter must produce the same canonical schema.

## Live smoke tests

Low frequency and only where permitted.

## Regression tests

When a source changes:
1. capture new fixture;
2. update parser;
3. add regression test;
4. compare quality metrics.

---

# 38. Repository structure

```text
apps/
  scraper/
    src/
      core/
        job_generator.py
        crawler_manager.py
        rate_limiter.py
        retry_policy.py

      sources/
        base.py
        indigo/
          adapter.py
          client.py
          parser.py
          mapper.py
          models.py
          fixtures/
        airindia/
          adapter.py
          client.py
          parser.py
          mapper.py
          models.py
          fixtures/
        cleartrip/
        yatra/
        makemytrip/
        goibibo/
        easemytrip/
        ixigo/
        akasa/
        spicejet/
        airindia_express/

      normalization/
        prices.py
        airports.py
        airlines.py
        dates.py
        cabins.py
        trip_types.py
        mappings.py
        ai_fallback.py

      validation/
        schemas.py
        business_rules.py
        quality_checks.py
        deduplication.py

      storage/
        postgres.py
        object_store.py

      monitoring/
        metrics.py
        alerts.py
        source_health.py

config/
  routes.yaml
  lead_times.yaml
  sources.yaml
  rate_limits.yaml
  normalization_mappings.yaml

docs/
  sources/
  decisions/
  runbooks/
  methodology/
```

---

# 39. Configuration outside code

Example:

```yaml
routes:
  - origin: DEL
    destination: BOM

lead_times: [1, 7, 15, 30, 45]

sources:
  - indigo
  - airindia
  - cleartrip
```

Do not embed routes/lead times in individual source adapters.

---

# 40. Collection lifecycle

```text
CREATED
  ↓
QUEUED
  ↓
RUNNING
  ↓
SOURCE_RESPONSE
  ↓
EXTRACTED
  ↓
NORMALIZED
  ↓
VALIDATED
  ↓
QUALITY_CHECKED
  ↓
PUBLISHED
```

Failure paths:

```text
RUNNING
  ↓
FAILED / RESTRICTED / TIMEOUT

EXTRACTED
  ↓
NORMALIZATION_EXCEPTION
  ↓
AI_FALLBACK
  ↓
RESOLVED / QUARANTINED
```

---

# 41. Quarantine

Never silently discard unusual data.

Tables:

```text
normalization_exceptions
validation_exceptions
quality_exceptions
```

Fields:

```text
exception_id
observation_id
source
field
raw_value
error_code
error_message
ai_attempted
ai_candidate
ai_confidence
resolution_status
resolved_by
resolved_at
```

Statuses:

```text
OPEN
AI_RESOLVED
MANUAL_REVIEW
APPROVED
REJECTED
IGNORED
```

---

# 42. Source-change workflow

```text
monitor detects anomaly
        ↓
stop publication from affected source
        ↓
retain raw responses
        ↓
create incident
        ↓
inspect fixture
        ↓
update adapter
        ↓
regression tests
        ↓
live smoke test if permitted
        ↓
compare quality metrics
        ↓
re-enable publication
```

Do not allow a broken parser to silently feed the index.

---

# 43. Airfare-specific quality checks

At minimum:

### Completeness
- missing fare;
- missing airline;
- missing flight number;
- missing route;
- missing travel date.

### Consistency
- origin/destination;
- lead days;
- fare arithmetic;
- currency;
- cabin;
- passenger count.

### Availability
- sold-out;
- unavailable;
- zero-price;
- search errors.

### Duplicates
- technical duplicates;
- logical duplicates;
- unexpected repeated offers.

### Plausibility
- extreme fares;
- abrupt route-level changes;
- sudden observation-count changes.

### Parser health
- number of extracted flights;
- unique airlines;
- unique flight numbers;
- percentage of records with each important field.

---

# 44. Initial implementation phases

## Phase 0 — Source feasibility

Tasks:
- create source registry;
- verify API options;
- request API/partner access;
- review source policies/terms/robots;
- define permitted collection methods;
- define fare concept;
- define routes;
- define lead times.

Deliverable:

```text
docs/source-feasibility-matrix.md
```

---

## Phase 1 — Canonical contracts

Tasks:
- FareSearchRequest;
- RawObservation;
- FareObservation;
- CollectionResult;
- status/error enums;
- schema versioning.

Do this before implementing many adapters.

---

## Phase 2 — Storage

Tasks:
- PostgreSQL schema;
- migrations;
- object storage;
- collection runs/jobs;
- raw observations;
- exceptions.

---

## Phase 3 — Deterministic normalization

Tasks:
- price parser;
- currency normalization;
- airport mapping;
- airline mapping;
- date/time;
- cabin;
- trip type;
- versioned mappings;
- raw+normalized preservation.

---

## Phase 4 — Pydantic validation

Tasks:
- canonical schema;
- field constraints;
- business validation;
- validation error reporting;
- tests.

---

## Phase 5 — AI exception resolver

Tasks:
- detect unknown mapping;
- send only necessary context;
- structured response;
- Pydantic validation of AI output;
- confidence policy;
- quarantine;
- mapping approval;
- audit log;
- budget/rate limits.

---

## Phase 6 — API adapters

Priority:

1. IndiGo NDC, if authorized;
2. Air India NDC, if authorized;
3. Cleartrip Flight API, if authorized;
4. Yatra Air API, if authorized.

Each adapter:
- client;
- authentication;
- request builder;
- parser;
- mapper;
- fixtures;
- sandbox test;
- error handling;
- metrics.

---

## Phase 7 — Web framework

Only for approved sources.

Tasks:
- Crawlee HTTP;
- Crawlee Playwright;
- rate limiting;
- browser contexts;
- evidence capture;
- parser fixtures;
- adapter tests.

---

## Phase 8 — First permitted web source

Choose one stable approved source.

Tasks:
- inspect search flow;
- determine HTTP vs browser;
- identify result structure;
- implement adapter;
- capture fixtures;
- compare with manual observation;
- validate;
- monitor.

Do not begin with ten sources simultaneously.

---

## Phase 9 — Monitoring

Tasks:
- run metrics;
- source health;
- missingness;
- unique counts;
- duplicates;
- outliers;
- extraction anomaly detection;
- alerts.

---

## Phase 10 — Airflow

Tasks:
- DAG;
- route generation;
- lead-time generation;
- source scheduling;
- retries;
- dependencies;
- quality gates;
- alerts;
- index trigger.

---

# 45. First meaningful milestone

Do NOT define success as "ten websites scraped."

First milestone:

```text
one permitted source
+
one route
+
one lead time
+
one collection run
+
raw evidence
+
canonical observation
+
normalisation
+
Pydantic validation
+
quality checks
+
PostgreSQL
+
reproducible tests
```

Example:

```text
route: DEL-BOM
lead time: T+7
passengers: 1 adult
cabin: economy
trip: one-way
```

---

# 46. Second milestone

Expand to:

```text
3 routes
×
5 lead times
×
multiple collection days
```

Then investigate:
- fare volatility;
- missing observations;
- source stability;
- lead-time patterns;
- duplicates;
- outliers;
- source differences.

Only after this should the statistical index methodology be finalized.

---

# 47. What Antigravity must NOT change without approval

Stop and ask before changing:

1. canonical FareObservation schema;
2. fare concept;
3. lead times;
4. route definitions;
5. source inclusion/exclusion;
6. normalization rules with statistical consequences;
7. automatic acceptance of AI normalization;
8. observation deletion;
9. outlier treatment;
10. index formulas;
11. access-control handling;
12. CAPTCHA handling;
13. IP rotation/evasion mechanisms;
14. use of undocumented endpoints as APIs.

---

# 48. Required documentation per source

Create:

```text
docs/sources/<source>.md
```

with:
- source description;
- API/web status;
- authorization status;
- terms/robots/policy review;
- API documentation;
- endpoints;
- authentication;
- request parameters;
- response structure;
- fare concept;
- parser rules;
- normalization mappings;
- expected fields;
- known limitations;
- rate limits;
- failure modes;
- fixtures;
- last verification date;
- adapter version.

---

# 49. Source feasibility matrix

| Source | Preferred access | Current assessment | Adapter |
|---|---|---|---|
| IndiGo | Official NDC | API available; authorization required | `IndigoNdcAdapter` |
| Air India | Official NDC | API available; eligibility/authorization required | `AirIndiaNdcAdapter` |
| Cleartrip | Flight API | API documented; credentials required | `CleartripFlightApiAdapter` |
| Yatra | Air API | Partner API advertised; access required | `YatraAirApiAdapter` |
| MakeMyTrip | Partner fare API if granted | Public travel-request API is not a fare-search API | API if granted; otherwise permitted web |
| Goibibo | Partner fare API if granted | Public fare-search API not confirmed | API if granted; otherwise permitted web |
| EaseMyTrip | Partner API if granted | API integrations exist; public fare-search docs not confirmed | API if granted; otherwise permitted web |
| ixigo | Partner API if granted | API services exist; public fare-search docs not confirmed | API if granted; otherwise permitted web |
| Akasa Air | Authorized API if available | Public fare-search API not confirmed | Permitted web only if authorized |
| SpiceJet | Authorized API if available | Public fare-search API not confirmed | Permitted web only if authorized |
| Air India Express | Authorized API if available | Public fare-search API not confirmed | Permitted web only if authorized |

This matrix is a current research snapshot and must be re-verified before production.

---

# 50. Technology stack

### Collection
- Python 3.12+
- Crawlee for Python
- Playwright
- httpx

### Parsing/validation
- Pydantic
- Parsel/lxml where useful
- Python deterministic transformation functions

### Queue/coordination
- Redis

### Storage
- PostgreSQL
- SQLAlchemy/asyncpg
- S3-compatible object storage

### Orchestration
- Apache Airflow

### Observability
- OpenTelemetry
- Prometheus
- Grafana
- structured logging
- optional Sentry

### Testing
- pytest
- Playwright tests
- API sandbox tests
- fixture/regression tests

### Development
- Docker
- Git/GitHub Actions
- Antigravity as coding agent

---

# 51. Definition of Done

The pipeline is complete when:

- [ ] source registry exists
- [ ] API-first feasibility documented
- [ ] authorized collection method documented
- [ ] common FareSearchRequest exists
- [ ] common FareObservation exists
- [ ] raw evidence retained
- [ ] adapter interface exists
- [ ] deterministic normalization exists
- [ ] mappings are versioned
- [ ] Pydantic validation exists
- [ ] business validation exists
- [ ] quality checks exist
- [ ] quarantine exists
- [ ] AI fallback is exception-only
- [ ] AI responses are validated
- [ ] source health monitoring exists
- [ ] extraction anomaly detection exists
- [ ] duplicate detection exists
- [ ] rate limiting exists
- [ ] retry policy exists
- [ ] access restrictions stop relevant jobs
- [ ] no security-control bypass exists
- [ ] PostgreSQL persistence exists
- [ ] raw object storage exists
- [ ] fixture tests exist
- [ ] regression tests exist
- [ ] Airflow orchestration exists
- [ ] logs/metrics exist
- [ ] source documentation exists
- [ ] every enabled production source has a current verification date

---

# 52. Final mental model

```text
SOURCE DISCOVERY
      ↓
API available + authorized?
   /              \
 YES              NO
  ↓                ↓
API Adapter     permitted web?
                   /    \
                 YES     NO
                  ↓       ↓
             Web Adapter  exclude
                  ↓
             RAW RESPONSE
                  ↓
            SOURCE ADAPTER
                  ↓
         DETERMINISTIC NORMALIZER
                  |
          +-------+-------+
          |               |
       success          unknown
          |               |
          |          AI exception
          |               |
          |       candidate/review
          |               |
          +-------+-------+
                  ↓
             PYDANTIC
              VALIDATION
                  ↓
          BUSINESS VALIDATION
                  ↓
             DATA QUALITY
                  ↓
        +---------+---------+
        |                   |
     ACCEPT              QUARANTINE
        ↓
   POSTGRESQL
        ↓
   INDEX ENGINE
        ↓
      API
        ↓
   DASHBOARD

AIRFLOW = orchestration
CRAWLEE = crawl/job management
PLAYWRIGHT = browser automation
HTTPX = direct HTTP
REDIS = queue/coordination
POSTGRESQL = structured source of truth
OBJECT STORAGE = raw evidence
PYDANTIC = schema/type validation
NORMALIZER = deterministic standardisation
AI = controlled exception resolver
```

**Core principle:** The scraper collects; the source adapter interprets the source; the normalizer standardizes representations; Pydantic validates structure; the quality engine checks plausibility and collection health; PostgreSQL stores canonical data; Airflow orchestrates; the statistical engine decides how observations contribute to the airfare index.
