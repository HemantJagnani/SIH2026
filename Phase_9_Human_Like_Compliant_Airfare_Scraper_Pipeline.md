# Phase 9 — Human-Like, JavaScript-Capable, CAPTCHA-Respecting Airfare Scraper

## Objective

Build a zero-license-cost airfare collection engine that:

- uses a real browser for JavaScript-rendered airline/OTA pages;
- follows the normal public search journey;
- maintains coherent browser sessions, cookies and local storage;
- supports optional approved proxy pools and session-to-proxy affinity;
- detects CAPTCHA, 403, 429, blocking and access restrictions;
- never solves CAPTCHA or bypasses authentication/access controls;
- stores raw evidence and normalized fare observations;
- feeds the existing PostgreSQL/APIx/dashboard pipeline;
- can combine web-scraped sources with Ignav/API sources.

## Important expectation

No open-source framework can guarantee that a site will never identify automation. The practical target is a normal browser workflow, conservative traffic, coherent sessions, condition-based waiting and safe handling of access restrictions.

## Free stack

- Python 3.12+
- Crawlee for Python 1.10.x
- Playwright
- Playwright-managed Chromium
- httpx/aiohttp
- Parsel or BeautifulSoup
- Pydantic v2
- SQLAlchemy 2
- PostgreSQL
- Redis
- MinIO (optional local S3-compatible raw storage)
- APScheduler/cron for POC
- pytest/pytest-asyncio
- Docker Compose

Optional later: Airflow, Prometheus/Grafana, OpenTelemetry, Sentry.

## Architecture

```text
Scheduler
   |
   v
Search Job Generator
   |
   v
Request Queue
   |
   +------------------+-------------------+
   |                  |                   |
   v                  v                   v
Ignav/API         HTTP Collector     Browser Collector
                                       Crawlee + Playwright
                                             |
                                    +--------+--------+
                                    |        |        |
                                    v        v        v
                               Session     Policy   Browser
                               Manager      Gate     State
                                    |        |        |
                                    +--------+--------+
                                             |
                                             v
                                       Search Workflow
                                             |
                         +-------------------+----------------+
                         |                   |                |
                         v                   v                v
                       DOM            Network responses    Page state
                         |                   |                |
                         +-------------------+----------------+
                                             |
                                             v
                                        Raw Evidence
                                             |
                                             v
                                      Source Parser
                                             |
                                             v
                                       Normalization
                                             |
                                             v
                                      Validation / QA
                                        |          |
                                        v          v
                                  PostgreSQL   Quarantine
                                        |
                                        v
                                       APIx
                                        |
                                  +-----+-----+
                                  |           |
                                  v           v
                               FastAPI    Next.js
```

## Source adapter pattern

```python
class FareSourceAdapter(Protocol):
    async def search(self, request: FareSearchRequest) -> list[FareObservation]:
        ...
```

Suggested adapters:

```text
sources/
  airlines/
    indigo/
    airindia/
    airindia_express/
    akasa/
    spicejet/
  otas/
    makemytrip/
    yatra/
    easemytrip/
    cleartrip/
    ixigo/
    goibibo/
  api/
    ignav.py
```

## Canonical request

```python
from datetime import date
from pydantic import BaseModel, Field
from typing import Literal

class FareSearchRequest(BaseModel):
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    travel_date: date
    lead_days: int
    passengers: int = Field(default=1, ge=1, le=9)
    cabin: Literal["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"] = "ECONOMY"
    trip_type: Literal["ONE_WAY", "ROUND_TRIP"] = "ONE_WAY"
    market: str = "IN"
```

## Canonical fare observation

```python
class FareObservation(BaseModel):
    collection_run_id: UUID
    source: str

    origin: str
    destination: str
    travel_date: date
    lead_days: int
    search_timestamp: datetime

    airline: str
    flight_number: str | None = None
    fare_class: str | None = None
    cabin_class: str | None = None

    departure_time_local: str | None = None
    departure_time_utc: str | None = None
    arrival_time_local: str | None = None
    arrival_time_utc: str | None = None

    stops: int | None = None

    base_fare: Decimal | None = None
    taxes: Decimal | None = None
    airport_charges: Decimal | None = None
    convenience_fee: Decimal | None = None
    total_fare: Decimal | None = None
    currency: str

    price_status: str | None = None
    requires_self_transfer: bool | None = None
    source_itinerary_id: str | None = None
    source_url: str

    availability_status: str
    raw_evidence_uri: str | None = None
```

Do not manufacture base fare/tax components when the source exposes only a total.

## State machine

```text
CREATED
 -> POLICY_CHECK
 -> OPEN_SOURCE
 -> WAIT_PAGE_READY
 -> HANDLE_CONSENT
 -> ENTER_ORIGIN
 -> ENTER_DESTINATION
 -> SELECT_DATE
 -> SELECT_PASSENGERS
 -> SUBMIT_SEARCH
 -> WAIT_RESULT_STATE
 -> EXTRACT
 -> VALIDATE
 -> PERSIST
 -> DONE
```

Failure states:

```text
ROBOTS_DISALLOWED
CAPTCHA_BLOCKED
ACCESS_BLOCKED
RATE_LIMITED
AUTH_REQUIRED
NO_RESULTS
SOLD_OUT
SEARCH_ERROR
SCHEMA_CHANGED
INVALID
```

## Browser workflow

Use a real browser and perform the public search workflow in sequence:

1. open the normal source page;
2. wait for page readiness;
3. handle consent if required;
4. enter origin;
5. enter destination;
6. choose travel date;
7. choose passenger count/cabin;
8. submit search;
9. wait for a real result-state signal;
10. capture and parse results.

Prefer semantic locators:

```python
await page.get_by_label("From").fill("DEL")
await page.get_by_label("To").fill("BOM")
await page.get_by_role("button", name="Search").click()
```

Use stable `data-testid`/ARIA selectors when labels are unavailable. Avoid brittle deep CSS chains.

Use condition-based waits rather than production sleeps.

## Human-like interaction layer

Appropriate:

- real browser execution;
- normal viewport;
- consistent locale/timezone;
- coherent cookies/local storage;
- persistent session where appropriate;
- one logical search per job;
- condition-based waits;
- low concurrency;
- conservative per-domain limits;
- normal navigation sequence;
- no unrelated background crawling.

Do not add code whose sole purpose is to defeat or hide from a protection mechanism.

## Session management

Use Crawlee `SessionPool`.

Keep the session coherent:

```text
session S1
   -> cookies
   -> local storage
   -> usage/error state
   -> optional approved proxy identity
```

Normal session expiry can create a new session.

For CAPTCHA or explicit anti-automation blocking:

```text
detect
  -> screenshot
  -> save HTML
  -> record status
  -> pause source
```

Do not automatically create a new identity solely to continue after a block.

## Persistent browser state

A source can have a persistent profile:

```text
runtime/browser_profiles/
  indigo/
  airindia/
  akasa/
```

Protect these directories and never commit them.

Example `.gitignore`:

```gitignore
runtime/browser_profiles/
storage/
.env
*.state.json
```

Playwright supports storage-state snapshots for cookies and local storage.

## Proxy/IP architecture

The code should support an optional pool of approved proxies:

```text
ProxyProvider
  -> Direct connection
  -> Institution-approved proxy A
  -> Institution-approved proxy B
  -> Future approved provider
```

Session-to-proxy affinity:

```text
S1 -> P1
S1 -> P1
S1 -> P1
```

Do not do:

```text
403 -> switch proxy -> retry -> switch proxy
```

Instead:

```text
403/CAPTCHA
  -> capture evidence
  -> mark source blocked
  -> pause source
```

A reliable free public proxy pool should not be a dependency for this project.

## Robots policy

Configure:

```python
respect_robots_txt_file=True
```

Run a project-level policy check before each source.

If the requested path is disallowed, classify it as:

```text
ROBOTS_DISALLOWED
```

and do not request it.

## CAPTCHA detection

Detect, do not solve.

```python
CAPTCHA_MARKERS = (
    "captcha",
    "verify you are human",
    "human verification",
    "security check",
    "automated queries",
)

async def captcha_present(page) -> bool:
    text = (await page.locator("body").inner_text()).lower()
    return any(m in text for m in CAPTCHA_MARKERS)
```

Also inspect source-specific semantic structures such as IDs/classes/test IDs containing `captcha`.

On detection save:

```text
screenshot
HTML
URL
timestamp
source
search parameters
status=CAPTCHA_BLOCKED
```

## HTTP status policy

| Event | Action |
|---|---|
| 200 + valid results | parse |
| 200 + no results | NO_RESULTS |
| 200 + sold out | SOLD_OUT |
| 400 | adapter/config fix |
| 401 | AUTH_REQUIRED |
| 403 | ACCESS_BLOCKED, stop source |
| 404 | possible URL change |
| 408 | bounded retry |
| 429 | backoff / honor Retry-After |
| 451 | stop |
| 5xx | bounded retry |
| CAPTCHA | stop source |
| login wall | stop source |
| unexpected page | SCHEMA_CHANGED |

## Retry policy

Retry:

- timeouts: 1–2 bounded retries;
- 5xx: bounded exponential backoff;
- 429: honor `Retry-After`; otherwise conservative backoff.

Do not automatically retry:

- 403;
- CAPTCHA;
- login/authentication wall;
- robots disallow;
- schema-change failure.

## Rate limiter

```python
class SourceRateLimiter:
    def __init__(self, min_interval_seconds: float):
        self.min_interval = min_interval_seconds
        self.next_allowed_at = 0.0

    async def wait(self):
        now = monotonic()
        if now < self.next_allowed_at:
            await asyncio.sleep(self.next_allowed_at - now)
        self.next_allowed_at = monotonic() + self.min_interval
```

Initial POC values:

```yaml
min_interval_seconds: 5
max_concurrency: 1
```

Adjust per source only after testing.

## Network-response extraction

Playwright can observe browser requests/responses. For a JS-heavy fare page, prefer a structured public response already loaded by the page over brittle DOM traversal.

Pattern:

```python
async with page.expect_response(
    lambda r: "/search" in r.url
) as response_info:
    await page.get_by_role("button", name="Search").click()

response = await response_info.value
status = response.status
content_type = response.headers.get("content-type", "")
```

Only use responses that are legitimately exposed to the public page/session. Do not use this mechanism to bypass access controls.

## Extraction priority

```text
1. Public structured JSON delivered to the browser
2. JSON-LD / structured data
3. Accessibility/semantic DOM
4. Stable data-testid / data attributes
5. Visible text / structural DOM
6. OCR only as a last resort
```

## Raw evidence

For every successful or failed run store:

```text
collection_run_id
source
source_url
timestamp
search parameters
HTTP status
browser/session ID
proxy ID if applicable
page title
HTML snapshot
relevant JSON response
screenshot
parser version
schema version
status
error reason
```

Suggested local layout:

```text
runtime/evidence/
  2026-09-22/
    source=indigo/
      run=<uuid>/
        request.json
        page.html
        result.json
        screenshot.png
        metadata.json
```

## Price normalization

Normalize airports to IATA codes.

Use `Decimal`, not float, for money.

Accept formats such as:

```text
₹ 5,499
INR 5,499
5,499
₹5,499
```

into:

```text
Decimal("5499.00")
```

For an INR index, non-INR observations should be rejected/quarantined unless an explicitly approved methodology defines currency conversion.

## Fare semantics

Record the actual components returned by the source:

```text
base fare
taxes
airport/statutory fees
convenience fee
ancillaries
total
```

Do not compare a bare base fare against an all-in consumer payable price.

## Availability states

```python
class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    NO_RESULTS = "NO_RESULTS"
    SOLD_OUT = "SOLD_OUT"
    SEARCH_ERROR = "SEARCH_ERROR"
    CAPTCHA_BLOCKED = "CAPTCHA_BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    ACCESS_BLOCKED = "ACCESS_BLOCKED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    ROBOTS_DISALLOWED = "ROBOTS_DISALLOWED"
    SCHEMA_CHANGED = "SCHEMA_CHANGED"
    INVALID = "INVALID"
```

## Validation gate

An observation enters the index dataset only when:

```text
AVAILABLE
correct origin/destination
correct travel date
correct cabin
correct passenger count
correct trip type
currency = INR
total_fare > 0
valid itinerary
```

Self-transfer inclusion should be controlled by methodology.

## Time handling

Preserve:

```text
departure_time_local
arrival_time_local
departure_time_utc
arrival_time_utc
```

Calculate lead time from dates:

```python
lead_days = (travel_date - search_date).days
```

## Deduplication

A practical key:

```text
source
origin
destination
travel_date
airline
flight_number
departure_time_utc
arrival_time_utc
cabin
fare_class
total_fare
```

Do not globally merge airline and OTA rows just because they reference the same flight.

## Outliers

Never silently delete.

Store:

```text
outlier_flag
outlier_reason
detection_method
detection_version
```

The POC may use the previously agreed `> 3 × group median` rule as a flag only. It is not an official statistical methodology.

## Missingness

Never invent a price.

Record why the quote is missing:

```text
NO_RESULTS
SOLD_OUT
CAPTCHA_BLOCKED
RATE_LIMITED
SOURCE_ERROR
AUTH_REQUIRED
ROBOTS_DISALLOWED
PARSER_FAILURE
```

## Source health

Track:

```text
success_rate
valid_observation_rate
blocked_rate
captcha_rate
rate_limit_rate
parser_error_rate
median_response_time
median_search_runtime
last_successful_collection
last_schema_change
observation_count
```

## Schema-change protection

Compare every run with historical distributions:

```text
observation_count
required-field fill rate
currency distribution
price-field fill rate
airline/carrier values
DOM/result signature
```

Example:

```text
Expected observations >= 5
Observed = 0
HTTP = 200
Parser exception = 0

=> POSSIBLE_SCHEMA_CHANGED
```

Do not publish an index from a suspiciously empty source without an alert.

## Browser diagnostics

On failures capture:

```text
screenshot
HTML
current URL
page title
console messages
network status summary
```

Use Playwright tracing during development to diagnose action sequence and page-state changes.

Do not store passwords or sensitive tokens in traces.

## Minimal Crawlee collector

```python
import asyncio
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

crawler = PlaywrightCrawler(
    headless=False,
    browser_type="chromium",
    use_session_pool=True,
    respect_robots_txt_file=True,
    retry_on_blocked=False,
    max_request_retries=2,
    max_session_rotations=0,
    max_requests_per_crawl=1,
)

@crawler.router.default_handler
async def request_handler(context: PlaywrightCrawlingContext) -> None:
    page = context.page

    # 1. verify policy
    # 2. load/reuse session
    # 3. run source-specific search workflow
    # 4. check CAPTCHA/block state
    # 5. capture evidence
    # 6. extract fare results
    # 7. normalize and validate
    # 8. persist

async def main():
    await crawler.run(["https://TARGET-SOURCE.example/"])

if __name__ == "__main__":
    asyncio.run(main())
```

## Optional approved proxies

```python
from crawlee.proxy_configuration import ProxyConfiguration

proxy_configuration = ProxyConfiguration(
    proxy_urls=[
        "http://approved-proxy-1:3128",
        "http://approved-proxy-2:3128",
    ]
)
```

Use only proxies you are permitted to use.

## Suggested YAML

```yaml
sources:
  indigo:
    enabled: true
    acquisition:
      mode: webpage
    browser:
      required: true
    robots:
      respect: true
    rate_limit:
      min_interval_seconds: 5
      max_concurrency: 1
    blocked_policy:
      captcha: stop_source
      http_403: stop_source
      http_429: backoff
      http_5xx: retry

  airindia:
    enabled: true
    acquisition:
      mode: webpage
    browser:
      required: true
    robots:
      respect: true
    rate_limit:
      min_interval_seconds: 5
      max_concurrency: 1

  ignav:
    enabled: true
    acquisition:
      mode: api
```

## First end-to-end real test

Only run:

```text
Source: one airline website
Route: DEL -> BOM
Lead time: T+7
Passengers: 1
Cabin: Economy
Trip: one-way
```

Acceptance criteria:

```text
[ ] policy gate passes
[ ] page loads
[ ] browser session created
[ ] search form completed
[ ] result state detected
[ ] fare extracted
[ ] INR validated
[ ] FareObservation constructed
[ ] raw evidence stored
[ ] PostgreSQL row inserted
[ ] dashboard shows observation
```

Only then expand to all routes and T+1/T+7/T+15/T+30/T+45.

## Edge-case coverage

Test:

- redirects;
- cookie/consent banners;
- location/market selector;
- language selector;
- popups/new tabs;
- date-picker redesign;
- slow JavaScript;
- no-result state;
- sold-out state;
- hidden/deferred prices;
- infinite scroll;
- pagination;
- multiple fare families;
- mixed cabin;
- mixed trip type;
- self-transfer;
- overnight flights;
- missing flight number;
- currency mismatch;
- price changes after fare selection;
- “from” price vs exact fare;
- 403/429/5xx;
- CAPTCHA;
- login wall;
- schema changes;
- duplicate itineraries;
- malformed amounts/dates;
- missing tax fields;
- zero/negative prices.

## Development sequence

1. Define models and status enums.
2. Implement policy gate.
3. Implement Crawlee/Playwright browser runner.
4. Implement session manager.
5. Implement source-level rate limiter.
6. Implement CAPTCHA/block detection.
7. Implement evidence capture.
8. Implement one airline adapter.
9. Add parser fixtures.
10. Add PostgreSQL persistence.
11. Add Ignav adapter.
12. Add more sources.
13. Add APIx.
14. Add dashboard.
15. Begin 30-day collection/backtest window.

## Repository structure

```text
apps/
  scraper/
    src/
      core/
        crawler.py
        browser.py
        session_manager.py
        rate_limiter.py
        policy_gate.py
        anti_bot_detector.py
        evidence.py
      sources/
        base.py
        airlines/
          indigo/
            adapter.py
            navigation.py
            parser.py
            normalizer.py
            selectors.py
          airindia/
          airindia_express/
          akasa/
          spicejet/
        otas/
          makemytrip/
          yatra/
          easemytrip/
          cleartrip/
          ixigo/
          goibibo/
        api/
          ignav.py
      models/
      storage/
      validation/
      observability/
    tests/
      fixtures/
      adapters/
      core/

apps/api/
apps/web/
packages/schemas/
packages/statistics/
packages/common/
infrastructure/
docs/
docker-compose.yml
```

## Environment

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/airfare
REDIS_URL=redis://localhost:6379/0

RAW_STORAGE_MODE=local
RAW_STORAGE_PATH=./runtime/evidence

IGNAV_API_KEY=

# Optional approved institutional proxies only
APPROVED_PROXY_URLS=

SCRAPER_HEADLESS=false
SCRAPER_DEFAULT_MIN_INTERVAL_SECONDS=5
SCRAPER_DEFAULT_MAX_CONCURRENCY=1
```

## Free local deployment

```text
PostgreSQL
Redis
MinIO (optional)
FastAPI
Scraper
Next.js
```

Run through Docker Compose.

## What Antigravity should not change autonomously

- do not disable robots checks;
- do not enable automatic blocked-page bypass;
- do not add CAPTCHA-solving;
- do not bypass authentication/access controls;
- do not rotate proxies after CAPTCHA/403 simply to continue;
- do not silently convert non-INR values;
- do not invent prices;
- do not drop failure states;
- do not alter APIx methodology without explicit approval.

## Definition of done

```text
[OK] scheduled collection jobs
[OK] robots policy enforcement
[OK] real browser execution
[OK] JavaScript rendering
[OK] browser session management
[OK] normal fare-search workflow
[OK] dynamic-result waiting
[OK] public network-response observation where useful
[OK] CAPTCHA detection
[OK] 403/429 detection
[OK] login-wall detection
[OK] schema-change detection
[OK] raw evidence
[OK] fare parsing
[OK] INR normalization
[OK] validation
[OK] PostgreSQL persistence
[OK] source health metrics
[OK] safe stop on blocked source
```

## Official technical references

Crawlee:
- https://crawlee.dev/python/docs/quick-start
- https://crawlee.dev/python/docs/guides/playwright-crawler
- https://crawlee.dev/python/docs/guides/proxy-management
- https://crawlee.dev/python/api/class/SessionPool
- https://crawlee.dev/python/api/class/PlaywrightCrawler
- https://crawlee.dev/python/docs/guides/storages

Playwright:
- https://playwright.dev/python/docs/locators
- https://playwright.dev/python/docs/actionability
- https://playwright.dev/python/docs/api/class-browsercontext
- https://playwright.dev/python/docs/auth
- https://playwright.dev/python/docs/network
- https://playwright.dev/python/docs/trace-viewer

Robots Exclusion Protocol:
- https://www.rfc-editor.org/rfc/rfc9309.html
