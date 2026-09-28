# Frontend P0 Correctness & Data-Integrity Fix Report

**Date:** 2026-09-28  
**Scope:** P0 Frontend Correctness and Data-Integrity Implementation  
**Status:** Complete & Verified  

---

## 1. Executive Summary

This report documents the implementation of the six P0 frontend correctness and data-integrity fixes identified during the comprehensive UI/UX audit of the AERIX Airfare Price Index dashboard. 

All modifications strictly adhered to the governance and data-integrity guidelines:
- **Zero UI Layout Reshuffling or Premature P1 Redesign:** The vellum and ink chart-paper aesthetic and structural hierarchy were strictly preserved.
- **Zero Backend / Scraper / Econometrics Modification:** `apps/api/`, `apps/scraper/`, `apps/econometrics/`, and all Python calculation engines remained completely untouched.
- **Zero Modification to Authoritative Datasets:** DGCA schedules, CY2024 passenger shares, and production scraped datasets (`runtime/top60_fare_observations.json`, `easemytrip_normalized_data.json`, `backtest_results.json`, `sensitivity_results.json`) were untouched.
- **Absolute Elimination of Synthetic / Trigonometric Numbers in Production Series:** All `Math.sin()` and `Math.cos()` price movements and fake sparklines were removed; missing series now render explicit `"Data unavailable"` and `"Insufficient observations"` notices.
- **Strict Adherence to Formula Standards:** $P_{\text{ref}}$ is never used as an index denominator.

---

## 2. Files Modified

| File Path | Nature of Change |
| :--- | :--- |
| `web/src/components/RecordStrip.tsx` | Status classification helper (`isRunSuccess`, `isRunPartial`, `isRunFailed`) with case-insensitive handling for `"COMPLETED"`, `"OK"`, and `"SUCCESS"`. |
| `web/src/components/WeightBar.tsx` | Dynamic basket derivation from `routeWeights` and `DGCA_TOP60_ROUTES`; removed hardcoded 3-route limitation; dynamic route descriptions and palette coloring. |
| `web/src/views/IndexView.tsx` | Replaced trigonometric series (`Math.sin`/`Math.cos`) with genuine `backtest.daily_series`; integrated BOTH route and empirical lead-time weights into What-If calculation; added explicit `"Insufficient observations"` and `"Data unavailable"` states; added visible error banner. |
| `web/src/views/MethodView.tsx` | Bound Section 8 (30-Day Market Backtest Performance) directly to `backtest.summary` from the API; bound sensitivity callout to `sensitivity.maximum_divergence_pts`; added restrained API error banner. |
| `web/src/views/BookingCurvesView.tsx` | Added explicit `error` state and restrained failure banner (`"Data unavailable — unable to retrieve the latest result."`) instead of silent empty fallback. |
| `web/src/views/OverviewView.tsx` | Replaced generic backend failure text with restrained statistical data product message (`"Data unavailable — unable to retrieve the latest result."`). |
| `web/src/api.ts` | Removed silent `.catch(() => {})` with hardcoded fallback run in `api.runs()`; errors now bubble to views for clear, honest state rendering. |
| `web/src/components/RecordStrip.test.ts` | Unit test suite verifying case-insensitive run status parsing (`COMPLETED`, `ok`, `SUCCESS`, `partial`, `failed`). |

---

## 3. Exact Fixes by Audit Item

### Item 1: `RecordStrip.tsx` — Run-Status Bug & "COMPLETED" Success
- **Issue:** The backend collector emits `"status": "COMPLETED"`. The frontend only checked `status === 'ok'`, displaying successful collection runs as errors/exceptions.
- **Fix:** Introduced exported helper functions:
  ```ts
  export function isRunSuccess(status: string | null | undefined): boolean {
    if (!status) return false;
    const s = status.trim().toLowerCase();
    return s === 'ok' || s === 'completed' || s === 'success';
  }
  ```
  Updated `okCount`, `exceptions`, and `Tick` rendering to use `isRunSuccess()`, `isRunPartial()`, and `isRunFailed()`.
- **Outcome:** Successful runs with `"status": "COMPLETED"` are now rendered as solid, filled successful ticks (`1 of 1 run ok`), with no spurious error ticks or exception banners.

### Item 2: `IndexView.tsx` — Lead-Time Weighting in What-If Simulator
- **Issue:** The What-If simulation only multiplied three route weights against route values; `leadWeights` state was completely ignored. Changing lead-time weights had zero effect on the calculated index.
- **Fix:** Formulated dynamic lead-time index scaling based on the official empirical lead-time relatives ($M(d)$ from `sensitivity_results.json` / MoSPI CPI 2024 specifications: T+1=107.7, T+7=104.7, T+15=101.2, T+21=103.0, T+30=101.7, T+45=101.7):
  ```ts
  const defLeadTotal = Object.entries(DEFAULT_LEAD_WEIGHTS).reduce(
    (sum, [d, w]) => sum + w * (EMPIRICAL_LEAD_FACTORS[Number(d)] ?? 100), 0
  );
  const curLeadTotal = Object.entries(leadWeights).reduce(
    (sum, [d, w]) => sum + w * (EMPIRICAL_LEAD_FACTORS[Number(d)] ?? 100), 0
  );
  const leadFactor = defLeadTotal > 0 ? curLeadTotal / defLeadTotal : 1.0;
  ```
  Each day's overall simulated index is:
  $$\text{simulatedOverall} = \left(\sum_r W_{\text{norm}}(r) \cdot R_t(r)\right) \times \text{leadFactor}$$
- **Outcome:** Modifying lead-time weights (e.g. increasing spot T+1 weight or decreasing advance T+30 weight) immediately and smoothly recalculates the overall index across the entire series.

### Item 3: `IndexView.tsx` — Removal of Fabricated Trigonometric Series
- **Issue:**
  1. Synthetic route daily movements were fabricated with `Math.sin(i * 0.3) * 0.35` and `Math.cos(i * 0.25) * 0.25`.
  2. The series was artificially back-cast to `2026-07-06` and forecast to `2026-10-03` using `Math.sin(t * Math.PI * 2) * 1.2` waves.
  3. Sparklines for all 54 non-pilot routes were fabricated via character-code sine formulas (`Math.sin((idx + route.charCodeAt(0)) * 0.28) * 0.65`).
- **Fix:**
  1. Completely deleted all trigonometric generation formulas and synthetic date extensions.
  2. Bounded the time-series strictly to genuine 30-day observations in `backtest.daily_series` (2026-08-24 to 2026-09-22).
  3. When an individual route lacks historical daily time-series observations, its daily series is set to `null`, and its sparkline explicitly renders:
     `<span style={{ fontStyle: 'italic' }}>Insufficient observations</span>`.
  4. Soloing a route without daily observations renders a clear notice:
     `"Data unavailable — insufficient daily observations for {route}."`
- **Outcome:** Zero sinusoidal fiction. Ground-truth backtest points are displayed with complete statistical integrity.

### Item 4: `MethodView.tsx` — Dynamic Binding of Backtest Metrics
- **Issue:** Section 8's 30-Day Market Backtest Performance table contained static hardcoded numbers instead of binding to the API.
- **Fix:**
  - Bound MAE to `backtest.summary.mean_absolute_error_mae` (1.3302) vs `naive_mae` (1.3669).
  - Bound RMSE to `backtest.summary.root_mean_squared_error_rmse` (2.3875) vs `naive_rmse` (2.4139).
  - Bound Daily Volatility to `backtest.summary.apix_daily_volatility_percent` (2.30%) vs `naive_scraped_daily_volatility_percent` (2.30%).
  - Bound Volatility Reduction Ratio to `backtest.summary.volatility_reduction_ratio` (1.00x).
  - Bound Benchmark Correlation to `backtest.summary.benchmark_correlation` (0.3583).
  - Bound Maximum Drawdown to `backtest.summary.maximum_drawdown_percent` (4.37%).
  - Bound Sensitivity callout to `sensitivity.maximum_divergence_pts` (0.2625 pts).
- **Outcome:** The MethodView table dynamically reflects actual econometric metrics returned by the backend engine.

### Item 5: Global API Error Handling
- **Issue:** Silent `.catch(() => {})` handlers suppressed network failures and substituted fake mock runs or fell back to static numbers.
- **Fix:**
  - In `api.ts`: Removed fallback run inside `runs()`. Errors now throw appropriately.
  - In `IndexView.tsx`: Added `error` and `loading` state. When APIs fail to load, a restrained banner is displayed:
    `"Data unavailable — unable to retrieve the latest result."`
  - In `MethodView.tsx`: Displaying restrained error banner and fallback table state when API data is unreachable.
  - In `BookingCurvesView.tsx`: Added `error` state and rendered restrained banner when coverage or matrix endpoints fail.
  - In `OverviewView.tsx`: Standardized failure text to `"Data unavailable — unable to retrieve the latest result."`.
- **Outcome:** Clean, restrained, institutional error handling adhering to statistical reporting best practices.

### Item 6: `WeightBar.tsx` — Dynamic Basket Derivation
- **Issue:** `WeightBar` was hardcoded to a 3-route model (`ROUTES = ['DEL-BOM', 'DEL-BLR', 'BOM-BLR']`) with fixed colors, descriptions, and a static title.
- **Fix:**
  - Removed `const ROUTES = [...]` constant.
  - Derived active routes dynamically:
    `const keys = mode === 'lead' ? [...LEAD_DAYS] : Object.keys(routeWeights);`
  - Dynamic description lookup from `DGCA_TOP60_ROUTES`:
    `match.origin ⇄ match.destination (share% DGCA share)`.
  - Dynamic palette color assignment using `getRouteColor(route, idx)`.
  - Dynamic toolbar title:
    `Route Basket Allocation (${keys.length} Corridors)` / `Lead Time Windows (${keys.length} Advance Tiers)`.
  - Preserved all divider dragging, keyboard navigation, steppers, and normalization.
- **Outcome:** `WeightBar` supports arbitrary DGCA route subsets dynamically while maintaining interaction fidelity.

---

## 4. Test Suite Execution & Results

### Frontend Test Suite (`vitest run` in `web/`)
```
 RUN  v5.0.1 C:/Users/Hemant Jagnani/OneDrive/Desktop/SIH2026/web

 ✓ src/lib/indexMath.test.ts (5 tests) 7ms
 ✓ src/components/RecordStrip.test.ts (5 tests) 6ms

 Test Files  2 passed (2)
      Tests  10 passed (10)
   Start at  18:37:08
   Duration  460ms
```
- **Result:** 10/10 tests passed (100%).

### Frontend Build Suite (`tsc -b && vite build` in `web/`)
```
vite v8.3.0 building client environment for production...
transforming...
✓ 237 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                                 0.65 kB
dist/assets/index-dv7ImT2R.css                                 29.80 kB
dist/assets/index-BCtLDc1e.js                                 398.89 kB
✓ built in 3.58s
```
- **Result:** TypeScript compile and Vite production bundle succeeded with 0 errors.

### Python Backend / Core Regression Suite (`pytest tests/ -q`)
```
........................................................................ [ 45%]
........................................................................ [ 91%]
..............                                                           [100%]
158 passed, 98 warnings in 66.64s (0:01:06)
```
- **Result:** 158/158 tests passed (100%).

---

## 5. Verification Checklist

| Requirement | Verification Check | Status |
| :--- | :--- | :---: |
| **RecordStrip recognizes COMPLETED** | Tested `isRunSuccess('COMPLETED')` case-insensitively; okCount displays `1 of 1 run ok` with no exceptions. | **VERIFIED** |
| **What-If lead-time weighting** | Verified lead weights scale the index dynamically via empirical lead relatives ($M(d)$); altering lead weights shifts overall series immediately. | **VERIFIED** |
| **No Math.sin/Math.cos in dashboard** | Verified automated AST/string search across `web/src` produced 0 occurrences of trigonometric series in production dashboard. | **VERIFIED** |
| **MethodView backtest numbers match backend** | Bound directly to `backtest.summary` (MAE=1.3302, RMSE=2.3875, Vol=2.30%, Drawdown=4.37%, etc.) and `sensitivity.maximum_divergence_pts` (0.2625 pts). | **VERIFIED** |
| **Visible error states on API failure** | Visible error banners render `"Data unavailable — unable to retrieve the latest result."` without silent fallback to mock numbers. | **VERIFIED** |
| **WeightBar reflects actual basket** | Dynamic keys from `routeWeights`; dynamic DGCA route metadata lookup; dynamic corridor count display. | **VERIFIED** |
| **$P_{\text{ref}}$ is never an index denominator** | Verified arithmetic and geometric aggregations use only base-period levels and weights; $P_{\text{ref}}$ is absent from denominators. | **VERIFIED** |
| **No production data files modified** | `git status --porcelain` confirms 0 changes to `runtime/top60_fare_observations.json`, `backtest_results.json`, or backend code. | **VERIFIED** |

---

## 6. Remaining Observations & Next Steps

1. **Backend Integration:** In full production, when all 60 DGCA routes accumulate daily backtest histories in `backtest.daily_series`, the frontend will automatically render sparklines and individual trajectories without requiring any code modifications.
2. **P1 Visual Redesign:** All P0 data-integrity fixes are complete, verified, and locked. The codebase is now ready for P1 visual redesign when requested.
