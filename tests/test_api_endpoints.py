import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure scraper src and api src are in python path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
scraper_src = os.path.join(ROOT, "apps", "scraper", "src")
api_src = os.path.join(ROOT, "apps", "api", "src")
if scraper_src not in sys.path:
    sys.path.insert(0, scraper_src)
if api_src not in sys.path:
    sys.path.insert(0, api_src)

from apps.api.src.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "redis" in data
    assert data["database"]["type"] == "Neon PostgreSQL (Hosted)"
    assert "fare_observations_count" in data["database"]
    assert data["data_status"] == "REAL_PRODUCTION_SURVEILLANCE"


def test_airfare_index_endpoint():
    response = client.get("/api/v1/airfare-index?frequency=monthly")
    assert response.status_code == 200
    data = response.json()
    assert "index_value" in data
    assert float(data["index_value"]) > 0
    assert "base_value" in data
    assert float(data["base_value"]) == 100.0
    assert data["data_status"] == "EXPERIMENTAL_APIX"
    assert data["governance"] == "PROJECT_METHODOLOGY_DEMONSTRATION"


def test_airfare_index_csv_export():
    response = client.get("/api/v1/airfare-index?frequency=monthly&format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "attachment; filename=" in response.headers.get("content-disposition", "")
    text = response.text
    assert "period,frequency,route,lead_time,index_value,data_status,governance" in text
    assert "EXPERIMENTAL_APIX" in text


def test_nso_cpi_feed_json():
    response = client.get("/api/v1/nso/cpi-feed?period=2026-09&format=json")
    assert response.status_code == 200
    data = response.json()
    assert data["data_status"] == "EXPERIMENTAL_APIX"
    assert data["feed_status"] == "PROTOTYPE_FOR_NSO_INTEGRATION"
    assert "NSO/MoSPI CPI Integration" in data["feed_designation"]
    assert data["coicop_2018_code"] == "07.3.3.1.2.01"
    assert round(float(data["national_cpi_weight_percent"]), 5) == 0.02951
    assert "CY2024" in data["base_period"]
    assert "headline_index" in data
    assert "route_elementary_indices" in data
    assert len(data["route_elementary_indices"]) > 0
    assert "official_classification" in data
    assert "apix_experimental_metrics" in data


def test_nso_cpi_feed_csv_export():
    response = client.get("/api/v1/nso/cpi-feed?period=2026-09&format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "attachment; filename=" in response.headers.get("content-disposition", "")
    text = response.text
    assert "coicop_code" in text
    assert "07.3.3.1.2.01" in text
    assert "Transport and Communication" in text
    assert "0.02951" in text
    assert "EXPERIMENTAL_APIX" in text


def test_rbi_nowcast_endpoint():
    response = client.get("/api/v1/rbi/nowcast")
    assert response.status_code == 200
    data = response.json()
    assert data["data_status"] == "SYNTHETIC_DEMONSTRATION_PANEL"
    assert data["feed_status"] == "RESEARCH_PROTOTYPE_NOWCAST"
    assert "Reserve Bank of India" in data["consumer_agency"]
    assert "latest_daily_airfare_index" in data
    assert "daily_mom_momentum_percent" in data
    assert "yield_elasticity" in data
    assert "urgency_pricing_spread_ratio" in data["yield_elasticity"]
    assert "dgca_backtest_tracking" in data
    assert "analytical_price_indicator" in data
    assert "analytical_indicator_note" in data


def test_backtest_endpoint():
    """Default backtest returns synthetic 30-day demonstration panel with backward compatibility."""
    response = client.get("/api/v1/backtest")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "daily_series" in data
    assert data["backtest_type"] == "SYNTHETIC_30_DAY_DEMONSTRATION"
    assert data["data_status"] == "SYNTHETIC_DEMONSTRATION"
    assert data["series_type"] == "SYNTHETIC_LONGITUDINAL_PANEL"
    assert data["observation_days"] == 30
    assert len(data["daily_series"]) == 30
    assert "metrics" in data
    assert data["metrics"]["mean_absolute_error_mae"] > 0
    assert data["metrics"]["root_mean_squared_error_rmse"] > 0


def test_backtest_explicit_synthetic_mode():
    """Explicit mode=synthetic returns 30-day synthetic demonstration series."""
    response = client.get("/api/v1/backtest?mode=synthetic")
    assert response.status_code == 200
    data = response.json()
    assert data["backtest_type"] == "SYNTHETIC_30_DAY_DEMONSTRATION"
    assert data["data_status"] == "SYNTHETIC_DEMONSTRATION"
    assert data["observation_days"] == 30
    assert len(data["daily_series"]) == 30
    assert "limitations" in data
    assert len(data["limitations"]) > 0


def test_backtest_real_mode():
    """mode=real returns strictly genuine observed collection dates from hosted database."""
    response = client.get("/api/v1/backtest?mode=real")
    assert response.status_code == 200
    data = response.json()
    assert data["backtest_type"] == "REAL_DATA_VALIDATION"
    assert data["data_status"] == "REAL_PRODUCTION_OBSERVATIONS"
    assert data["observation_days"] >= 1
    assert data["observation_days"] < 30  # Confirms real sparse dates, not fabricated 30 days
    assert "daily_series" in data
    assert len(data["daily_series"]) == data["observation_days"]
    assert "evaluation_start" in data
    assert "evaluation_end" in data
    assert "benchmark_source" in data
    assert "provenance_note" in data
    assert "limitations" in data


def test_backtest_invalid_mode():
    """Invalid mode parameter returns structured HTTP 400 Bad Request."""
    response = client.get("/api/v1/backtest?mode=unsupported_mode")
    assert response.status_code == 400
    assert "Invalid mode 'unsupported_mode'" in response.json()["detail"]
    assert "Supported modes are: 'synthetic', 'real'" in response.json()["detail"]


def test_backtest_insufficient_real_observations_no_fabrication():
    """In real mode with sparse collection history, MAE/RMSE/correlation must be null, not fabricated."""
    response = client.get("/api/v1/backtest?mode=real")
    assert response.status_code == 200
    data = response.json()
    metrics = data["metrics"]
    assert metrics["mean_absolute_error_mae"] is None
    assert metrics["root_mean_squared_error_rmse"] is None
    assert metrics["benchmark_correlation"] is None
    assert metrics["apix_daily_volatility_percent"] is None
    assert metrics["status"] == "INSUFFICIENT_LONGITUDINAL_DEPTH_FOR_TRACKING_METRICS"


def test_backtest_no_fabricated_days_in_real_mode():
    """Confirms real mode does NOT fabricate missing calendar days or interpolate."""
    response = client.get("/api/v1/backtest?mode=real")
    assert response.status_code == 200
    data = response.json()
    dates = [d["date"] for d in data["daily_series"]]
    # In database, the distinct collection dates are 2026-09-21, 2026-09-22, 2026-09-27
    assert len(dates) <= 5
    for point in data["daily_series"]:
        assert point["data_status"] == "REAL_PRODUCTION_OBSERVATIONS"
        assert point["observation_count"] > 0
        assert point["mean_fare_inr"] > 0


def test_backtest_dgca_benchmark_provenance_disclosure():
    """Verifies that DGCA benchmark is explicitly disclosed as traffic volume distribution, not airfare prices."""
    response = client.get("/api/v1/backtest?mode=real")
    assert response.status_code == 200
    data = response.json()
    bench = data["benchmark_source"]
    assert "DGCA CY2024 Traffic Volume Benchmark" in bench
    assert "not daily market transaction airfare prices" in bench


def test_backtest_synthetic_and_real_never_mixed():
    """Ensures synthetic panel data and real observed production data are strictly isolated."""
    resp_synth = client.get("/api/v1/backtest?mode=synthetic")
    resp_real = client.get("/api/v1/backtest?mode=real")
    
    data_synth = resp_synth.json()
    data_real = resp_real.json()

    # Provenance tags must never overlap
    assert data_synth["data_status"] == "SYNTHETIC_DEMONSTRATION"
    assert data_real["data_status"] == "REAL_PRODUCTION_OBSERVATIONS"

    assert data_synth["backtest_type"] == "SYNTHETIC_30_DAY_DEMONSTRATION"
    assert data_real["backtest_type"] == "REAL_DATA_VALIDATION"

    # Synthetic has 30 days starting in August; real has only genuine September collection dates
    assert data_synth["observation_days"] == 30
    assert data_real["observation_days"] < 30
    assert data_synth["daily_series"][0]["date"] == "2026-08-24"
    assert "2026-08-24" not in [d["date"] for d in data_real["daily_series"]]


def test_sensitivity_endpoint():
    response = client.get("/api/v1/sensitivity")
    assert response.status_code == 200
    data = response.json()
    assert data["data_status"] == "STATIC_METHODOLOGICAL_METADATA"
    assert data["governance"] == "PROJECT_METHODOLOGY_DEMONSTRATION"
    assert "variants" in data
    assert "baseline_index_value" in data


def test_lead_curves_endpoint():
    response = client.get("/api/v1/lead-curves?route=DEL-BOM")
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "DEL-BOM"
    assert data["data_status"] == "REAL_PRODUCTION_OBSERVATIONS"
    assert "curve_points" in data
    assert len(data["curve_points"]) > 0


def test_matrix_endpoint():
    response = client.get("/api/v1/matrix")
    assert response.status_code == 200
    data = response.json()
    assert "cells" in data
    assert "total_cells" in data
    assert data["total_cells"] > 0
    assert data["data_status"] == "REAL_PRODUCTION_OBSERVATIONS"


def test_coverage_endpoint():
    response = client.get("/api/v1/coverage")
    assert response.status_code == 200
    data = response.json()
    assert data["total_target_cells"] == 360
    assert data["populated_cells"] > 0
    assert data["coverage_percent"] > 0
    assert data["data_status"] == "REAL_PRODUCTION_OBSERVATIONS"


def test_quality_metrics_endpoint():
    response = client.get("/api/v1/quality-metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["data_status"] == "REAL_PRODUCTION_OBSERVATIONS"
    assert "total_observations" in data
    assert "currency" in data
    assert data["currency"] == "INR"


def test_methodology_endpoint():
    response = client.get("/api/methodology")
    assert response.status_code == 200
    data = response.json()
    assert data["base_value"] == 100.0
    assert "2024" in data["reference_period"]
    assert "route_weights" in data
    assert "lead_time_weights" in data
    assert data["data_status"] == "STATIC_METHODOLOGICAL_METADATA"
    assert data["governance"] == "PROJECT_METHODOLOGY_DEMONSTRATION"


def test_runs_endpoint():
    response = client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "run_date" in data[0]
    assert "status" in data[0]
    assert data[0]["observations_count"] > 0
    assert "data_status" in data[0]


def test_observations_endpoint():
    response = client.get("/api/observations?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5
    if len(data) > 0:
        assert "route" in data[0]
        assert "total_fare" in data[0]
        assert data[0]["data_status"] == "REAL_PRODUCTION_OBSERVATIONS"


# Structured error handling tests
def test_error_nso_invalid_period():
    response = client.get("/api/v1/nso/cpi-feed?period=invalid_period")
    assert response.status_code == 400
    assert "Invalid period format" in response.json()["detail"]


def test_error_nso_invalid_format():
    response = client.get("/api/v1/nso/cpi-feed?period=2026-09&format=xml")
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]


def test_error_airfare_index_invalid_frequency():
    response = client.get("/api/v1/airfare-index?frequency=hourly")
    assert response.status_code == 400
    assert "Invalid frequency" in response.json()["detail"]


def test_error_matrix_invalid_lead_time():
    response = client.get("/api/v1/matrix?lead_time=T+999")
    assert response.status_code == 400
    assert "Invalid lead_time" in response.json()["detail"]


def test_error_lead_curves_malformed_route():
    response = client.get("/api/v1/lead-curves?route=DELBOM")
    assert response.status_code == 400
    assert "Invalid route parameter" in response.json()["detail"]


def test_error_lead_curves_nonexistent_route():
    response = client.get("/api/v1/lead-curves?route=ZZZ-YYY")
    assert response.status_code == 404
    assert "No fare observations found" in response.json()["detail"]


def test_error_rbi_nowcast_out_of_bounds_date():
    response = client.get("/api/v1/rbi/nowcast?as_of_date=1999-01-01")
    assert response.status_code == 404
    assert "not found in available backtest window" in response.json()["detail"]
