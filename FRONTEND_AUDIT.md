# APIx Frontend Architecture & UI/UX Audit Report
**Statistical Data Product Evaluation & Integrity Audit**
*Document Version: 1.0.0 | Date: 2026-09-28*

---

## Executive Summary

This audit establishes a complete architectural, data integrity, and visual baseline for the **APIx (Indian Airfare Price Index)** frontend application.

The primary objective is to evaluate the existing frontend against the requirements of a credible, professional macroeconomic and statistical data product (comparable to official statistical portals such as MoSPI, RBI DBIE, US BLS, or Eurostat HICP), while preserving the existing layout and information architecture.

### Key Audit Findings
1. **Critical Data Integrity Issues (P0):**
   - The collection audit strip (`RecordStrip.tsx`) flags successful runs as errors due to a case-sensitive status mismatch (`COMPLETED` vs `'ok'`), falsely showing "0 of 1 runs ok".
   - The interactive "What If" weight simulator ignores lead-time weights in client-side recalculation; modifying lead weights causes zero change in the displayed series.
   - Client-side trigonometric sine and cosine waves (`Math.sin()`) are used to fabricate historical price movements across 54 routes and sparklines, presented alongside real DGCA traffic volumes.
   - The 30-Day Market Backtest table in `MethodView.tsx` contains hardcoded numbers (MAE 1.3302 vs 5.0933, RMSE 1.7056, Volatility 1.48%, Correlation 0.8659) that directly contradict the actual backend data in `backtest_results.json`.
2. **Major Visual & Architectural Inconsistencies (P1):**
   - An "Akasa-inspired" landing page (`LandingView.tsx`) with airline livery, 200+ lines of airplane SVGs, bright orange branding (`#FA5A00`), and fake mock authentication was introduced, violating the strict vellum/ink "chart paper" design tokens codified in the master specification.
   - Route colors are inconsistent between `IndexView.tsx` and `BookingCurvesView.tsx`, causing the same route (e.g. DEL-HYD) to appear in conflicting colors.
   - Content container maximum widths fluctuate arbitrarily between 820px, 940px, and 1200px across tabs.
3. **Information Integrity & Methodology (P1/P2):**
   - The application claims "MoSPI CPI 2024 Compliant" and "Eurostat HICP 2024 Aligned" in multiple badges and headings, overclaiming official compliance rather than stating methodology alignment.
   - Borrowed bond-market vocabulary ("Yield curves") is used instead of accepted aviation economic terminology ("Advance-Purchase Booking Curves").

---

## 1. Page & Route Inventory

The active application is a Vite + React SPA located in `web/` (controlled by `App.tsx` tab state):

| Route / Tab ID | View Component | Status | Layout Type & Primary Role |
| :--- | :--- | :--- | :--- |
| `landing` | `LandingView.tsx` | Active (Default) | Split modal with Akasa-style airplane graphics & mock authentication. |
| `overview` | `OverviewView.tsx` | Active | Editorial prose landing explaining methodology, coverage stats, and route list. |
| `index` | `IndexView.tsx` | Active | Core dashboard: headline sentence, main SVG time-series chart, route sparkline strip, lead-time small multiples, what-if weights, and collection record strip. |
| `curves` | `BookingCurvesView.tsx` | Active | Small multiples grid of advance-purchase curves (T+45 to T+1), late-booking premium chart, and data table. |
| `method` | `MethodView.tsx` | Active | 9-section formal technical documentation, formulas, DGCA Top-60 table, quality gates, backtest evaluation, and audit logs. |
| *(unrouted)* | `Phase28View.tsx` | Orphaned | Legacy single-route (DEL-BOM) production dashboard. Not referenced in `App.tsx`. |
| *(unrouted)* | `LeadTimeView.tsx` | Orphaned | Legacy standalone lead-time view. Not referenced in `App.tsx`. |
| *(unrouted)* | `DataView.tsx` | Orphaned | Legacy standalone raw observations table. Not referenced in `App.tsx`. |

---

## 2. Major Reusable Components

| Component | File Path | Usage & State | Assessment |
| :--- | :--- | :--- | :--- |
| `WeightBar` | `web/src/components/WeightBar.tsx` | Active (`IndexView`) | Segmented weight bar with draggable handles and steppers. **Issue:** Only hardcodes 3 routes; ignores lead weights in main chart math. |
| `RecordStrip` | `web/src/components/RecordStrip.tsx` | Active (`IndexView`) | Pipeline run history tick bar. **Issue:** Status matching bug flags `COMPLETED` as an error. |
| `WeightsPanel` | `web/src/components/WeightsPanel.tsx` | Orphaned / Unused | Legacy slider panel for 4 lead days. Obsolete CSS variables. |
| `RoutePanel` | `web/src/views/BookingCurvesView.tsx` | Inline in view | Multi-curve SVG route panel. Displays single-point rings and late premium pill. |
| `PremiumChart` | `web/src/views/BookingCurvesView.tsx` | Inline in view | Small comparative chart. Breaks when only 1 date exists. |

---

## 3. Data Classification: Provenance of All Displayed Values

To guarantee credibility as an economic data product, every displayed metric is categorized by source:

### A. Real Production Data (Authoritative)
- **DGCA CY2024 Passenger Volumes, National Shares & Ranks:** Sourced from official DGCA scheduled city-pair statistics (`DGCA_TOP60_ROUTES` in `web/src/data/dgcaTop60.ts` and `/api/methodology`).
- **Matrix Cell Coverage & Population Counts:** Loaded live via `/api/v1/coverage` (57 routes, populated cells out of 360 target).
- **DEL-BOM Live Fares:** Real scraped median/mean fares from EaseMyTrip DOM live capture (`/api/v1/lead-curves?route=DEL-BOM`).
- **Google Flights Top-60 Production Fares:** Real per-cell median, mean, and geometric mean fares across populated matrix cells (`/api/v1/matrix`).
- **Pipeline Collection Timestamps & Page Counts:** Live execution records from `/api/runs`.
- **Sample Raw Observations:** Real fare quotes loaded from `easemytrip_parsed_data.json` via `/api/observations`.

### B. Synthetic Demonstration Data
- **30-Day Historical Backtest:** Generated series in `backtest_results.json` evaluated via `/api/v1/backtest`.
- **4-Regime Weighting Sensitivity Divergence:** Calculated variants in `sensitivity_results.json` via `/api/v1/sensitivity`.
- **Single Observation Date Baseline:** Curves stamped with `'2026-09-22'` in `BookingCurvesView.tsx`.
- **Trigonometric Interpolations:** Client-side `Math.sin()` / `Math.cos()` waves used in `IndexView.tsx` for DEL-BLR, BOM-BLR, and pre-backtest dates.
- **Synthesized Sparklines:** 60-day sparklines for 54 routes generated using character-code arithmetic and sine offsets.

### C. Static UI Text
- Econometric methodology explanations, 9-step aggregation formulas, and axiom cards in `MethodView.tsx`.
- Introductory narrative and problem definition in `OverviewView.tsx`.
- MoSPI CPI 2024 airfare expenditure weight constant (`0.02951%`, COICOP `07.3.3.1.2.01`).
- Axis titles, glossary definitions, and table captions.

### D. Hardcoded Placeholder Data
- Default route weights `{ 'DEL-BOM': 0.35, 'DEL-BLR': 0.35, 'BOM-BLR': 0.30 }` in `IndexView.tsx` and `WeightBar.tsx`.
- Future-dated mock index values for `2026-10-03` (`101.88`, `100.45`, `99.82`, `momRate = 0.05`).
- Static backtest metrics in `MethodView.tsx` Section 8 table (e.g. MAE `1.3302 vs 5.0933`, RMSE `1.7056`, Volatility `1.48%`, Correlation `0.8659`).
- Static route change percentages (`+1.9%`, `+0.4%`, `-0.2%`) in `IndexView.tsx`.
- Static maxDate `'2026-09-22'` and sensitivity divergence `0.26` in `IndexView.tsx`.
- Hardcoded "Festival advance demand" annotation in `IndexView.tsx`.
- Mock user credentials (`analyst@aviation.gov.in`, `admin@apix.gov.in`) in `LandingView.tsx` and `App.tsx`.

---

## 4. Detailed Audit Findings by Dimension

### 4.1 All Hardcoded Values that Should Come from Backend/API
1. **[P0] `IndexView.tsx` (Lines 78–82):** `DEFAULT_ROUTE_WEIGHTS` hardcodes `{ 'DEL-BOM': 0.35, 'DEL-BLR': 0.35, 'BOM-BLR': 0.30 }`. Must be loaded from `/api/methodology` or `dgcaTop60.ts`.
2. **[P0] `IndexView.tsx` (Lines 261–266, 346–350):** `delBomVal = 101.88`, `delBlrVal = 100.45`, `bomBlrVal = 99.82`, `momRate = 0.05`. Hardcoded fallback values must come from `/api/v1/airfare-index`.
3. **[P0] `MethodView.tsx` (Lines 720–752):** Backtest comparison table hardcodes static strings that diverge from `backtest_results.json`. Must bind directly to `backtest.summary`.
4. **[P1] `IndexView.tsx` (Line 469):** `maxDev = Math.max(...diffs, 0.26); maxDate: '2026-09-22'`. Must bind to `/api/v1/sensitivity`.
5. **[P2] `IndexView.tsx` (Line 1075):** `route === 'DEL-BOM' ? '+1.9%' : route === 'DEL-BLR' ? '+0.4%' : '-0.2%'`. Must calculate actual MoM change per route or display `—` if not available.
6. **[P2] `IndexView.tsx` (Line 1374):** Hardcoded string `"See all 57 route booking curves →"`. Must dynamically reflect `availableRoutes.length`.

### 4.2 Static / Mock / Demo Data Displayed
1. **[P0] `IndexView.tsx` (Lines 258–275):** Client-side trigonometric formulas generate synthetic series for DEL-BLR, BOM-BLR, and pre-backtest dates.
2. **[P0] `IndexView.tsx` (Lines 580–584):** Sparklines for 54 routes are synthesized via `Math.sin((idx + route.charCodeAt(0)) * 0.28) * 0.65`.
3. **[P1] `LandingView.tsx`:** Entire authentication system is a client-side mock storing JSON in `localStorage`.
4. **[P2] `BookingCurvesView.tsx` (Line 491):** Hardcodes `obs_date: '2026-09-22'` for every route curve.

### 4.3 Styling Duplication & Inconsistencies
1. **[P1] Landing vs App Visual Theme Clash:** `LandingView.tsx` introduces 850+ lines of `.akasa-*` CSS with rounded pills (`border-radius: 20px`), cards with drop shadows (`box-shadow: 0 20px 40px -15px rgba(0,0,0,0.1)`), and vibrant Akasa orange (`#FA5A00`). This completely clashes with the flat, zero-shadow, zero-pill vellum/ink chart-paper design system.
2. **[P2] Duplicate Search & Filter Bars:** Filter pills and search inputs are implemented 4 separate times with inline styles or divergent CSS in `IndexView` Section 3, `IndexView` Section 4, `BookingCurvesView`, and `MethodView`.
3. **[P2] Competing Table Classes:** `MethodView` uses `.method-table`, `.dgca-table-wrap table`, and `.run-log-table`, each with distinct padding, background, and font sizes, while `IndexView` and `BookingCurvesView` use `.chart-data-table`.

### 4.4 Alignment & Spacing Problems
1. **[P1] Inconsistent Page Max-Widths:** `OverviewView.tsx` sets `maxWidth: 820px`, `MethodView.tsx` sets `maxWidth: 940px`, while `IndexView.tsx` and `BookingCurvesView.tsx` expand to full width (`1200px`). Switching tabs causes jarring layout jumps.
2. **[P1] Header Collisions on Tablet (< 1024px):** Header has fixed height `48px` without wrapping. The brand, 5 nav tabs, run status, and auth pill collide and push elements off-screen on screens under 1024px.
3. **[P2] Route Strip Grid Overflow:** `IndexView.tsx` line 1105 uses a fixed 6-column grid (`160px 130px 85px 65px 1fr auto`) requiring > 600px minimum width, breaking on mobile screens.
4. **[P2] Small Multiples Panel Cramping:** When grid panels scale to 230px on small screens, inner plotting width is 158px, leaving only ~26px between the 6 lead day labels.

### 4.5 Typography Inconsistencies
1. **[P2] Heading Hierarchy Mismatch:** `OverviewView` and `BookingCurvesView` use Newsreader Serif for `h1` (headline) and B612 Monospace for `h2` (16px, bold), whereas `MethodView` uses Newsreader Serif for `h1` (32px) and styled section cards with flex headers for `h2`.
2. **[P2] Missing Tabular Numerals:** Table cells, tooltips, chart tick labels, and stepper buttons omit `.font-num` (`font-variant-numeric: tabular-nums`), causing numeral jitter.
3. **[P3] Leftover Template Fonts:** `App.css` contains leftover CSS rules from the default Vite template.

### 4.6 Color Inconsistencies
1. **[P1] Conflicting Route Palette Assignment:** `IndexView.tsx` (`DYNAMIC_PALETTE`, 13 colors) and `BookingCurvesView.tsx` (`PALETTE`, 16 colors) use different color arrays and hashing algorithms. As a result, routes like `DEL-HYD` or `BLR-DEL` render in conflicting colors between the Index and Booking Curves views.
2. **[P1] Akasa Palette Intrusion:** `LandingView.tsx` uses bright orange (`#FA5A00`, `#FF7A00`) and slate blues (`#0F172A`, `#334155`), which are absent from the rest of the application.
3. **[P2] Poor Contrast in Dynamic Colors:** Palette entries `#F57F17` (amber) and `#827717` (olive) fail WCAG AA contrast standards on light vellum background (`#F0F2EE`).

### 4.7 Border / Radius / Shadow Inconsistencies
1. **[P1] Card & Shadow Violations:** While the core design token guideline specifies flat borders (`--contour: #C9D0CB`) with zero radius and zero drop shadows, `LandingView.tsx` uses `border-radius: 16px`, `box-shadow`, and gradient fills.
2. **[P2] Pill Radius Inconsistencies:** Badges in `MethodView` use `border-radius: 3px`, the user pill in `App.tsx` uses `border-radius: 16px`, and buttons in `LandingView` use `border-radius: 20px`.

### 4.8 Misleading, Generic, or AI-Generated Charts
1. **[P0] Mathematical Waveforms on Main Chart:** Trigonometric sine waves generated in `IndexView.tsx` mimic real inflation dynamics for DEL-BLR and BOM-BLR without disclosure.
2. **[P1] Broken Late-Booking Premium Chart:** When only a single observation day is present, `PremiumChart` renders solitary floating dots with no lines, appearing broken.
3. **[P1] Arbitrary Event Annotations:** A colored band between `2026-09-14` and `2026-09-18` labelled "Festival advance demand" is hardcoded in JSX without backing data.
4. **[P2] Decorative Overview Sketch:** The static SVG curve in `OverviewView.tsx` is an artificial drawing rather than a real data graphic.

### 4.9 Tables Needing Structural Improvement
1. **[P0] Backtest Performance Table Discrepancies:** `MethodView.tsx` Section 8 table displays hardcoded figures that contradict `backtest_results.json`.
2. **[P2] DGCA Top-60 Table Usability:** Capped in an inner scroll container; lacks sorting by passenger volume, rank, share %, or weight; lacks sticky header.
3. **[P2] Raw Observations Table Usability:** Shows first 30 rows with no pagination or column sorting.

### 4.10 Responsive & Layout Problems
1. **[P1] Site Header Breakage below 1024px:** Nav tabs, status, and auth pill collide.
2. **[P1] Index Chart Right Margin on Mobile:** Direct end-of-line labels (`overall`, `DEL-BOM`, `DEL-BLR`, `BOM-BLR`) stack or clip on screens under 480px.
3. **[P2] Basket Route Strip Stacking:** Needs responsive flex-wrap or horizontal scrolling on mobile viewports.

### 4.11 Missing Loading, Empty, and Error States
1. **[P0] RecordStrip Status Bug:** Falsely identifies `status: "COMPLETED"` as an error because it checks for `status === 'ok'`.
2. **[P0] Silent Error Swallowing in MethodView:** `api.methodology()`, `api.observations()`, `api.getBacktest()`, and `api.getSensitivity()` swallow errors in empty catch blocks (`.catch(() => {})`).
3. **[P1] Silent Fallbacks in IndexView:** If backend fails, `IndexView` silently defaults to hardcoded values without warning the user.
4. **[P2] Thin-Data Degradation in Curve Panels:** When only 1 lead horizon is populated, a single point renders with no indication of why other horizons are absent.

### 4.12 Accessibility Issues
1. **[P2] Keyboard Inaccessibility on Route Strips:** Clicking a route strip in `IndexView` or a curve in `BookingCurvesView` lacks `onKeyDown` handlers (Enter / Space).
2. **[P2] Header Tablist Keyboard Navigation:** Arrow key navigation between tabs is not implemented.
3. **[P2] Color Contrast Failures:** Yellow and amber palette entries on vellum background fail WCAG AA contrast.

### 4.13 Terminology & Methodological Honesty
1. **[P1] False Compliance Badges:** "MoSPI CPI 2024 Compliant" and "Eurostat HICP 2024 Aligned" claim official government certification rather than methodological alignment.
2. **[P2] Jargon Overclaiming:** "Yield curves" should be replaced by "Advance-Purchase Booking Curves".
3. **[P2] Marketing Language:** "apix ELEVATE" and "Instant Demo: MoSPI Principal Analyst" should be removed.

### 4.14 Frontend/Backend Data-Flow Problems
1. **[P0] Lead Weights Disconnected from Index Math:** Adjusting lead weights in `WeightBar` does not affect `fullDailySeries`.
2. **[P0] WeightBar Route Mismatch:** Only 3 routes are available in `WeightBar`, while 57 routes are displayed in the basket.
3. **[P0] MethodView Disconnected from API State:** Fetches `backtest` and `sensitivity` but renders hardcoded HTML.
4. **[P2] Directional Route Keying Inconsistency:** Inconsistent usage of `DEL-BLR` vs `BLR-DEL` requires runtime key normalization.

### 4.15 Unnecessary Visual Decoration
1. **[P1] Decorative Akasa Airplane SVG:** 200+ lines of raw SVG markup in `LandingView.tsx` that degrades the statistical seriousness of the application.
2. **[P1] Fake Authentication Gateway:** Fake email/password inputs, 256-bit encryption claims, and demo user buttons that provide no actual security or function.
3. **[P2] Arbitrary Demand Annotation:** Fake festival demand band on the main chart.

### 4.16 Reusable Component Opportunities
1. **`RouteFilterBar`:** Consolidate the 4 separate search and hub filter implementations into a single component.
2. **`ToggleGroup`:** Standardize the toggle button groups used in Index and Booking Curves views.
3. **`DataTableContainer`:** Standardize the `<details className="chart-data-table">` pattern.
4. **`RouteBadge`:** Standardize the Route Code + Rank Badge + City Pair format.

---

## 5. Prioritized Fix Plan

### Phase 1: Correctness & Data Integrity (P0) — Immediate Priority
1. **Fix `RecordStrip.tsx` Status Logic:** Accept `status.toLowerCase() === 'completed'` or `'ok'` as valid; display correct run counts without false exception flags.
2. **Connect Lead Weights to Index Calculation:** Update `IndexView.tsx` to compute the overall index using both route weights and lead-time weights.
3. **Eliminate Client-Side Synthetic Waveforms:** Replace `Math.sin()` formulas with genuine series from `/api/v1/backtest` and `/api/v1/matrix`, or explicitly mark thin/synthetic routes with clear provenance badges.
4. **Bind `MethodView.tsx` to Backend Backtest Data:** Replace hardcoded static HTML table values with live values from `backtest.summary`.
5. **Add Global API Error Handling:** Replace silent `.catch(() => {})` handlers with an error notification state across all views.
6. **Synchronize WeightBar with DGCA Basket:** Expand `WeightBar.tsx` to support the Top-10 or full basket routes dynamically.

### Phase 2: Information Architecture & Visual Discipline (P1)
7. **Retire `LandingView.tsx` as Default Screen:** Make `OverviewView.tsx` the default entry point. Fold authentic product identity into the Overview page and remove the fake authentication system.
8. **Align Container Max-Widths:** Standardize all page views to `--max-w: 1200px` with consistent padding.
9. **Synchronize Route Palette Assignment:** Create a single shared route-to-color lookup map in `web/src/lib/palette.ts` used by both `IndexView` and `BookingCurvesView`.
10. **Fix Header Responsiveness:** Allow nav items to adapt cleanly on viewports under 1024px.
11. **Gracefully Handle Single-Date Curves:** In `BookingCurvesView.tsx`, handle single observation dates cleanly without broken chart lines.

### Phase 3: Consistency & Polish (P2)
12. **Extract Shared `RouteFilterBar` Component:** Replace the 4 duplicated search/filter bars with one reusable component.
13. **Correct Terminology:** Replace "Yield curves" with "Booking curves", and replace compliance claims with honest alignment statements ("Methodology aligned with MoSPI CPI 2024 principles").
14. **Add Keyboard Accessibility:** Implement Enter/Space activation on route strips and curve SVG elements.
15. **Standardize Tables & Numbers:** Apply `.font-num` to all numeric values and harmonize table classes.
16. **Remove Hardcoded Chart Annotations:** Remove fake festival demand bands.

### Phase 4: Codebase Cleanup (P3)
17. **Remove Orphaned Views:** Delete `Phase28View.tsx`, `LeadTimeView.tsx`, `DataView.tsx`, `WeightsPanel.tsx`, and `App.css`.
18. **Add Table Export:** Provide CSV download options for index history and DGCA Top-60 tables.

---

## 6. File Modification Manifest

### Files That Would Need Modification
- `web/src/App.tsx` (Default tab routing, header responsive layout, auth cleanup)
- `web/src/index.css` (Remove `.akasa-*` styles, harmonize container widths, table styles)
- `web/src/components/RecordStrip.tsx` (Fix `COMPLETED` run status matching)
- `web/src/components/WeightBar.tsx` (Dynamic basket routes, link to lead-time weighting)
- `web/src/views/IndexView.tsx` (Fix lead weight recalculation, remove sine waves, synchronize colors)
- `web/src/views/BookingCurvesView.tsx` (Synchronize route palette, fix single-date premium chart)
- `web/src/views/MethodView.tsx` (Bind backtest table to live API, fix silent catch blocks, correct terminology)
- `web/src/views/OverviewView.tsx` (Ensure max-width consistency with Index and Curves)
- `web/src/api.ts` (Remove hardcoded fallback runs, add robust status typings)

### Files That Should NOT Be Modified
- `web/src/data/dgcaTop60.ts` (Authoritative DGCA CY2024 baseline matrix data — fully verified)
- `web/src/data/dgca_top60.json` (Immutable regulatory reference JSON)
- `apps/api/src/main.py` (Backend API routes and data loaders are working and verified)
- `apps/scraper/src/**/*` (Scraper engine, canonical models, and pipeline ingestion)
- `runtime/top60_fare_observations.json` (Real production scrape dataset)
- `runtime/top60_observation_classification.json` (Production data classification)
- `backtest_results.json` (Ground-truth econometrics backtest results)
- `sensitivity_results.json` (Ground-truth 4-regime sensitivity analysis)
- `DEL_BOM_*` data and methodology files (Pilot reference artifacts)
