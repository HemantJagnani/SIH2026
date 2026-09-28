# AERIX Product Definition & Methodology Specification

**Version:** 1.0.0-PROD  
**Methodology Identifier:** `APIX_METHODOLOGY_V1`  
**Effective Date:** 2026-09-27  
**Project:** Development of a Real-time Airfare Price Index for India through Automated Web Scraping (CPI Augmentation)  

---

## 1. Scope & Primary Target Product

The AERIX Consumer Price Index (CPI) airfare component measures the pure price change over time for scheduled domestic passenger air transport in India, holding product characteristics strictly constant.

### 1.1 Minimum Core Product Definition
Each scraped price observation entering the primary CPI airfare index must satisfy the following immutable product attributes:

| Product Attribute | Required Specification | Rationale & CPI Compliance |
| :--- | :--- | :--- |
| **Market Scope** | Domestic India (`origin_iata` $\in$ India, `dest_iata` $\in$ India) | Indian CPI covers domestic household expenditure. |
| **Journey Type** | One-Way (`ONE_WAY`) | Standard elementary unit of domestic air passenger travel. |
| **Passenger Profile** | Exactly 1 Adult (`adults=1, children=0, infants=0`) | Standard adult consumer without age/concession restrictions. |
| **Cabin Class** | Economy (`ECONOMY`) | Represents $\sim 94\%$ of domestic passenger volume in India. |
| **Currency** | Indian Rupee (`INR`) | Domestic transaction currency. |
| **Price Concept** | **Mandatory Payable Consumer Total** (`total_fare`) | Total consumer price required to fly, inclusive of non-optional taxes, airport development fees (UDF/ADF), user development fees (PSF), fuel charges (YQ/YR), and goods & services tax (GST). Excludes optional ancillaries. |
| **Route** | Direct or valid connecting city-pair (e.g., `DEL–BOM`) | Fixed geographic market stratum. |
| **Travel Date** | Fixed scheduled departure date ($T_{travel}$) | Explicit calendar day. |
| **Lead-Time Class** | $L \in \{T+1, T+7, T+15, T+21, T+30, T+45\}$ | Captures dynamic pricing trajectory across lead time. |

---

## 2. Fare Family Architecture & Strata Policy

Airline reservation systems and online travel aggregators (OTAs) offer multiple fare tiers for a single flight itinerary (e.g., `Saver`, `EMTEXCLUSIVE`, `FlexiPlus`, `IndigoUpFront`). Silently mixing these into a single homogeneous price series would violate the fundamental Axiom of Item Homogeneity in index number theory, generating pseudo price volatility caused by product mix shifts rather than real price change.

### 2.1 The Two-Tier Strategy

AERIX implements **Strategy A (Fare-Family-Specific Product Strata)** combined with **Strategy B (Defined Qualifying Baseline Selection)**:

```
                                  [ Flight Itinerary ]
                                           │
         ┌─────────────────────────────────┴─────────────────────────────────┐
         ▼                                                                   ▼
[ Primary Headline Index ]                                     [ Product Strata Sub-Indices ]
(Lowest Mandatory Qualifying                                    (Independent Homogeneous Series)
       Baseline Fare)                                                        │
         │                                    ┌──────────────────┬───────────┴───────┬──────────────────┐
         │                                    ▼                  ▼                   ▼                  ▼
    e.g. "Saver"                      [ Standard Saver ]   [ Flexible Flexi ]   [ OTA Exclusive ]  [ Premium UpFront ]
   or lowest entry price                 (7kg / 15kg,        (Free seats/meals,    (Low cancel fee,   (Extra legroom,
                                       non-refundable)      reduced change fee)    free date change)   20kg baggage)
```

1. **Primary CPI Headline Airfare Index ($I_{AERIX}^{Headline}$):**
   * Employs the **Defined Qualifying Baseline Selection Rule**: selects the lowest mandatory payable standard economy fare per itinerary (typically `Saver` or `Value` or standard lowest card offer).
   * Ensures backward compatibility and represents the minimum entry price available to a price-conscious consumer.
2. **Detailed Product Strata Sub-Indices ($I_{AERIX}^{stratum}$):**
   * Observations are partitioned into 4 distinct homogeneous strata:
     1. **Stratum 1 (`STANDARD_SAVER`):** Basic economy; 7 kg cabin baggage, 15 kg check-in baggage; standard seat; non-refundable/strict cancellation penalty. (Includes: `Saver`, `Value`, `SpiceSaver`).
     2. **Stratum 2 (`FLEXIBLE_ECONOMY`):** Economy ticket with complimentary standard seat selection and meal, and reduced date-change penalty. (Includes: `Flex`, `FlexiPlus`, `Classic`, `SpiceFlex`).
     3. **Stratum 3 (`OTA_EXCLUSIVE`):** Aggregator-exclusive promotional corporate/retail fare featuring reduced cancellation fee (e.g. ₹999) and zero date-change fee. (Includes: `EMTEXCLUSIVE`, `Retail`).
     4. **Stratum 4 (`PREMIUM_UPFRONT`):** Economy ticket with dedicated front-row/extra legroom seat, complimentary hot meal, and enhanced check-in baggage allowance (20 kg). (Includes: `IndigoUpFront`, `SpiceMax`).
3. **Anti-Mixing Guarantee:** Under no circumstances are observations from Stratum 1 and Stratum 4 averaged together in an elementary geometric mean (Jevons) without explicit stratum classification.

---

## 3. Discount Semantics & Mandatory Price Integrity

Online aggregators and airlines frequently display strikethrough prices, instant bank discounts, and promo code vouchers. To maintain statistical integrity and avoid arbitrary price adjustments:

1. **Separation of Concerns:**
   * `displayed_fare`: The mandatory gross price rendered on the flight result card.
   * `mandatory_payable_fare`: The non-negotiable cash price required to complete the reservation without conditional eligibility.
   * `discount`: Promotional coupon or bank card discount amount (stored strictly as descriptive metadata).
   * `discount_type`: Type of discount (e.g., `PROMOTIONAL_COUPON_CODE`, `BANK_CREDIT_CARD`, `INSTANT_WALLET`).
2. **Mandatory Payable Price Rule:**
   * Promotional coupon text (e.g., *"Use code BOOKNOW to get extra Rs.220 instant discount"*) is **never automatically subtracted** from `total_fare`.
   * Gated or conditional discounts (requiring specific bank credit cards, promo codes, or loyalty points) do not apply to the general population and must NOT depress the official price index.
   * `total_fare` is strictly set to the **displayed mandatory payable price**.

---

## 4. Result Stream Stabilization Policy

Asynchronous frontend streaming in modern Angular/React single-page applications can result in partial card collection if scraping terminates prematurely. 

### 4.1 Stabilization Invariant
A search result is declared complete if and only if:
1. At least one non-skeleton flight card is detected.
2. Card count remains identical ($C_{t} == C_{t-1}$) for $N$ consecutive observations (`RESULT_STABILITY_REQUIRED`, default $3$).
3. Polling occurs at a bounded interval (`RESULT_STABILITY_INTERVAL`, default $2.0\text{s}$).
4. Total stabilization wait does not exceed a hard ceiling (`RESULT_MAX_WAIT`, default $30.0\text{s}$).

---

## 5. Non-Fabrication & Missingness Provenance Contract

In strict compliance with National Statistical Commission (NSC) standards:
* **Zero Fabrication:** If an unbundled price component (such as `base_fare`, `taxes`, `gst`, or `airport_charges`) is not explicitly rendered in the search results DOM, it **must remain `None` (NULL)**.
* **No Backward Calculation:** Estimating base fare or taxes by applying standard percentage formulas to `total_fare` is strictly prohibited.
* **Field Provenance:** Every field carries a metadata block indicating its collection status:
  * `OBSERVED`: Explicitly scraped from DOM text.
  * `UNAVAILABLE` (`SOURCE_TOTAL_ONLY`): Source only exposes the bundled total payable price.
  * `UNAVAILABLE` (`NOT_PRESENT_IN_DOM`): Field is not rendered by the portal in search listing mode.
