# AERIX Backtest Endpoint Dual-Mode & Real-Data Validation Report

**Document Reference:** `AERIX-BACKTEST-AUDIT-2026`  
**Endpoint Audited:** `GET /api/v1/backtest`  
**Target Module:** `apps/api/src/main.py`  
**Execution Date:** September 29, 2026  
**Auditor:** AERIX Core Engineering & Quality Assurance Group  

---

## 1. Executive Summary & Objective

The `GET /api/v1/backtest` endpoint has been upgraded to support two mutually exclusive, clearly separated modes of evaluation:

1. **`mode=synthetic` (Default):** The existing 30-day historical longitudinal panel simulating airline yield volatility against a mathematical market drift benchmark, preserving backward compatibility with the frontend dashboard (`web/`).
2. **`mode=real`:** A strictly empirical validation mode operating exclusively on genuine production observations from the hosted database, dynamically discovering real collection dates, reporting only observed metrics, and disallowing statistical fabrication.

### Core Non-Fabrication Invariants Enforced:
- **Zero Interpolation:** Missing calendar days between real collection passes are **never** filled with synthetic or interpolated quotes.
- **Zero Metric Fabrication:** Time-series tracking error metrics (MAE, RMSE, Pearson correlation, volatility dampening) that require an external high-frequency airfare benchmark or a continuous daily baseline are explicitly returned as `null` rather than invented.
- **DGCA Benchmark Boundary:** DGCA CY2024 domestic passenger volume data is strictly designated as a **Traffic Volume & Sampling Representativeness Benchmark**, **not** a daily airfare price series. No airfare MAE/RMSE is computed against passenger counts.

---

## 2. Dynamic Real Dates & Observation Discovery

The real-data mode (`mode=real`) connects to the hosted Neon PostgreSQL database (`fare_observations` table) and dynamically extracts all genuine collection runs:

| Real Collection Date | Primary Data Source | Observed Quote Count | Route Scope | Mean Observed Fare | Median Observed Fare |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`2026-09-21`** | `ignav` (Pilot Validation Channel) | **54** quotes | 1 route (`DEL-BOM`) | ₹6,826.61 | ₹6,583.00 |
| **`2026-09-22`** | `easemytrip` (Canonical Normalized Pilot) | **145** quotes | 1 route (`DEL-BOM`) | ₹9,398.79 | ₹6,960.00 |
| **`2026-09-27`** | `google_flights` (Top-60 Full Production Sweep) | **8,998** quotes (11,716 classified) | 57 routes in DB (60 routes in classification) | ₹9,977.90 | ₹8,697.00 |

- **Total Observation Days:** **3 distinct dates** (`2026-09-21`, `2026-09-22`, `2026-09-27`)
- **Total Real Observations:** **9,197** verified records in Neon DB (supplemented by 11,716 verified records in `runtime/top60_observation_classification.json`)
- **Evaluation Window:** **`2026-09-21 to 2026-09-27`**

---

## 3. DGCA Benchmark Audit & Comparability Assessment

### Was a Genuine DGCA Airfare Price Comparison Possible?
**NO.** The audit determined the following institutional reality:

1. **Nature of DGCA Data in Project:**
   The DGCA data ingested into AERIX (from DGCA CY2024 Domestic Traffic Reports) consists of annual passenger traffic counts across India's Top-60 city-pairs (covering 91,993,488 domestic passengers; 57.02% of all-India scheduled traffic).
2. **Passenger Volume $\ne$ Airfare Price:**
   DGCA publishes traffic volume weights ($W_r$), not high-frequency daily route transaction airfare prices.
3. **Institutional Non-Comparability:**
   Comparing scraped airfares in rupees against passenger volumes in millions to compute MAE or RMSE is mathematically invalid.
4. **Conclusion:**
   In `mode=real`, the benchmark source is explicitly labeled:
   > `"DGCA CY2024 Traffic Volume Benchmark (DGCA publishes Top-60 city-pair passenger traffic distributions, not daily market transaction airfare prices)"`
   No airfare MAE/RMSE is computed against this volume baseline.

---

## 4. Metric Computation & Availability Audit

### 4.1 Metrics Successfully Calculated (from Real Data):
- **Per-Date Observation Count:** Verified counts ($54$, $145$, $8,998$).
- **Per-Date Route Count:** Distinct city pairs active on that collection date ($1$ on Days 1 & 2; $57$ on Day 3).
- **Per-Date Price Distribution:** Empirical arithmetic mean, median, geometric mean, minimum fare, and maximum fare for each date.
- **Per-Route Median Prices:** Median transaction fares per route on each collection day.
- **Provenance Tags:** Explicit `data_status: "REAL_PRODUCTION_OBSERVATIONS"` and `backtest_type: "REAL_DATA_VALIDATION"`.

### 4.2 Metrics Explicitly Set to `null` (Unavailable Due to Insufficient Longitudinal Depth):
- **`mean_absolute_error_mae` $\to$ `null`:** Unavailable because DGCA does not publish daily price indexes, and no external high-frequency benchmark exists for this timeframe.
- **`root_mean_squared_error_rmse` $\to$ `null`:** Unavailable for the same reason.
- **`benchmark_correlation` $\to$ `null`:** Unavailable (correlation requires paired daily series of identical price relatives over an extended time horizon).
- **`apix_daily_volatility_percent` $\to$ `null`:** Unavailable across non-contiguous sparse dates.
- **`volatility_reduction_ratio` $\to$ `null`:** Unavailable without continuous daily baseline.

---

## 5. Dual-Mode API Specification

### Endpoint Signature
`GET /api/v1/backtest?mode={synthetic|real}`

- **Query Parameter:** `mode` (Optional, string).
  - Supported: `"synthetic"` (default), `"real"`.
  - Case-insensitive (`"SYNTHETIC"`, `"Synthetic"`, `"real"`, `"REAL"` supported).
  - Invalid value (e.g. `mode=random`) $\to$ **HTTP 400 Bad Request**:
    ```json
    {
      "detail": "Invalid mode 'random'. Supported modes are: 'synthetic', 'real'."
    }
    ```

### 5.1 Real Mode Output Example (`GET /api/v1/backtest?mode=real`)
```json
{
  "backtest_type": "REAL_DATA_VALIDATION",
  "data_status": "REAL_PRODUCTION_OBSERVATIONS",
  "evaluation_window": "2026-09-21 to 2026-09-27",
  "evaluation_start": "2026-09-21",
  "evaluation_end": "2026-09-27",
  "observation_days": 3,
  "total_real_observations": 9197,
  "benchmark_source": "DGCA CY2024 Traffic Volume Benchmark (DGCA publishes Top-60 city-pair passenger traffic distributions, not daily market transaction airfare prices)",
  "provenance_note": "Evaluated strictly on genuinely observed production quotes from hosted Neon PostgreSQL database (fare_observations). No synthetic points, no interpolation, and no fabricated index series.",
  "metrics": {
    "evaluation_period": "2026-09-21 to 2026-09-27",
    "total_days": 3,
    "total_observations": 9197,
    "mean_absolute_error_mae": null,
    "root_mean_squared_error_rmse": null,
    "benchmark_correlation": null,
    "apix_daily_volatility_percent": null,
    "volatility_reduction_ratio": null,
    "status": "INSUFFICIENT_LONGITUDINAL_DEPTH_FOR_TRACKING_METRICS",
    "reason": "Airfare tracking metrics (MAE/RMSE) require an external high-frequency airfare price benchmark (DGCA provides traffic volume weights, not daily price indices). A multi-week longitudinal baseline across consistent route scope is required before valid tracking error can be calculated."
  },
  "summary": {
    "evaluation_period": "2026-09-21 to 2026-09-27",
    "total_days": 3,
    "total_observations": 9197,
    "mean_absolute_error_mae": null,
    "root_mean_squared_error_rmse": null,
    "benchmark_correlation": null,
    "apix_daily_volatility_percent": null,
    "volatility_reduction_ratio": null,
    "status": "INSUFFICIENT_LONGITUDINAL_DEPTH_FOR_TRACKING_METRICS"
  },
  "limitations": [
    "Longitudinal history is currently limited to 3 distinct collection dates (2026-09-21 to 2026-09-27) recorded during prototype development.",
    "DGCA publishes domestic passenger volumes (traffic representativeness), not daily ticket transaction prices; therefore, airfare MAE and RMSE cannot be computed against DGCA data.",
    "Time-series tracking metrics (MAE, RMSE, correlation) require a continuous longitudinal time series across an identical route scope; calculating them across 3 sparse dates would represent statistical fabrication.",
    "Scope transition across dates: Collections on 2026-09-21 and 2026-09-22 were single-route validation pilots, whereas 2026-09-27 represents the full 60-route Top-60 production basket."
  ],
  "daily_series": [
    {
      "day": 1,
      "date": "2026-09-21",
      "observation_count": 54,
      "route_count": 1,
      "sample_routes": ["DEL-BOM"],
      "collection_sources": ["ignav"],
      "mean_fare_inr": 6826.61,
      "median_fare_inr": 6583.0,
      "geometric_mean_inr": 6777.89,
      "min_fare_inr": 6314.0,
      "max_fare_inr": 10868.0,
      "route_median_fares": {"DEL-BOM": 6583.0},
      "data_status": "REAL_PRODUCTION_OBSERVATIONS"
    },
    {
      "day": 2,
      "date": "2026-09-22",
      "observation_count": 145,
      "route_count": 1,
      "sample_routes": ["DEL-BOM"],
      "collection_sources": ["easemytrip"],
      "mean_fare_inr": 9398.79,
      "median_fare_inr": 6960.0,
      "geometric_mean_inr": 8641.45,
      "min_fare_inr": 6529.0,
      "max_fare_inr": 25778.0,
      "route_median_fares": {"DEL-BOM": 6960.0},
      "data_status": "REAL_PRODUCTION_OBSERVATIONS"
    },
    {
      "day": 3,
      "date": "2026-09-27",
      "observation_count": 8998,
      "route_count": 57,
      "sample_routes": ["AMD-BLR", "AMD-BOM", "AMD-DEL", "ATQ-DEL", "BBI-DEL", "BLR-BBI", "BLR-BOM", "BLR-CCU", "BLR-COK", "BLR-DEL"],
      "collection_sources": ["google_flights"],
      "mean_fare_inr": 9977.9,
      "median_fare_inr": 8697.0,
      "geometric_mean_inr": 9170.81,
      "min_fare_inr": 3196.0,
      "max_fare_inr": 175132.0,
      "route_median_fares": {"AMD-BLR": 8394.0, "AMD-BOM": 7328.0, "AMD-DEL": 6039.0, "ATQ-DEL": 5629.0, "BBI-DEL": 10064.0},
      "data_status": "REAL_PRODUCTION_OBSERVATIONS"
    }
  ],
  "last_updated": "2026-09-29T13:49:20.125678+00:00"
}
```

### 5.2 Synthetic Mode Output Example (`GET /api/v1/backtest?mode=synthetic` or default)
```json
{
  "backtest_type": "SYNTHETIC_30_DAY_DEMONSTRATION",
  "data_status": "SYNTHETIC_DEMONSTRATION",
  "series_type": "SYNTHETIC_LONGITUDINAL_PANEL",
  "evaluation_window": "2026-08-24 to 2026-09-22",
  "observation_days": 30,
  "benchmark_source": "Synthetic Theoretical Market Drift Benchmark (+0.06%/day simulated baseline). Note: DGCA CY2024 published data provides route passenger volume weights (Wr), not daily airfare price series.",
  "provenance_note": "The 30-day series was synthesized from base scraped quotes to evaluate Jevons elementary tracking error and noise reduction against a simulated drift trend; it is NOT an observed DGCA daily airfare series.",
  "summary": {
    "evaluation_period": "2026-08-24 to 2026-09-22",
    "total_days": 30,
    "base_index_start": 100.0,
    "final_index_end": 101.8845,
    "total_30day_return_percent": 1.885,
    "mean_absolute_error_mae": 1.3302,
    "root_mean_squared_error_rmse": 2.3875,
    "benchmark_correlation": 0.3583,
    "apix_daily_volatility_percent": 2.301,
    "naive_scraped_daily_volatility_percent": 2.3047,
    "volatility_reduction_ratio": 1.0,
    "naive_mae": 1.3669,
    "naive_rmse": 2.4139,
    "maximum_drawdown_percent": 4.37,
    "stratum_coverage_mean": 1.0,
    "mospi_t21_checkpoint_present": true,
    "antigravity_acceptance_passed": true
  },
  "metrics": {
    "evaluation_period": "2026-08-24 to 2026-09-22",
    "total_days": 30,
    "mean_absolute_error_mae": 1.3302,
    "root_mean_squared_error_rmse": 2.3875,
    "benchmark_correlation": 0.3583
  },
  "limitations": [
    "The underlying 30-day daily series is a statistically synthesized panel derived from pilot observations, not 30 distinct calendar days of web scraping.",
    "The benchmark is a theoretical economic drift model, not an official DGCA transaction airfare price index (DGCA publishes passenger traffic volumes, not daily airfares).",
    "Demonstrates econometric compilation stability and noise dampening under simulated volatility shocks."
  ],
  "daily_series": [
    {
      "day": 1,
      "date": "2026-08-24",
      "apix_index": 100.0,
      "naive_scraped_index": 100.0,
      "ground_truth_benchmark": 100.0,
      "daily_mom_inflation_rate": 0.0,
      "route_indices": {"DEL-BOM": 100.0},
      "lead_time_indices": {"DEL-BOM_T+7": 100.0},
      "total_observations": 145,
      "overall_coverage_ratio": 1.0
    }
  ],
  "last_updated": "2026-09-29T13:49:18.987654+00:00"
}
```

---

## 6. Automated Test Suite Validation

Eight dedicated tests were added to [`tests/test_api_endpoints.py`](file:///c:/Users/Hemant%20Jagnani/OneDrive/Desktop/SIH2026/tests/test_api_endpoints.py) and executed:

| Test Name | Mode Tested | Verification Criteria | Status |
| :--- | :--- | :--- | :--- |
| `test_backtest_endpoint` | Default (`none`) | Returns 30-day synthetic series, `data_status == "SYNTHETIC_DEMONSTRATION"` | **PASSED** |
| `test_backtest_explicit_synthetic_mode` | `mode=synthetic` | Returns 30-day synthetic series, full limitation disclosures | **PASSED** |
| `test_backtest_real_mode` | `mode=real` | Returns strictly real collection dates ($3$ days), $9,197$ quotes | **PASSED** |
| `test_backtest_invalid_mode` | `mode=unsupported_mode` | Rejects with HTTP 400 Bad Request and supported modes error detail | **PASSED** |
| `test_backtest_insufficient_real_observations_no_fabrication` | `mode=real` | Confirms MAE, RMSE, and correlation are strictly `null` (not fabricated) | **PASSED** |
| `test_backtest_no_fabricated_days_in_real_mode` | `mode=real` | Confirms exactly 3 observed dates returned ($< 30$ days), zero interpolation | **PASSED** |
| `test_backtest_dgca_benchmark_provenance_disclosure` | `mode=real` | Validates explicit disclosure that DGCA is passenger volume, not airfares | **PASSED** |
| `test_backtest_synthetic_and_real_never_mixed` | Cross-mode invariant | Verifies that synthetic and real dates and provenance tags never overlap | **PASSED** |

### Test Execution Results
- `python -m pytest tests/test_api_endpoints.py -v`: **29 passed in 17.36s**
- `pytest tests/ -q`: **187 passed, 0 failed in 22.67s**
- Live verification script `scratch/verify_backtest_modes.py`: **All 4 live modes validated against port 8000**.

---

## 7. Institutional Governance Sign-Off

The dual-mode enhancement for `GET /api/v1/backtest` is fully implemented and institutional governance standards are verified:
- **Zero claims of "30-day real backtest":** The 30-day series is explicitly designated as `SYNTHETIC_30_DAY_DEMONSTRATION`.
- **Zero claims of "DGCA airfare backtest":** DGCA data is transparently identified as passenger volume weights.
- **Genuine real-data validation:** `mode=real` reports the exact 3 collection dates (`2026-09-21`, `2026-09-22`, `2026-09-27`) covering $9,197$ production quotes, returning `null` for multi-day tracking errors rather than inventing metrics.
