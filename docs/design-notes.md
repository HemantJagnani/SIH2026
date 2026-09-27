# APIx Design Notes — Frontend Completion (v3)

## 1. Information Architecture (IA) Change
The top navigation is simplified to four flat, plain-word destinations with no nested tab bars layered on top:

```
APIx        Overview   Index   Booking curves   Method
```

- **Overview** (Default route): First-time visitor landing page explaining what APIx is, the 200–400% intraday dispersion problem, truthful live vs. synthetic status per route, an illustrative sketch, and outbound links to Index and Method.
- **Index**: Headline prose sentence, price index trajectory chart, what-if weight adjustments, and the 3-route basket table directly beneath the chart.
- **Booking curves**: Advance-purchase curves with clean empty states, minimum-range scaling, and standardized label formatting.
- **Method**: Prose-first explanation of formula, weights (clearly marked `assumed`), statistical limitations, and the raw observations table folded inside a collapsed `<details>` block at the bottom.

---

## 2. Rationale for Removals & Corrections

### 2.1 Badges ("CPI 2024 COMPATIBLE", "MoSPI T+21 ALIGNED")
- **Action**: Completely deleted; no replacement badges.
- **Why**: Fabricated compliance claims. The project is an independent hackathon prototype with one live route (DEL-BOM) and synthetic history. Claiming official institutional alignment or MoSPI endorsement destroys credibility with economists, statisticians, and evaluators.

### 2.2 Invented Citations & Jargon (`(§63)`, "Yield curves", `(122)`)
- **Action**: Removed fake citation `(§63)`; replaced bond-market term "Lead-Time Yield Curves" with "Booking curves" / "Average price by lead time"; removed raw count `(122)` as a tab title.
- **Why**: Reaching for false institutional authority weakens the presentation. All labels must be plain sentence-case describing what they actually do.

### 2.3 "Real Data → DEL-BOM" Navigation Item
- **Action**: Removed from header navigation.
- **Why**: Styled like a promotional callout/ad with an arrow (forbidden by design rules). The reality of live DEL-BOM data belongs naturally in the Overview route-status table and the Index data-status prose.

### 2.4 Standalone "Data" Tab
- **Action**: Removed as a top-level nav item; folded into the Method page inside a `<details>` block (`All recorded fares (122)`).
- **Why**: Raw data rows are audit evidence supporting the methodology, not a primary destination. The table now includes scrape timestamp (`observed_at`) and computed lead time.

### 2.5 Stat-Tile Hero Box Grid
- **Action**: Removed bordered 4-box card grid and all-caps labels.
- **Why**: Violates the flat "chart paper" surface language and all-caps ban. Replaced with the generated headline sentence and an unbordered inline summary line.

### 2.6 Mislabeled Weights Status ("measured")
- **Action**: Changed lead-window weight status to `assumed`.
- **Why**: Equal 17% splits are an assumption, not an empirical measurement. Claiming an assumption is "measured" is a factual falsehood.

### 2.7 Pipeline Note: Carrier/Stop Templated Pricing Caveat
- **Note**: The live collector records fares per carrier and stop-count rather than per individual flight. A caveat has been explicitly added to the Method page's limitations list: *"Fares are currently recorded per carrier and stop-count rather than per individual flight."* Furthermore, all stored observations now record explicit observation timestamps (`observed_at`) and computed lead times.

