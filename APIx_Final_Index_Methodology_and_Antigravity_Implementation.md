
# Final Project Report — Indian Airfare Price Index (APIx)
## Full Index Methodology, Required Data Specification, and Phase-wise Implementation Plan

**Project:** Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)

**Status:** Final-project methodology specification — implementation-ready  
**Geographic scope:** India, initially domestic air travel  
**Primary frequency:** Monthly CPI-compatible index  
**Secondary frequencies:** Daily and weekly market indicators  
**Core collection design:** T+1, T+7, T+15, T+30, T+45  
**Indian methodological reference:** CPI 2024 methodology of MoSPI/NSO  
**International methodological reference:** Eurostat HICP Methodological Manual 2024 and Eurostat practical guidance on web scraping

---

# 1. Executive decision

The final system should **not calculate the airfare index by averaging all scraped ticket prices**.

The production methodology should have the following hierarchy:

```text
Scraped observations
        ↓
Legal/source validation + collection-quality checks
        ↓
Price normalization
        ↓
Offer/itinerary identity + duplicate handling
        ↓
Comparable-product stratification
        ↓
Daily observations → monthly product prices
        ↓
Short-chain Jevons elementary indices
        ↓
Lead-time aggregation
        ↓
Route aggregation
        ↓
All-India experimental Airfare Price Index (APIx)
        ↓
CPI-compatible integration layer
```

The methodology is deliberately aligned with the current Indian CPI 2024 framework:

- **2024 = 100** as the CPI reference base.
- **Jevons short/chain index** for elementary indices.
- **Young / Modified Laspeyres** for higher-level weighted aggregation.
- Expenditure-based weights for the official CPI hierarchy.
- Airfare collection from online platforms.
- Domestic airfare collection associated with advance purchase timing; the current MoSPI expert-group recommendation identifies **21 days for domestic travel** and **60 days for international travel**. The project's T+1/T+7/T+15/T+30/T+45 design should therefore be retained as a richer analytical lead-time framework, while T+21 should also be collected as an official-alignment checkpoint if the project is intended to claim close methodological comparability with CPI 2024.

This project should be described as an **experimental/analytical Airfare Price Index designed to be compatible with India's CPI methodology**, not as an official CPI sub-index unless MoSPI adopts it.

---


## Implementation decision — T+21 and the exact APIx calculation hierarchy

**Collection schedule (domestic):** T+1, T+7, T+15, **T+21**, T+30 and T+45. T+21 is an additional Indian CPI-alignment checkpoint; retain the five originally specified lead times as separately reportable series. For future international coverage, add T+60 as a separate checkpoint. Lead time is the calendar-day difference between the search date and the flight travel date. Do not silently fold T+21 into T+15 or T+30.

**Source and implementation note:** The T+21 domestic and T+60 international checkpoints are based on the MoSPI CPI 2024 Expert Group discussion of advance booking. The other five lead times are project-defined analytical strata. The presence of T+21 does not, by itself, make APIx an official MoSPI index.

**Calculation order (mandatory):** valid consumer-payable INR observations → comparable product/offer identification → within-month geometric price for each product → matched product pairs across adjacent months → short-chain Jevons for each homogeneous route × lead-time × product-quality stratum → chain elementary indices → aggregate product-quality strata using documented expenditure/booking shares → aggregate lead times using booking shares → aggregate routes using route expenditure shares (or explicitly labelled DGCA passenger-share proxy) → APIx. Do not weight observations by how many rows a scraper returns.

For a matched homogeneous stratum s in month t, let M(s,t) be products with valid comparable monthly prices in both t−1 and t, and N(s,t) = |M(s,t)|. Let P(i,t) be the geometric mean of valid within-month observations of product i. The elementary link is:

    J(s,t) = [ PRODUCT over i in M(s,t) of (P(i,t) / P(i,t−1)) ] ^ [1 / N(s,t)]

Numerically stable implementation:

    J(s,t) = exp( mean over matched i of [ln P(i,t) − ln P(i,t−1)] )

Chain each elementary index independently:

    I(s,t) = I(s,t−1) × J(s,t)

For route r and lead-time l, aggregate its homogeneous product-quality strata q using documented weights A(q|r,l):

    I(r,l,t) = SUM over q of A(q|r,l) × I(r,l,q,t)

Aggregate lead times using booking-behaviour shares B(l|r) (route-specific if available; otherwise documented national shares):

    I(r,t) = SUM over l of B(l|r) × I(r,l,t)

Aggregate routes using route weights W(r):

    APIx(t) = SUM over r of W(r) × I(r,t)

All weights at each aggregation level must sum to 1. Prefer route-level expenditure shares derived from in-scope transactions; if unavailable, DGCA passenger shares are a clearly labelled proxy, not household CPI expenditure weights. Use the official MoSPI airfare expenditure weight only when integrating the airfare sub-index into the broader CPI. The index reference must be 2024=100 only if a valid 2024 price reference exists; otherwise use an explicitly named project reference period.

**Required Antigravity acceptance tests:** (1) all matched prices unchanged ⇒ Jevons link 1; (2) all matched prices rise 10% ⇒ link 1.10; (3) chained index equals previous index times link; (4) route, lead-time and quality weights each sum to 1; (5) adding duplicate scraped rows does not change the result; (6) T+21 is scheduled and stored independently; (7) missing/sold-out prices are never treated as zero; (8) each published value records data, weight and methodology versions.


# 2. What the index is intended to measure

The target is:

> The change over time in the consumer-facing price of a representative basket of domestic passenger airfares in India, holding the relevant service characteristics sufficiently comparable between periods.

The index should measure **price change**, not:

- the number of flights,
- the number of scraped records,
- the cheapest ticket available,
- airline market share,
- website traffic,
- average search-result price without product matching.

A useful conceptual definition is:

\[
APIx_t =
\text{price level of the representative airfare basket at time }t
\]

with the reference period normalized to 100.

---

# 3. Indian CPI alignment

## 3.1 Current CPI 2024 framework

MoSPI's CPI 2024 documentation states that:

- the current CPI series uses **2024 = 100**;
- the CPI 2024 classification follows **COICOP 2018**;
- CPI 2024 has 12 divisions, 43 groups, 92 classes and 162 subclasses;
- **Jevons short index** is used for elementary index compilation;
- **Young / Modified Laspeyres** is used for higher-level aggregation;
- airfare prices are collected through well-known online platforms;
- online/e-commerce prices are collected as part of the alternative data-source framework.

Therefore, the index engine should reproduce this structure as closely as the available airfare data permits.

## 3.2 Important distinction

There are three different kinds of weights in this project:

### A. Official CPI expenditure weight
This answers:

> How important is airfare expenditure in household consumption?

This is the weight required when the airfare index is eventually inserted into the overall CPI.

### B. Route weights
This answers:

> How important is route r within the airfare market represented by the project?

DGCA passenger traffic can provide a route-representation proxy.

### C. Lead-time weights
This answers:

> What share of consumer airfare purchases/searches occurs at each advance-purchase window?

These should ideally come from transaction/booking data or a reliable industry source.

These weights must **never be conflated**.

---

# 4. Scope of the final APIx

## 4.1 Primary product scope

For the first production methodology version:

- domestic flights within India;
- one-way journey;
- adult passenger;
- economy cabin;
- INR;
- consumer-facing payable price;
- scheduled commercial passenger service;
- no self-transfer itineraries;
- normal consumer booking;
- comparable fare conditions.

## 4.2 Recommended product dimensions

Every observation must retain:

1. origin airport
2. destination airport
3. travel date
4. day of week
5. search/collection timestamp
6. lead time
7. airline
8. flight number
9. departure time
10. arrival time
11. duration
12. number of stops
13. stopover airport(s)
14. cabin
15. fare family
16. baggage entitlement
17. refundability
18. changeability
19. meal/other material included services, if available
20. base fare
21. mandatory taxes
22. airport charges
23. convenience/payment fee
24. total payable fare
25. currency
26. source/outlet
27. availability status
28. source itinerary ID
29. evidence/snapshot reference.

Not every field has to be used in the first formula, but they must be stored because they are needed for comparability, quality adjustment, auditing and future methodology improvements.

---

# 5. Definition of a homogeneous airfare product

A flight ticket is not homogeneous merely because it has the same origin and destination.

For index purposes, define a product specification such as:

```text
DOMESTIC
+ DEL-BOM
+ economy
+ adult
+ one-way
+ nonstop
+ standard fare family
+ standard baggage condition
+ weekday
+ morning departure band
+ specified lead-time class
```

A recommended product/stratum key is:

```text
product_stratum_id =
origin
+ destination
+ travel_day_type
+ departure_time_band
+ cabin
+ fare_family_group
+ baggage_group
+ stop_category
+ passenger_type
+ lead_time_class
```

Airline and flight number should be retained as characteristics and identifiers rather than being the only product definition.

### Why?

Flight numbers can disappear, schedules can change and airlines can introduce or remove flights. If flight number is the entire product identity, the index becomes unstable.

The product specification should remain meaningful from a consumer perspective.

---

# 6. Price concept

The primary price must be the **total mandatory payable consumer price**.

If the website exposes:

\[
P =
BaseFare + MandatoryTaxes + AirportCharges + MandatoryFees
\]

then:

\[
P_{total}=P_{base}+P_{tax}+P_{airport}+P_{mandatory\ fee}
\]

Use this total as the index price.

## 6.1 Do not include optional purchases

Do not automatically include:

- optional checked baggage;
- seat selection;
- meals;
- insurance;
- priority boarding;
- donations;
- optional upgrades.

If a particular product definition explicitly includes a service, then that service must be consistently defined across periods.

## 6.2 Do not manufacture components

If the source gives only:

```text
₹5,842
```

store:

```text
total_fare = 5842
base_fare = NULL
taxes = NULL
fees = NULL
```

Do not estimate a tax/base split.

---

# 7. Data model required for implementation

## 7.1 Raw observation table

Recommended table: `fare_observations`

```text
observation_id
collection_run_id
source
source_type
source_url
search_timestamp_utc
search_timestamp_local

origin
destination
travel_date
travel_day_of_week
lead_days

airline
flight_number
source_itinerary_id

departure_time_local
arrival_time_local
departure_time_utc
arrival_time_utc
duration_minutes
stops
stopover_airports

cabin_class
fare_family
fare_class
baggage_allowance
refundability
changeability
meal_included

base_fare
taxes
airport_charges
mandatory_fees
total_fare
currency

availability_status
price_status
requires_self_transfer

raw_evidence_uri
parser_version
schema_version
collection_agent_version
```

## 7.2 Normalized observation table

Add:

```text
normalized_price_inr
product_stratum_id
offer_fingerprint
itinerary_fingerprint
quality_status
duplicate_group_id
replacement_group_id
month
week
day
```

## 7.3 Weight tables

### Route weights

```text
route
dgca_period
passenger_count
route_share
route_weight
weight_source
weight_version
```

### Lead-time weights

```text
lead_time_class
booking_share
lead_time_weight
weight_source
weight_reference_period
weight_version
```

### Outlet/source weights

```text
source
source_type
market_share
source_weight
weight_source
weight_reference_period
```

### Official airfare/CPI weight

```text
cpi_item_code
cpi_weight
weight_reference_period
sector
rural_weight
urban_weight
combined_weight
source_document
```

---

# 8. Required data before implementing the index engine

The scraper data alone is not sufficient for a statistically defensible index.

## 8.1 Mandatory data

### Fare data
You need repeated observations for:

- all selected routes;
- all selected lead times;
- multiple travel dates;
- multiple collection dates;
- all source websites;
- airline;
- flight number;
- itinerary;
- fare conditions;
- total payable fare.

### Route data
You need DGCA route traffic:

\[
W_r = \frac{Passengers_r}{\sum_r Passengers_r}
\]

for the selected route universe.

Preferably obtain:

- route passenger volume;
- domestic passenger traffic;
- period/month/year;
- origin;
- destination;
- direction handling.

### Lead-time data

Preferred:

\[
W_l =
\frac{Bookings_l}{\sum_l Bookings_l}
\]

where \(l\) is the lead-time class.

If booking data is unavailable, use a documented external source or survey.

Equal weights:

\[
W_l = \frac{1}{L}
\]

should be a fallback only, and must be labelled provisional.

### CPI weight data

For integration with CPI:

\[
W_{airfare}^{CPI}
=
\frac{Airfare\ expenditure}
{Total\ in\ scope\ household\ expenditure}
\]

Use the official MoSPI weight when available at the required classification/sector level.

Do not derive this from DGCA passenger shares.

---

# 9. Route sampling

The route universe should be selected using DGCA traffic.

The selection process should be reproducible:

```text
DGCA route data
      ↓
rank routes by traffic
      ↓
remove invalid/non-domestic routes
      ↓
apply minimum coverage rule
      ↓
select representative route panel
      ↓
assign route weights
```

The system should store both:

- `selected_route_flag`
- `route_weight`

This allows the route panel to be audited later.

## 9.1 Direction

Treat:

```text
DEL-BOM
BOM-DEL
```

as separate observations if the price structures differ materially.

If the statistical design treats them as one route, aggregate the two directions only after defining the rule and obtaining appropriate directional weights.

---

# 10. Lead-time framework

The project's required lead-time classes are:

```text
T+1
T+7
T+15
T+30
T+45
```

where:

\[
LeadDays = TravelDate - SearchDate
\]

Also add:

```text
T+21
```

as an official-alignment domestic airfare checkpoint because the current MoSPI expert-group documentation identifies 21 days for domestic travel.

For international expansion, retain:

```text
T+60
```

as an additional checkpoint.

## 10.1 Exact lead-time rule

If:

```text
search date = 2026-10-01
travel date = 2026-10-08
```

then:

\[
LeadDays=7
\]

Do not calculate lead time using elapsed hours unless the methodology explicitly changes.

---



# 10A. Indian CPI-alignment checkpoint: T+21 and final calculation hierarchy

The original project specification requires the advance-purchase windows **T+1, T+7, T+15, T+30 and T+45**. For the final production methodology, add **T+21** as an additional domestic-airfare checkpoint for closer alignment with the current MoSPI CPI 2024 airfare collection design. The project's original five windows remain separately reportable; T+21 is an additional alignment stratum rather than a replacement for them.

The final domestic lead-time collection framework is therefore:

```text
T+1
T+7
T+15
T+21   <- Indian CPI-alignment checkpoint
T+30
T+45
```

For any later international-airfare extension, maintain **T+60** as the corresponding CPI-alignment checkpoint where applicable to the adopted MoSPI methodology.

## 10A.1 Core calculation hierarchy

For each homogeneous product stratum `s`, first calculate the matched-product short-chain Jevons link:

\[
J_{s,t}=\left[\prod_{i\in M_{s,t}}\frac{\bar P_{i,t}}{\bar P_{i,t-1}}\right]^{1/N_{s,t}}
\]

where `M_(s,t)` is the set of comparable products observed in both periods, `N_(s,t)` is the number of matched products, and `P-bar_(i,t)` is the monthly geometric price of product `i`.

Chain the elementary index through time:

\[
I_{s,t}=I_{s,t-1}\times J_{s,t}
\]

with the chosen reference period initialized to 100.

For each route `r`, aggregate the lead-time-specific indices using consumer booking-behaviour weights:

\[
I_{r,t}=\sum_l W_l I_{r,l,t}
\]

subject to:

\[
\sum_l W_l=1
\]

Then aggregate route indices using route-representation weights:

\[
APIx_t=\sum_r W_r I_{r,t}
\]

subject to:

\[
\sum_r W_r=1
\]

The complete implementation hierarchy is therefore:

```text
Comparable monthly product prices
        -> matched price relatives
        -> short-chain Jevons elementary index
        -> lead-time weighted route index
        -> route-weighted all-India APIx
```

Here, `W_l` is the lead-time/booking-behaviour weight, `W_r` is the route-representation weight, `P-bar_(i,t)` is the monthly geometric price of a comparable product, and `I_(s,t)` is the chained elementary index. This hierarchy must be implemented instead of a simple arithmetic comparison of average scraped fares.

## 10A.2 Implementation requirement

Antigravity must treat T+21 as a first-class configured lead-time value throughout the system: search scheduling, schema validation, sampling configuration, weight tables, index calculation, API responses, dashboard filters, tests and backtesting. It must not hard-code only the original five lead times. Lead-time configuration must remain versioned so future methodological changes can be introduced without rewriting historical results.


# 11. Collection frequency

The final project should collect fares at high frequency because airfare prices can change rapidly.

Recommended:

- daily collection for the index sample;
- multiple collection times if feasible;
- weekly aggregation for monitoring;
- monthly aggregation for CPI-compatible publication.

Do not confuse collection frequency with index frequency.

The same product may be observed many times during a month.

---

# 12. Monthly price of a product

Eurostat web-scraping guidance notes that when products are observed multiple times within a month and transaction weights are unavailable, an unweighted arithmetic or geometric aggregation can be used.

For airfare, use the geometric mean as the default because the downstream elementary index is Jevons-based.

For product \(i\) in month \(t\):

\[
\bar P_{i,t}
=
\left(
\prod_{d=1}^{D_{i,t}} P_{i,t,d}
\right)^{1/D_{i,t}}
\]

where:

- \(P_{i,t,d}\) = valid observed price;
- \(D_{i,t}\) = number of valid observations.

Equivalent log form:

\[
\ln(\bar P_{i,t})
=
\frac{1}{D_{i,t}}
\sum_d \ln(P_{i,t,d})
\]

This is useful for numerical stability.

---

# 13. Observation eligibility

Before a price enters the index, it must satisfy:

```text
currency = INR
price > 0
availability = available
not cancelled
not parser error
not technical error
not duplicate
not self-transfer
product specification valid
required characteristics present
```

Possible quality states:

```text
VALID
SOLD_OUT
NOT_AVAILABLE
CAPTCHA_BLOCK
SERVER_ERROR
PARSER_ERROR
LEGAL_RESTRICTION
INVALID_PRICE
DUPLICATE
QUALITY_REVIEW
OUTLIER_REVIEW
REPLACED
```

Never convert missing/sold-out into zero.

---

# 14. Outlier treatment

The objective is to remove **data errors**, not genuine airfare volatility.

Examples:

### Remove/quarantine
- ₹0
- negative price
- malformed currency
- HTML parser accidentally reading a seat count as fare
- duplicated DOM price
- impossible duration
- impossible date
- corrupted value such as `₹5,84,200` caused by parsing.

### Retain
- ₹25,000 during a major festival
- high fare shortly before departure
- sudden airline repricing
- unusually high but valid business event demand.

The index should capture genuine price volatility.

## 14.1 Statistical outlier flag

Use robust statistics for review, not automatic deletion.

For example, within a homogeneous stratum:

\[
z_i =
\frac{\ln P_i - median(\ln P)}
{1.4826 \times MAD(\ln P)}
\]

Flag if:

\[
|z_i| > z_{threshold}
\]

but send the observation to review.

Do not delete genuine market movements solely because they are statistically unusual.

---

# 15. Duplicate and source handling

This is one of the most important parts of the project.

The same flight may appear on:

```text
IndiGo
MakeMyTrip
Yatra
EaseMyTrip
Cleartrip
ixigo
Goibibo
```

Therefore, row count cannot be used as a market weight.

## 15.1 Itinerary fingerprint

Create:

\[
F_{itinerary}
=
hash(
origin,
destination,
travel\ date,
airline,
flight\ number,
departure,
arrival,
stops
)
\]

## 15.2 Offer fingerprint

Create a more detailed fingerprint:

\[
F_{offer}
=
hash(
F_{itinerary},
fare\ family,
cabin,
baggage,
refundability,
changeability
)
\]

Two identical offers across sources can then be detected.

## 15.3 Do not automatically discard all source differences

If:

- airline direct price = ₹5,200
- OTA payable price = ₹5,050

these are genuinely different consumer purchase offers.

Keep both if both are legally/operationally accessible and satisfy the scope.

If the displayed prices are exactly the same offer replicated across sources, prevent accidental over-weighting.

---

# 16. Outlet/source treatment

The source is an outlet dimension.

The project should preferably have source-level weights if credible market-share information becomes available.

If source weights are available:

\[
\sum_s W_s = 1
\]

and:

\[
I_{stratum,t}
=
\sum_s W_s I_{s,stratum,t}
\]

If source weights are not available, do not invent precise market shares.

For the first implementation:

1. deduplicate exact replicated offers;
2. maintain balanced source sampling;
3. publish source coverage;
4. run sensitivity tests under equal-source weighting and observation weighting;
5. replace provisional source weights once credible market-share data is obtained.

---

# 17. Product matching

The core principle is:

> Compare like with like.

For month \(t-1\) and month \(t\), define the matched set:

\[
M_{s,t}
=
\{i:
i\ exists\ in\ both\ periods
\land
Q_{i,t}=Q_{i,t-1}
\}
\]

where \(Q\) is the product specification.

## 17.1 Exact match

Same:

- route
- travel-day type
- departure-time band
- cabin
- fare family group
- baggage group
- stop category
- passenger type
- lead-time class

→ direct price comparison.

## 17.2 Acceptable replacement

If the original flight/offer disappears:

- replacement must be in the same product stratum;
- it should be consumer-comparable;
- replacement must be logged;
- quality difference must be assessed.

## 17.3 Non-comparable change

Examples:

```text
nonstop → one-stop
economy → premium economy
standard fare → fully flexible fare
no baggage → baggage included
```

Do not blindly compare as if nothing changed.

---

# 18. Quality adjustment

A major airfare change can be caused by a quality change rather than a pure price change.

The first production version should use a strict matching strategy.

Future advanced version can use hedonic adjustment.

## 18.1 Direct comparable case

\[
PriceRelative_i
=
\frac{P_{i,t}}{P_{i,t-1}}
\]

## 18.2 Quality-adjusted case

If the replacement has an estimated quality difference:

\[
P^{QA}_{i,t}
=
\frac{P_{replacement,t}}{QF}
\]

where \(QF\) is the estimated quality factor.

For example, if a model estimates that the replacement's extra baggage service increases the comparable value by 4%, then the quality-adjusted price must remove that 4% component.

Do not implement arbitrary quality factors in version 1.

---

# 19. Elementary index: short-chain Jevons

This is the central formula.

For homogeneous stratum \(s\):

\[
J_{s,t}
=
\left[
\prod_{i \in M_{s,t}}
\frac{\bar P_{i,t}}
{\bar P_{i,t-1}}
\right]^{1/N_{s,t}}
\]

where:

- \(M_{s,t}\) = matched products;
- \(N_{s,t}\) = number of matched products;
- \(\bar P_{i,t}\) = monthly geometric price.

Equivalent log form:

\[
\ln J_{s,t}
=
\frac{1}{N_{s,t}}
\sum_{i \in M_{s,t}}
\left[
\ln(\bar P_{i,t})-\ln(\bar P_{i,t-1})
\right]
\]

Then chain:

\[
I_{s,t}
=
I_{s,t-1} \times J_{s,t}
\]

If the reference period is \(0\):

\[
I_{s,0}=100
\]

and recursively:

\[
I_{s,t}
=
100
\prod_{\tau=1}^{t}
J_{s,\tau}
\]

This is preferable to directly comparing every month with a fixed base price because the short-chain method handles changing samples and replacements more naturally.

---

# 20. Minimum matched-sample rule

Do not calculate an elementary index from an extremely small sample.

Define:

```text
MIN_MATCHED_PRODUCTS
MIN_OBSERVATION_DAYS
MIN_COVERAGE_RATIO
```

Example project rule:

\[
Coverage_{s,t}
=
\frac{N_{matched,s,t}}
{N_{eligible,s,t-1}}
\]

Only publish the stratum if:

\[
Coverage_{s,t}\ge C_{min}
\]

The exact threshold must be calibrated from the actual data rather than invented permanently.

Suggested starting engineering threshold:

```text
matched products >= 5
coverage >= 50%
```

Then perform sensitivity testing with thresholds such as 30%, 50%, 70%.

These are engineering safeguards, not official MoSPI thresholds.

---

# 21. Lead-time aggregation

For each route \(r\), calculate a lead-time-specific index:

\[
I_{r,l,t}
\]

where:

\[
l \in
\{1,7,15,30,45,21\}
\]

for the domestic project.

If the consumer booking weights are \(W_l\):

\[
\sum_l W_l=1
\]

then:

\[
I_{r,t}
=
\sum_l W_l I_{r,l,t}
\]

This is the higher-level weighted arithmetic aggregation consistent with the Young/Modified Laspeyres structure used in CPI 2024.

---

# 22. Route aggregation

Let:

\[
W_r
=
\frac{DGCAPassengers_r}
{\sum_r DGCAPassengers_r}
\]

Then:

\[
\sum_r W_r=1
\]

and:

\[
APIx_t
=
\sum_r W_r I_{r,t}
\]

This produces the experimental all-India airfare index.

## Important qualification

DGCA passenger-share weighting is a **route-representation proxy**.

It is not the official household expenditure weight for airfare.

---

# 23. Better route weights when fare data is available

If the project obtains reliable route-level expenditure or transaction information, use it.

A useful approximation is:

\[
E_r
=
Passengers_r \times AverageFare_r
\]

then:

\[
W_r^{exp}
=
\frac{E_r}
{\sum_r E_r}
\]

This is preferable to pure passenger weighting if the objective is to approximate expenditure importance.

However, actual consumer expenditure/booking data should be preferred to reconstructed expenditure whenever available.

---

# 24. Official CPI integration

Suppose the official CPI airfare item weight is:

\[
W_{airfare}^{CPI}
\]

Then an airfare sub-index can be inserted into a broader CPI structure as:

\[
CPI_t
=
\sum_k
W_k^{CPI} I_{k,t}
\]

where airfare is one of the \(k\) items.

For the airfare component:

\[
Contribution_{airfare,t}
=
W_{airfare}^{CPI}
\times
I_{airfare,t}
\]

The exact CPI classification code and official weight must come from the current MoSPI CPI 2024 weight structure.

The project must not substitute DGCA route weights for the official CPI expenditure weight.

---

# 25. Base year and reference period

The current Indian CPI reference is:

\[
2024=100
\]

Therefore, if historical 2024 airfare observations are available:

\[
APIx_{2024}=100
\]

using the methodology-defined annual/reference-period normalization.

If the project begins collecting only in 2026, it must not falsely label the resulting series as 2024=100.

In that situation use:

```text
APIx Jan-2026 = 100
```

or another clearly documented project reference period.

The series can later be re-referenced:

\[
I'_t
=
100 \times
\frac{I_t}{I_{reference}}
\]

Rebasing changes the level, not the growth rates.

---

# 26. Daily index

The daily index is a market-monitoring indicator.

For day \(d\), calculate a daily product price:

\[
P_{i,d}
=
GeometricMean(
valid\ observations\ for\ i\ on\ d
)
\]

Then daily matched Jevons:

\[
J_{s,d}
=
\left[
\prod_{i\in M_{s,d}}
\frac{P_{i,d}}{P_{i,d-1}}
\right]^{1/N}
\]

and chain:

\[
I_{s,d}=I_{s,d-1}J_{s,d}
\]

The daily index should be clearly labelled as a high-frequency indicator.

---

# 27. Weekly index

For week \(w\):

\[
P_{i,w}
=
\left(
\prod_{d\in w}P_{i,d}
\right)^{1/D}
\]

Then apply the same short-chain Jevons process.

Do not average daily index numbers to obtain the weekly index if a consistent price-level aggregation can be performed instead.

---

# 28. Monthly index

The monthly index is the primary CPI-compatible output.

Recommended chain:

```text
daily observations
      ↓
monthly product prices
      ↓
monthly matched products
      ↓
short Jevons
      ↓
lead-time weighted indices
      ↓
route weighted indices
      ↓
monthly APIx
```

---

# 29. Inflation rates

Month-on-month:

\[
MoM_t
=
\left(
\frac{APIx_t}{APIx_{t-1}}-1
\right)\times100
\]

Year-on-year:

\[
YoY_t
=
\left(
\frac{APIx_t}{APIx_{t-12}}-1
\right)\times100
\]

For a daily series, use the equivalent previous-day comparison.

---

# 30. Final combined formula

The conceptual project formula is:

\[
APIx_t
=
\sum_r W_r
\left[
\sum_l W_l
I_{r,l,t}
\right]
\]

where each \(I_{r,l,t}\) is produced by chained Jevons:

\[
I_{r,l,t}
=
I_{r,l,t-1}
\left[
\prod_{i\in M_{r,l,t}}
\frac{\bar P_{i,t}}
{\bar P_{i,t-1}}
\right]^{1/N_{r,l,t}}
\]

Therefore:

\[
\boxed{
APIx_t
=
\sum_r W_r
\left[
\sum_l W_l
I_{r,l,t-1}
\left(
\prod_{i\in M_{r,l,t}}
\frac{\bar P_{i,t}}
{\bar P_{i,t-1}}
\right)^{1/N_{r,l,t}}
\right]
}
\]

with:

\[
\sum_r W_r=1
\]

and:

\[
\sum_l W_l=1
\]

This is the primary implementation formula for the project.

---

# 31. Why the hierarchy is important

Do not calculate:

\[
\frac{AverageFare_t}{AverageFare_{t-1}}
\]

as the main index.

That method ignores:

- changing product composition;
- route importance;
- lead-time behaviour;
- repeated observations;
- quality differences;
- source duplication;
- product replacement;
- matched-product methodology.

The proposed hierarchy handles these explicitly.

---

# 32. Seasonality

Airfare is highly seasonal.

The main index should **retain genuine seasonal price movements**.

Examples:

- Diwali;
- Christmas/New Year;
- summer holidays;
- long weekends;
- school holidays;
- major national events.

Do not seasonally adjust the main APIx.

If required, publish a separate:

```text
APIx seasonally adjusted
```

analytical series.

---

# 33. Travel-date versus collection-date problem

This is especially important for airfare.

The price is observed on:

```text
search_date
```

but applies to:

```text
travel_date
```

Therefore every observation must store both.

Example:

```text
search_date = 2026-09-01
travel_date = 2026-09-30
lead_days = 29
```

The monthly CPI-style index is based on the **price observation period**, not simply the month in which the flight travels.

The travel date is a product characteristic.

This distinction must never be lost.

---

# 34. Advance-purchase measurement

For the project's standard lead-time strata:

```text
T+1
T+7
T+15
T+30
T+45
```

the system should generate search dates from target travel dates.

For example:

```text
Travel date: 30 Oct

T+1  → search on 29 Oct
T+7  → search on 23 Oct
T+15 → search on 15 Oct
T+30 → search on 30 Sep
T+45 → search on 15 Sep
```

Use calendar-day logic consistently.

---

# 35. Search design

The index requires a **predefined sampling frame**.

Create:

```text
route panel
×
travel-date panel
×
lead-time panel
×
departure-time strata
×
stop strata
×
fare-family strata
×
source panel
```

This is preferable to blindly scraping everything and allowing high-volume routes/airlines to dominate.

Eurostat's web-scraping guidance distinguishes targeted scraping from bulk scraping and emphasizes product definition, representativeness and comparability. For an official-statistics-oriented project, a controlled sampling frame is therefore important.

---

# 36. Travel-date sampling

For each month select a reproducible set of travel dates.

Recommended dimensions:

- Monday–Thursday;
- Friday;
- Saturday;
- Sunday;
- normal period;
- peak/holiday period.

Do not select only one travel date per month.

The project should capture enough travel-date variation to represent the service.

---

# 37. Departure-time stratification

A useful grouping:

```text
EARLY_MORNING
MORNING
AFTERNOON
EVENING
NIGHT
```

Exact time bands should be fixed before index production.

Why?

A ₹4,500 morning flight and ₹8,500 prime-time flight are not necessarily equivalent products.

---

# 38. Stop stratification

At minimum:

```text
NONSTOP
ONE_STOP
MULTIPLE_STOP
```

For the primary domestic index:

- use nonstop as the core product where sufficient data exists;
- calculate one-stop separately;
- do not mix nonstop and one-stop indiscriminately.

If the market-representative product definition requires both, aggregate them using explicit weights.

---

# 39. Fare-family stratification

At minimum classify:

```text
STANDARD
FLEXIBLE
PREMIUM/FLEX
OTHER
UNKNOWN
```

The primary index should ideally use the most consistently observable standard economy product.

Unknown fare family should not silently be treated as standard.

---

# 40. Baggage normalization

Possible groups:

```text
CABIN_ONLY
STANDARD_CHECKED_BAG
OTHER
UNKNOWN
```

Do not mix them without a quality rule.

If the project cannot reliably identify baggage conditions from a source, store:

```text
baggage_group = UNKNOWN
```

and exclude it from the strictest comparable index or handle it through a documented broad stratum.

---

# 41. Missing prices

A missing price has a reason.

Store:

```text
MISSING_REASON
```

such as:

```text
SOLD_OUT
NO_FLIGHT
SOURCE_DOWN
CAPTCHA_BLOCK
PARSER_FAILURE
LEGAL_RESTRICTION
NETWORK_FAILURE
PRICE_NOT_DISPLAYED
```

Never encode:

```text
missing = 0
```

and never replace it with the cheapest available flight automatically.

---

# 42. Replacement policy

When an offer disappears:

1. identify the original product;
2. determine why it disappeared;
3. search within the same stratum for a replacement;
4. check quality comparability;
5. document the replacement;
6. apply the chosen quality-adjustment rule if needed;
7. record the event permanently.

Recommended table:

```text
replacement_id
old_offer_id
new_offer_id
replacement_date
reason
same_stratum
quality_change
quality_adjustment_factor
method
review_status
```

---

# 43. Quality-control metrics

Every collection run should produce:

```text
requested searches
successful searches
valid observations
invalid observations
sold-out observations
parser failures
blocked/CAPTCHA events
duplicate rate
missing rate
currency error rate
price min
price max
price median
price geometric mean
routes covered
lead-times covered
sources covered
airlines covered
```

For each source also calculate:

\[
SuccessRate
=
\frac{SuccessfulSearches}
{RequestedSearches}
\]

and:

\[
ValidRate
=
\frac{ValidObservations}
{CollectedObservations}
\]

---

# 44. Index quality-control metrics

For each index cell calculate:

```text
matched product count
match rate
coverage rate
number of sources
number of airlines
number of travel dates
number of observations
geometric price
Jevons link
previous index
current index
MoM
YoY
revision flag
```

A cell should not silently produce an index when coverage is inadequate.

---

# 45. Revision policy

The index system should support revisions.

If a parsing error is discovered:

```text
raw observation
→ corrected observation
→ recalculation
→ new index version
```

Store:

```text
index_version
calculation_timestamp
methodology_version
data_version
weight_version
parser_version
```

Never overwrite the historical index without an audit trail.

---

# 46. Reproducibility

Every published index value must be reproducible from:

```text
raw observation version
+
normalization version
+
product classification version
+
weight version
+
methodology version
+
code version
```

A recommended index run ID:

```text
APIX-2026-09-V001
```

---

# 47. Database architecture

Recommended logical tables:

```text
sources
collection_runs
search_requests
fare_observations
normalized_fares
offer_fingerprints
itinerary_fingerprints
product_strata
routes
route_weights
lead_time_weights
source_weights
travel_date_calendar
quality_events
replacement_events
monthly_product_prices
elementary_indices
route_indices
api_indices
index_runs
methodology_versions
```

---

# 48. Antigravity implementation architecture

The implementation should be modular.

```text
app/
├── collectors/
│   ├── base.py
│   ├── indigo.py
│   ├── airindia.py
│   ├── airindia_express.py
│   ├── akasa.py
│   ├── spicejet.py
│   ├── easemytrip.py
│   ├── makemytrip.py
│   ├── yatra.py
│   ├── cleartrip.py
│   ├── ixigo.py
│   └── goibibo.py
│
├── normalization/
│   ├── fare_normalizer.py
│   ├── currency.py
│   ├── datetime.py
│   └── baggage.py
│
├── quality/
│   ├── validators.py
│   ├── duplicates.py
│   ├── outliers.py
│   ├── coverage.py
│   └── replacements.py
│
├── sampling/
│   ├── routes.py
│   ├── travel_dates.py
│   ├── lead_times.py
│   └── strata.py
│
├── weights/
│   ├── route_weights.py
│   ├── lead_time_weights.py
│   ├── source_weights.py
│   └── cpi_weights.py
│
├── aggregation/
│   ├── monthly_prices.py
│   ├── jevons.py
│   ├── lead_time.py
│   ├── routes.py
│   └── api_index.py
│
├── validation/
│   ├── index_checks.py
│   ├── coverage_checks.py
│   └── sensitivity.py
│
└── api/
    ├── routes.py
    └── schemas.py
```

---

# 49. Recommended Python interfaces

## Fare source

```python
class FareSourceAdapter(Protocol):
    async def search(
        self,
        request: FareSearchRequest
    ) -> list[RawFareObservation]:
        ...
```

## Normalization

```python
class FareNormalizer:
    def normalize(
        self,
        observation: RawFareObservation
    ) -> NormalizedFareObservation:
        ...
```

## Product classifier

```python
class ProductClassifier:
    def classify(
        self,
        observation: NormalizedFareObservation
    ) -> ProductStratum:
        ...
```

## Index engine

```python
class AirfareIndexEngine:
    def calculate_monthly_product_prices(...):
        ...

    def calculate_jevons_links(...):
        ...

    def chain_elementary_indices(...):
        ...

    def aggregate_lead_times(...):
        ...

    def aggregate_routes(...):
        ...

    def calculate_api_index(...):
        ...
```

---

# 50. Exact implementation pipeline

## Phase 0 — Methodology lock

Before coding the index engine, freeze:

- product definition;
- route universe;
- lead-time classes;
- travel-date sampling;
- departure-time bands;
- stop categories;
- fare-family categories;
- baggage categories;
- missing-data rules;
- duplicate rules;
- replacement rules;
- route weighting;
- lead-time weighting;
- source weighting;
- base/reference period;
- minimum coverage;
- rounding.

Output:

```text
APIx_Methodology_v1.0.md
```

---

# 51. Phase 1 — Data audit

Use the existing scraped dataset.

Tasks:

1. profile all columns;
2. inspect null rates;
3. inspect currencies;
4. inspect date consistency;
5. inspect routes;
6. inspect airlines;
7. inspect source distribution;
8. inspect lead-time distribution;
9. inspect fare ranges;
10. inspect duplicate rates;
11. inspect repeated itineraries;
12. inspect missing flight characteristics.

Output:

```text
data_quality_report.html
data_quality_summary.json
```

Do not calculate the final index until this phase is complete.

---

# 52. Phase 2 — Canonical schema

Convert all source-specific records into the canonical airfare schema.

Input:

```text
EaseMyTrip
MakeMyTrip
Yatra
Cleartrip
...
```

Output:

```text
NormalizedFareObservation
```

Every source must produce the same schema.

---

# 53. Phase 3 — Sampling frame

Create:

```text
routes.csv
travel_dates.csv
lead_times.csv
product_strata.csv
```

Each row should have a stable ID.

Example:

```text
DEL-BOM-NONSTOP-ECO-STANDARD-MORNING-T30
```

---

# 54. Phase 4 — Deduplication

Implement:

```python
itinerary_fingerprint()
offer_fingerprint()
duplicate_group()
```

Rules must distinguish:

- exact duplicate;
- same itinerary/different fare;
- same itinerary/different source;
- different itinerary.

---

# 55. Phase 5 — Price normalization

Implement:

```text
INR validation
Decimal price handling
mandatory-price calculation
currency quarantine
fee classification
```

Use `Decimal`, not binary floating point, for monetary amounts.

---

# 56. Phase 6 — Monthly product prices

For each:

```text
month
+
product_stratum
+
offer/product identity
```

calculate:

\[
\bar P_{i,t}
=
\exp
\left(
\frac{1}{D}
\sum_d \ln P_{i,t,d}
\right)
\]

Store both:

```text
geometric_price
observation_count
```

---

# 57. Phase 7 — Matching engine

Match month \(t-1\) to \(t\).

Output:

```text
product_id
price_previous
price_current
price_relative
match_status
replacement_status
quality_status
```

Then calculate:

\[
R_{i,t}
=
\frac{P_{i,t}}{P_{i,t-1}}
\]

---

# 58. Phase 8 — Jevons engine

For every elementary stratum:

\[
J_{s,t}
=
\exp
\left[
\frac{1}{N}
\sum_i
\ln R_{i,t}
\right]
\]

Then:

\[
I_{s,t}
=
I_{s,t-1}J_{s,t}
\]

Set:

\[
I_{s,0}=100
\]

for the chosen reference period.

---

# 59. Phase 9 — Lead-time aggregation

Calculate:

\[
I_{r,t}
=
\sum_l W_lI_{r,l,t}
\]

Validate:

```text
sum(W_l) == 1
```

If weights are provisional, mark them:

```text
weight_status = PROVISIONAL
```

---

# 60. Phase 10 — Route aggregation

Calculate:

\[
APIx_t
=
\sum_r W_rI_{r,t}
\]

Validate:

```text
sum(W_r) == 1
```

Store the exact route weights used in each index run.

---

# 61. Phase 11 — Validation

The final system should automatically test:

### Mathematical
- weights sum to 1;
- no negative prices;
- no zero prices;
- no invalid logarithms;
- no missing required index cells.

### Statistical
- coverage;
- matched sample;
- source concentration;
- route concentration;
- extreme movements;
- month-to-month breaks.

### Engineering
- deterministic output;
- idempotent reruns;
- reproducible calculations;
- version consistency.

---

# 62. Phase 12 — Backtesting

The project specification requires a 30-day backtest.

The backtest should compare the project's airfare indicators against available DGCA fare information where comparable.

Do not expect exact equality because:

- DGCA and scraped data may have different product definitions;
- observed booking windows may differ;
- DGCA may use different aggregation;
- route universes may differ;
- sources may differ.

Instead calculate:

\[
Error_t
=
APIx_t - Benchmark_t
\]

and:

\[
APE_t
=
\left|
\frac{APIx_t-Benchmark_t}
{Benchmark_t}
\right|\times100
\]

Also calculate correlation of changes:

\[
Corr(\Delta APIx,\Delta Benchmark)
\]

and:

\[
RMSE
=
\sqrt{
\frac{1}{T}
\sum_t
(APIx_t-Benchmark_t)^2
}
\]

The benchmark methodology and coverage must be documented.

---

# 63. Sensitivity analysis

The final project should calculate multiple variants.

## Variant A — Passenger route weights

\[
W_r^{DGCA}
\]

## Variant B — Fare-adjusted route weights

\[
W_r^{Fare}
\]

## Variant C — Equal route weights

\[
W_r^{Equal}
=
1/R
\]

## Variant D — Equal lead-time weights

\[
W_l^{Equal}
=
1/L
\]

Compare the resulting indices.

This is not to choose the most convenient result; it is to quantify how much the methodology depends on the weighting assumptions.

---

# 64. Robustness experiments

Run:

1. all sources;
2. airline websites only;
3. OTA websites only;
4. exact duplicate removal;
5. source-balanced sample;
6. nonstop only;
7. nonstop + one-stop;
8. all lead times;
9. official-alignment T+21 only;
10. equal lead-time weights;
11. booking-based lead-time weights.

Report:

```text
index level
MoM
YoY
difference from baseline
```

---

# 65. Data needed from the user before Antigravity starts coding

Provide these as files/configuration.

## A. Existing scraped fare data

Prefer CSV/Parquet/JSON with:

```text
source
search_timestamp
origin
destination
travel_date
lead_days
airline
flight_number
departure
arrival
duration
stops
fare_family
cabin
baggage
base_fare
taxes
fees
total_fare
currency
availability
source_itinerary_id
source_url
```

## B. DGCA route traffic

Need:

```text
origin
destination
period
passenger_count
```

Prefer monthly data.

## C. Lead-time/booking distribution

Need:

```text
lead_time
booking_count/share
period
market scope
source
```

If unavailable, explicitly mark the weights as provisional.

## D. CPI 2024 airfare weight

Need the current official MoSPI weight at the required aggregation level.

## E. Source information

Need:

```text
source
source_type
coverage
collection_method
legal/permission status
```

## F. Travel calendar

Need:

```text
date
weekday
holiday
festival
peak_period
```

This is needed for sampling and analysis.

---

# 66. Recommended additional data

For a genuinely strong final project, obtain:

### Flight schedule data

```text
airline
flight number
origin
destination
departure
arrival
effective dates
```

### Airport metadata

```text
airport_code
city
state
airport_name
timezone
```

### Holiday calendar

National and major state holidays.

### Weather/disruption indicators

Optional, for explanatory analysis only.

### Fuel prices

Optional explanatory variable.

### Airline capacity

Optional:

```text
route
airline
scheduled seats
frequency
```

These should not be inserted directly into the price index unless the methodology explicitly uses them.

---

# 67. Data that should NOT be used as index weights

Do not use:

- number of scraped rows;
- number of HTML cards;
- number of flights returned by a website;
- number of website visits;
- cheapest fare frequency;
- scraper frequency;
- number of search results.

These are collection characteristics, not consumer expenditure weights.

---

# 68. API output schema

Recommended endpoint:

```text
GET /api/v1/airfare-index
```

Parameters:

```text
from
to
frequency
route
lead_time
source
```

Response:

```json
{
  "index_name": "India Airfare Price Index",
  "reference_period": "2024",
  "base_value": 100,
  "frequency": "monthly",
  "period": "2026-09",
  "index": 118.42,
  "mom_percent": 2.31,
  "yoy_percent": 6.84,
  "methodology_version": "1.0",
  "weight_version": "2026.09"
}
```

---

# 69. Dashboard outputs

The dashboard should show:

## Main KPI

```text
Current APIx
MoM
YoY
```

## Route chart

```text
DEL-BOM
DEL-BLR
BOM-BLR
DEL-CCU
BLR-HYD
MAA-DEL
...
```

## Lead-time curve

Show:

```text
T+1
T+7
T+15
T+21
T+30
T+45
```

## Route heatmap

Rows:

```text
Origin
```

Columns:

```text
Destination
```

Value:

```text
latest index / MoM / YoY
```

## Source comparison

For diagnostic use only:

```text
airline direct
OTA
```

---

# 70. Recommended project outputs

The final project should produce:

```text
1. Raw scraped database
2. Clean normalized airfare database
3. Quality-control report
4. Product classification table
5. Route-weight table
6. Lead-time-weight table
7. Monthly product-price table
8. Elementary Jevons indices
9. Route-level indices
10. All-India APIx
11. Daily APIx indicator
12. Weekly APIx indicator
13. Monthly CPI-compatible APIx
14. Inflation rates
15. Backtest report
16. Sensitivity report
17. Methodology document
18. API
19. Dashboard
20. Automated tests
```

---

# 71. Testing requirements

## Unit tests

Test:

- lead-day calculation;
- currency conversion;
- price normalization;
- fingerprint generation;
- duplicate detection;
- geometric mean;
- Jevons formula;
- chaining;
- weighted aggregation;
- rebasing.

## Property tests

Verify:

\[
\sum W=1
\]

and:

- identical prices produce index = 100 relative;
- all prices increasing by 10% produces approximately 10% growth;
- multiplying every price by the same factor produces the same factor in the price index;
- changing currency incorrectly is rejected;
- zero/negative prices never enter logs.

## Regression tests

Use frozen raw data snapshots.

A code change must not unexpectedly change historical values.

---

# 72. Rounding policy

Do calculations at full precision.

Recommended:

```text
raw price: Decimal
monthly geometric price: high precision
Jevons: high precision
weights: high precision
index: round only at presentation
```

For example:

```text
stored index = 118.423817...
display = 118.42
```

Do not round each individual price before calculating the geometric mean.

---

# 73. Weight versioning

Weights must be versioned.

Example:

```text
route_weight_version = DGCA_2026_M09
lead_time_weight_version = BOOKING_2026_Q2
cpi_weight_version = CPI2024
```

This is essential for reproducibility.

---

# 74. Methodology versioning

Every result should carry:

```text
methodology_version
```

Example:

```text
APIx v1.0
```

A later improvement:

```text
APIx v1.1
```

might introduce:

- improved source weights;
- quality adjustment;
- improved route panel;
- additional lead-time weights.

Never silently change methodology.

---

# 75. Recommended first production version

Freeze the following as APIx v1.0:

### Product
Domestic, one-way, adult, economy, standard fare, mandatory payable price.

### Routes
DGCA-selected high-traffic domestic routes.

### Lead times
T+1, T+7, T+15, T+21, T+30, T+45.

### Time strata
Fixed departure-time bands.

### Stops
Nonstop and one-stop separately.

### Monthly price
Geometric mean of valid observations.

### Elementary formula
Short-chain Jevons.

### Lead-time aggregation
Weighted arithmetic mean.

### Route aggregation
Weighted arithmetic mean.

### Route weights
DGCA passenger-share proxy until better expenditure/booking weights are available.

### Reference
2024=100 if 2024 data exists; otherwise a clearly declared project reference period.

### Missing
No imputation in the first version unless a documented replacement/quality method applies.

### Quality
Strict matching first; advanced hedonic adjustment later.

---

# 76. What should be implemented first in Antigravity

Do **not** ask Antigravity to immediately write the complete scraper + index engine.

Use these prompts sequentially.

## Prompt 1 — Audit

```text
Read the project repository and all existing airfare schemas, scraper outputs and documentation.

Do not modify code.

Produce:
1. current architecture,
2. current data schema,
3. all existing fields,
4. missing fields required for the APIx methodology,
5. duplicate risks,
6. source-specific inconsistencies,
7. current test coverage,
8. files that should be reused,
9. files that should be refactored.

Compare the existing project against APIx_Methodology_v1.0.md.
```

## Prompt 2 — Canonical schema

```text
Implement the canonical RawFareObservation and NormalizedFareObservation models from APIx_Methodology_v1.0.md.

Do not change scraper behaviour yet.

Add:
- Decimal monetary fields,
- timestamps,
- lead_days,
- product characteristics,
- availability status,
- source itinerary ID,
- fingerprints,
- quality status,
- methodology/schema versions.

Add migrations and tests.
```

## Prompt 3 — Normalization

```text
Implement the normalization pipeline.

Requirements:
- validate INR,
- preserve source raw price,
- calculate total mandatory payable price only when components are explicitly available,
- never invent base/tax values,
- normalize timestamps,
- normalize stops,
- normalize cabin,
- normalize fare family,
- normalize baggage,
- calculate lead_days,
- assign quality status.

Add fixture-based tests.
```

## Prompt 4 — Sampling

```text
Implement the APIx sampling frame.

Create:
- route configuration,
- travel-date calendar,
- lead-time configuration,
- departure-time bands,
- stop categories,
- fare-family categories.

The lead-time configuration must include:
1, 7, 15, 21, 30, 45 days.

All configuration must be versioned.
```

## Prompt 5 — Deduplication

```text
Implement itinerary and offer fingerprints.

Detect:
- exact duplicates,
- same itinerary/different offer,
- replicated offers across sources.

Do not delete records physically.
Assign duplicate_group_id and keep raw evidence.
```

## Prompt 6 — Monthly product prices

```text
Implement monthly geometric product-price aggregation.

For each product:
P_month = exp(mean(log(valid prices)))

Exclude invalid observations.

Store:
- geometric_price,
- observation_count,
- active_days,
- source_count,
- quality_status.

Add tests.
```

## Prompt 7 — Jevons

```text
Implement the short-chain Jevons elementary index.

For matched products:
J = exp(mean(log(P_current/P_previous)))

Then:
I_current = I_previous * J

Initial reference:
I_reference = 100.

Do not use a long fixed-base average price ratio.

Add coverage checks and tests.
```

## Prompt 8 — Weights

```text
Implement versioned route and lead-time weights.

Validate:
sum(route_weights) = 1
sum(lead_time_weights) = 1

Do not use scraped row counts as weights.

Support:
- DGCA passenger-share route weights,
- booking-based lead-time weights,
- provisional equal weights only as an explicit fallback.
```

## Prompt 9 — Aggregation

```text
Implement:

route_lead_index[r,l,t]

I_route[r,t] = sum_l W_l * I[r,l,t]

APIx[t] = sum_r W_r * I_route[r,t]

Store all intermediate calculations for auditability.
```

## Prompt 10 — Validation

```text
Implement automated APIx validation.

Check:
- weight sums,
- coverage,
- matched sample size,
- duplicate rate,
- missing rate,
- extreme price changes,
- route coverage,
- lead-time coverage,
- source concentration,
- reproducibility.

Generate a validation report.
```

## Prompt 11 — Dashboard/API

```text
Expose:
- daily indicator,
- weekly index,
- monthly index,
- route indices,
- lead-time indices,
- MoM,
- YoY,
- data-quality metrics.

Every response must include methodology_version and weight_version.
```

---

# 77. Final implementation dependency graph

```text
SCRAPERS
   ↓
RAW FARES
   ↓
SCHEMA VALIDATION
   ↓
NORMALIZATION
   ↓
QUALITY FILTER
   ↓
FINGERPRINT / DEDUPLICATION
   ↓
PRODUCT CLASSIFICATION
   ↓
MONTHLY PRODUCT PRICES
   ↓
MATCHING / REPLACEMENT
   ↓
SHORT JE VONS
   ↓
LEAD-TIME AGGREGATION
   ↓
ROUTE AGGREGATION
   ↓
APIx
   ↓
MoM / YoY
   ↓
DASHBOARD + API
   ↓
BACKTEST + SENSITIVITY
```

---

# 78. Critical methodological rules to freeze

The following rules should be treated as non-negotiable in the implementation:

1. **Never average all scraped rows directly.**
2. **Never use scraper row count as a statistical weight.**
3. **Never mix different fare qualities without a matching/quality rule.**
4. **Never treat sold-out as zero.**
5. **Never invent tax/base-fare components.**
6. **Never compare different currencies without conversion methodology.**
7. **Never use flight number alone as product identity.**
8. **Never silently remove genuine high fares.**
9. **Never silently change weights.**
10. **Never silently change methodology.**
11. **Never overwrite raw observations.**
12. **Always retain collection timestamp and travel date separately.**
13. **Always retain source/outlet.**
14. **Always retain evidence for each observation.**
15. **Use Decimal/high precision for monetary calculations.**
16. **Use short-chain Jevons at the elementary level.**
17. **Use weighted arithmetic aggregation at higher levels.**
18. **Use DGCA traffic as route representation only unless better expenditure weights exist.**
19. **Use official MoSPI expenditure weight for CPI integration.**
20. **Treat APIx as experimental until formally adopted.**

---

# 79. Final data checklist

Before coding the index engine, the project team should have:

### Required now

- [ ] Existing scraped airfare dataset
- [ ] Route list
- [ ] DGCA route passenger data
- [ ] Search date
- [ ] Travel date
- [ ] Lead days
- [ ] Airline
- [ ] Flight number
- [ ] Departure/arrival
- [ ] Duration
- [ ] Stops
- [ ] Cabin
- [ ] Fare family
- [ ] Baggage condition
- [ ] Total fare
- [ ] Currency
- [ ] Availability
- [ ] Source
- [ ] Source itinerary ID
- [ ] Raw evidence/snapshot
- [ ] Collection timestamp

### Required for final statistical weighting

- [ ] Lead-time booking shares
- [ ] Route weights / DGCA traffic
- [ ] Official CPI airfare expenditure weight
- [ ] Sector weights if publishing rural/urban/combined variants
- [ ] Source/outlet market shares if available

### Strongly recommended

- [ ] Flight schedules
- [ ] Airport metadata
- [ ] Holiday calendar
- [ ] Airline capacity
- [ ] Historical airfare benchmark
- [ ] 2024 historical airfare observations for true 2024=100
- [ ] 30-day/longer validation benchmark

---

# 80. Final recommended architecture

The final project should therefore be viewed as a **statistical production pipeline**, not merely a scraping application.

The scraper is only the data-collection layer.

The statistically important part is:

```text
representative sampling
        +
homogeneous product definition
        +
quality-controlled price observations
        +
matched-product methodology
        +
short-chain Jevons
        +
documented weights
        +
higher-level Young-style aggregation
        +
auditability
        +
validation
```

This structure is the strongest route for making the project defensible as a final-year statistical/engineering project and for demonstrating meaningful alignment with the current Indian CPI 2024 framework.

---

# 81. Source basis

### Indian official sources

1. Ministry of Statistics and Programme Implementation, **CPI 2024 Series — Frequently Asked Questions**.
2. Ministry of Statistics and Programme Implementation, **Expert Group Report / Report on Comprehensive Updation of CPI**, including the discussion of the 2024 base, Jevons short index, Young index, online airfare collection and advance-purchase design.
3. MoSPI CPI 2024 metadata and official CPI portal.
4. HCES 2023–24 expenditure publications.

### International methodological sources

5. Eurostat, **HICP Methodological Manual 2024 edition**, especially the chapters on weights, index calculation, sampling, product comparability, replacements and selected service groups including flights.
6. Eurostat, **Practical Guidelines for Web Scraping for HICP**, November 2020, especially sections on targeted/bulk scraping, product-offer definition, repeated monthly observations, data quality, source relationships and index compilation.

The Indian CPI 2024 documents govern the Indian alignment. The Eurostat documents are used for additional web-scraping and price-index methodological guidance; they should not be represented as Indian law or as replacing MoSPI's methodology.
