# PPT Guide: How the Airfare Price Index is Calculated

This document provides a clean, evaluator-friendly explanation and generalized visual flowchart designed specifically for slide presentations (PPT). It uses abstract, standard terminology (Routes, Lead Times, Providers, Flights) instead of single examples, while keeping the logic intuitive and mathematically sound.

---

## 1. Generalized Slide Flowchart: "From Scraped Quotes to National Airfare Index"

```mermaid
flowchart TD
    classDef raw fill:#EFF6FF,stroke:#3B82F6,stroke-width:2px,color:#1E3A8A;
    classDef proc fill:#F0FDF4,stroke:#10B981,stroke-width:2px,color:#064E3B;
    classDef agg fill:#FFFBEB,stroke:#F59E0B,stroke-width:2px,color:#78350F;
    classDef final fill:#FEF2F2,stroke:#EF4444,stroke-width:2px,color:#7F1D1D;

    subgraph Level1["Level 1: Multi-Provider Reconciliation (Per Flight)"]
        A1["Flight i Quote on Provider A"]:::raw
        A2["Flight i Quote on Provider B"]:::raw
        A1 & A2 --> B["Average Across Providers\n→ 1 Verified Consensus Price per Flight"]:::proc
    end

    subgraph Level2["Level 2: Horizon Representative Price (Per Route & Lead Time)"]
        B --> C["All Flights Operating on Route r at Lead Time l\n(Flight 1, Flight 2, ... Flight N)"]:::raw
        C --> D["Geometric Mean (GM) Across All Flights\n→ Representative Price for Lead Time l: P(r, l)"]:::proc
    end

    subgraph Level3["Level 3: Route Level Price (All 6 Lead Horizons)"]
        D --> E["6 Advance-Purchase Horizons for Route r\n(T+1, T+7, T+15, T+21 ★, T+30, T+45)"]:::raw
        E --> F["Weighted Average by Booking Behavior (W_l)\n(Early vs. Urgent Bookings; T+21 MoSPI Checkpoint = 15.2%)\n→ 1 Representative Price for Route r: P(r)"]:::agg
    end

    subgraph Level4["Level 4: National Airfare Level (All-India Basket)"]
        F --> G["All 60 Domestic Scheduled Routes\n(Route 1, Route 2, ... Route 60)"]:::raw
        G --> H["Weighted Average by DGCA Passenger Volume (W_r)\n(57% National Traffic Coverage; Busiest Corridors Carry Higher Weight)\n→ 1 All-India Representative Fare: P_National"]:::agg
    end

    subgraph Level5["Level 5: National Index & Macroeconomic CPI Impact"]
        H --> I["National Airfare Price Index\nIndex = (P_National, t ÷ P_Base) × 100\n(Reference Base: 2024 = 100)"]:::final
        I --> J["MoSPI CPI Contribution (Percentage Points)\nInflation Rate × 0.02951% Household Expenditure Weight"]:::final
    end
```

---

## 2. The 5 Generalized Steps Explained Simply (For Evaluators)

### Step 1: Same Flight across Different Providers
- **The Problem:** The same physical flight (e.g., Airline X, Flight Y) may show slightly different prices across booking platforms (OTAs, airline direct APIs) due to convenience fees or markups.
- **The Fix:** Take the **average across providers**.
- **Result:** Each scheduled flight receives **one clean, consensus market fare**.

### Step 2: Multiple Flights in a Specific Lead-Time Horizon
- **The Problem:** On any given route and booking window (e.g., Route $r$ booked $l$ days ahead), there are multiple flights operating across different times of the day.
- **The Fix:** Calculate the **Geometric Mean (GM)** across all flights in that horizon.
- **Result:** **One representative price $P(r, l)$** for that specific lead-time window without upward skew from high-end outlier tickets.

### Step 3: Combining All 6 Booking Lead-Time Horizons
- **The Problem:** Urgent last-minute bookings (T+1) are expensive, while advance bookings (T+45) are cheaper. Fares naturally change as departure approaches.
- **The Fix:** Take a **weighted average** across all 6 horizons using empirical booking behavior weights ($W_l$):
  - **T+1**: $5.09\%$ (Urgent / last-minute travel)
  - **T+7**: $13.72\%$ (Short advance window)
  - **T+15**: $15.00\%$ (Mid advance window)
  - **T+21**: **$15.19\%$ (Official MoSPI CPI domestic checkpoint)**
  - **T+30**: $24.80\%$ (Standard leisure advance)
  - **T+45**: $26.20\%$ (Early planning)
- **Result:** **One representative price $P(r)$ for the route**.

### Step 4: Combining All Routes Across India
- **The Problem:** High-density trunk corridors carry millions of flyers, while smaller regional sectors carry fewer. Equal weighting would distort the national picture.
- **The Fix:** Take a **weighted average** of all 60 routes using official **DGCA CY2024 Passenger Traffic Shares** ($W_r$).
  - Captures **91.99M passengers** ($57.02\%$ of all Indian domestic air travel).
  - Stations in dual-airport cities (e.g., Goa Dabolim vs. Goa Mopa) are maintained separately.
- **Result:** **One All-India Representative Airfare Price $P_{\text{National}}$**.

### Step 5: Index Compilation & CPI Integration
- **Index Relative:**
  $$\text{Index}_t = \left(\frac{P_{\text{National}, t}}{P_{\text{Base}}}\right) \times 100 \quad (\text{Base } 2024 = 100)$$
- **Macroeconomic CPI Contribution:**
  $$\Delta \text{CPI}_{\text{pp}} = \text{Airfare Inflation Rate (\%)} \times 0.0002951$$
  *(Airfare represents 0.02951% of total Indian household consumption per MoSPI CPI 2024 Annexure 5.3d).*

---

## 3. Evaluator Q&A Cheat Sheet (Talking Points)

- **Q: Why use Geometric Mean (GM) instead of a simple average across flights?**
  - *Answer:* Simple arithmetic averages get distorted if a few premium tickets spike. Geometric Mean gives the true central tendency of the consumer market and eliminates upward bounce (aligned with Eurostat HICP and MoSPI standards).
- **Q: Why track 6 lead times, and why is T+21 special?**
  - *Answer:* Airline dynamic pricing varies heavily by advance purchase. MoSPI's upcoming CPI 2024 explicitly specifies **21 days advance booking** as the national domestic reference checkpoint. Tracking T+1 through T+45 captures the complete yield curve while keeping T+21 strictly isolated.
- **Q: Where do the route weights come from?**
  - *Answer:* Official DGCA CY2024 city-pair passenger statistics. Routes carrying more domestic passengers naturally have a higher weight in the national index.
