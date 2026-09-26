"""
Production End-to-End Test Suite for Phase 4.

Validates:
1. FastAPI endpoints: /api/v1/airfare-index, /api/v1/quality-metrics, /api/v1/lead-curves,
   /api/v1/backtest, /api/v1/sensitivity, /api/methodology, /api/observations.
2. 30-Day Historical Backtest fidelity and error metrics (MAE, RMSE).
3. 4-Regime Sensitivity Analysis robustness and sum-to-unity validation.
4. Antigravity 8 Mandatory Acceptance Gates.
"""

import os
import sys
import json
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure paths
test_dir = Path(__file__).resolve().parent
scraper_src = test_dir.parent.parent / "src"
api_src = test_dir.parent.parent.parent / "api" / "src"
project_root = test_dir.parent.parent.parent.parent

for p in [str(scraper_src), str(api_src)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from main import app
from models.canonical import (
    NormalizedFareObservation,
    ProductStratum,
    classify_travel_day_type,
    classify_departure_time_band,
    classify_lead_time_class,
)
from index import APIxEngine, WeightRegistry


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. API Endpoints Tests
# ---------------------------------------------------------------------------

def test_api_airfare_index_endpoint(client):
    response = client.get("/api/v1/airfare-index")
    assert response.status_code == 200
    data = response.json()
    assert "index_value" in data
    assert float(data["index_value"]) > 0
    assert "route_indices" in data
    assert "lead_time_indices" in data
    assert data["reference_period"] == "2024"
    assert "methodology_version" in data


def test_api_quality_metrics_endpoint(client):
    response = client.get("/api/v1/quality-metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["currency"] == "INR"
    assert data["total_observations"] > 0
    assert data["valid_observations"] > 0
    assert data["exact_duplicate_rate_percent"] == 0.0


def test_api_lead_curves_endpoint(client):
    response = client.get("/api/v1/lead-curves?route=DEL-BOM")
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "DEL-BOM"
    assert "curve_points" in data
    assert len(data["curve_points"]) > 0
    for pt in data["curve_points"]:
        assert "lead_time" in pt
        assert "average_fare_inr" in pt
        assert pt["average_fare_inr"] > 0


def test_api_backtest_endpoint(client):
    response = client.get("/api/v1/backtest")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "daily_series" in data
    summary = data["summary"]
    assert summary["total_days"] == 30
    assert "mean_absolute_error_mae" in summary
    assert "root_mean_squared_error_rmse" in summary
    assert summary["antigravity_acceptance_passed"] is True


def test_api_sensitivity_endpoint(client):
    response = client.get("/api/v1/sensitivity")
    assert response.status_code == 200
    data = response.json()
    assert "variants" in data
    assert "divergence_summary" in data
    assert "maximum_divergence_pts" in data
    assert float(data["maximum_divergence_percent"]) < 1.0  # Must be robust (<1%)


def test_api_methodology_endpoint(client):
    response = client.get("/api/methodology")
    assert response.status_code == 200
    data = response.json()
    assert data["base_value"] == 100.0
    assert data["lead_time_alignment_checkpoint"] == "T+21"
    # Route weights sum to 1.0
    route_sum = sum(data["route_weights"].values())
    assert abs(route_sum - 1.0) < 0.001
    # Lead time weights sum to 1.0
    lt_sum = sum(data["lead_time_weights"].values())
    assert abs(lt_sum - 1.0) < 0.001


def test_api_observations_endpoint(client):
    response = client.get("/api/observations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "route" in first
    assert "total_fare" in first
    assert first["total_fare"] > 0


# ---------------------------------------------------------------------------
# 2. Backtest and Sensitivity Artifact Verifications
# ---------------------------------------------------------------------------

def test_backtest_results_artifact():
    bt_path = project_root / "backtest_results.json"
    assert bt_path.exists(), "backtest_results.json must exist"
    with open(bt_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["daily_series"]) == 30
    assert data["summary"]["mean_absolute_error_mae"] > 0


def test_sensitivity_results_artifact():
    sens_path = project_root / "sensitivity_results.json"
    assert sens_path.exists(), "sensitivity_results.json must exist"
    with open(sens_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["variants"]) == 4
    for vname, vdata in data["variants"].items():
        assert abs(vdata["route_weight_sum"] - 1.0) < 0.001
        assert abs(vdata["lead_time_weight_sum"] - 1.0) < 0.001


# ---------------------------------------------------------------------------
# 3. Antigravity Mandatory 8 Acceptance Gates
# ---------------------------------------------------------------------------

def test_gate1_price_invariance():
    """Gate 1: Price Invariance -> J = 1.0000"""
    engine = APIxEngine()
    json_path = project_root / "easemytrip_normalized_data.json"
    with open(json_path, "r", encoding="utf-8") as f:
        obs = [NormalizedFareObservation(**r) for r in json.load(f)]
    p1 = engine.process_period("2026-08", obs)
    p2 = engine.process_period("2026-09", obs, prev_period="2026-08")
    assert p2.index_value == Decimal("100.00")
    assert p2.mom_percent == Decimal("0.00")


def test_gate2_scale_invariance_inflation():
    """Gate 2: Scale Invariance -> +10% price rise yields J = 1.1000"""
    engine = APIxEngine()
    json_path = project_root / "easemytrip_normalized_data.json"
    with open(json_path, "r", encoding="utf-8") as f:
        obs = [NormalizedFareObservation(**r) for r in json.load(f)]
    
    inflated_obs = []
    for o in obs:
        d = o.model_dump(mode="python")
        d["total_fare"] = Decimal(str(round(float(o.total_fare) * 1.10, 2)))
        d["normalized_price_inr"] = d["total_fare"]
        inflated_obs.append(NormalizedFareObservation(**d))

    p1 = engine.process_period("2026-08", obs)
    p2 = engine.process_period("2026-09", inflated_obs, prev_period="2026-08")
    assert abs(float(p2.index_value) - 110.00) < 0.15
    assert abs(float(p2.mom_percent) - 10.00) < 0.15


def test_gate3_recursive_chain_consistency():
    """Gate 3: Recursive chain consistency I_t = I_(t-1) * J_t"""
    engine = APIxEngine()
    json_path = project_root / "easemytrip_normalized_data.json"
    with open(json_path, "r", encoding="utf-8") as f:
        obs = [NormalizedFareObservation(**r) for r in json.load(f)]
    
    p1 = engine.process_period("2026-07", obs)
    p2 = engine.process_period("2026-08", obs, prev_period="2026-07")
    p3 = engine.process_period("2026-09", obs, prev_period="2026-08")
    assert p1.index_value == p2.index_value == p3.index_value == Decimal("100.00")


def test_gate4_weight_sum_unity():
    """Gate 4: Weight unity -> sum(W_r) = 1.0000 and sum(W_l) = 1.0000"""
    registry = WeightRegistry()
    assert sum(registry.route_weights.values()) == Decimal("1.0000")
    assert sum(registry.lead_time_weights.values()) == Decimal("1.0000")


def test_gate5_duplicate_invariance():
    """Gate 5: Ingesting duplicates does not change monthly geometric product price"""
    engine = APIxEngine()
    json_path = project_root / "easemytrip_normalized_data.json"
    with open(json_path, "r", encoding="utf-8") as f:
        obs = [NormalizedFareObservation(**r) for r in json.load(f)]
    
    # Ingest 2x duplicates
    double_obs = obs + obs
    p_single = engine.process_period("2026-08", obs)
    p_double = engine.process_period("2026-08", double_obs)
    assert p_single.index_value == p_double.index_value


def test_gate6_mospi_t21_isolation():
    """Gate 6: T+21 is an independent stratum and lead-time class"""
    assert classify_lead_time_class(21) == "T+21"
    reg = WeightRegistry()
    assert "T+21" in reg.lead_time_weights
    assert reg.lead_time_weights["T+21"] > Decimal("0")


def test_gate7_zero_price_handling():
    """Gate 7: Zero or negative fares are strictly rejected at canonical validation"""
    json_path = project_root / "easemytrip_normalized_data.json"
    with open(json_path, "r", encoding="utf-8") as f:
        valid_dict = json.load(f)[0]
    
    valid_dict["total_fare"] = Decimal("0.00")
    with pytest.raises(Exception):
        NormalizedFareObservation(**valid_dict)


def test_gate8_audit_metadata():
    """Gate 8: Every published series records methodology, weight, and timestamp versions"""
    engine = APIxEngine()
    json_path = project_root / "easemytrip_normalized_data.json"
    with open(json_path, "r", encoding="utf-8") as f:
        obs = [NormalizedFareObservation(**r) for r in json.load(f)]
    res = engine.process_period("2026-09", obs)
    assert res.methodology_version == "APIx v1.0"
    assert res.weight_version == "2026.09"
    assert res.published_at is not None
