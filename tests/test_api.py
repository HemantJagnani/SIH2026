"""
Tests for the FastAPI endpoints – Phase 6.

Uses httpx TestClient. All tests run against fixture data seeded
into a temporary database.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apix.config import load_config
from apix.db import init_db
from apix.pipeline import run as run_pipeline


@pytest.fixture(scope="module")
def seeded_db(tmp_path_factory):
    """Seed 3 days of fixture data for the API tests."""
    db_path = tmp_path_factory.mktemp("api") / "test_api.db"
    init_db(db_path)

    from dataclasses import replace
    cfg = load_config(Path(__file__).parent.parent / "config.yaml")
    src = replace(cfg.source, name="fixture")
    cfg_f = replace(cfg, source=src)

    today = date(2026, 1, 15)
    for i in range(3):
        run_pipeline(today - timedelta(days=2 - i), cfg=cfg_f, db_path=db_path)

    return db_path


@pytest.fixture(scope="module")
def client(seeded_db):
    """Return a TestClient pointed at the real app with the seeded DB."""
    import apix.api as api_module
    import apix.db as db_module

    # Patch the default DB path to the test DB
    original = db_module._DEFAULT_DB_PATH
    db_module._DEFAULT_DB_PATH = seeded_db
    api_module.init_db()

    from apix.api import app
    with TestClient(app) as c:
        yield c

    db_module._DEFAULT_DB_PATH = original


class TestIndexEndpoint:
    def test_daily_returns_list(self, client):
        r = client.get("/api/index?scope=overall&freq=daily")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_route_scope_requires_route(self, client):
        r = client.get("/api/index?scope=route")
        assert r.status_code == 422

    def test_route_scope_with_route(self, client):
        r = client.get("/api/index?scope=route&route=DEL-BOM&freq=daily")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_weekly_aggregation(self, client):
        r = client.get("/api/index?scope=overall&freq=weekly")
        assert r.status_code == 200

    def test_monthly_aggregation(self, client):
        r = client.get("/api/index?scope=overall&freq=monthly")
        assert r.status_code == 200


class TestItemsEndpoint:
    def test_returns_items_for_date(self, client):
        r = client.get("/api/items?obs_date=2026-01-15")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_invalid_date_returns_422(self, client):
        r = client.get("/api/items?obs_date=not-a-date")
        assert r.status_code == 422

    def test_items_have_required_fields(self, client):
        r = client.get("/api/items?obs_date=2026-01-15")
        data = r.json()
        if data:
            item = data[0]
            assert "route" in item
            assert "lead_days" in item
            assert "dep_band" in item
            assert "price" in item
            assert "is_synthetic" in item


class TestLeadCurveEndpoint:
    def test_returns_curves(self, client):
        r = client.get("/api/lead-curve?route=DEL-BOM")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_with_date_filter(self, client):
        r = client.get("/api/lead-curve?route=DEL-BOM&from=2026-01-13&to=2026-01-15")
        assert r.status_code == 200


class TestRelativesEndpoint:
    def test_returns_relatives(self, client):
        r = client.get("/api/relatives")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_with_date_filter(self, client):
        r = client.get("/api/relatives?from=2026-01-13&to=2026-01-15")
        assert r.status_code == 200

    def test_relatives_have_required_fields(self, client):
        r = client.get("/api/relatives")
        data = r.json()
        if data:
            rel = data[0]
            assert "obs_date" in rel
            assert "route" in rel
            assert "relative" in rel


class TestRunsEndpoint:
    def test_returns_runs(self, client):
        r = client.get("/api/runs")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 3  # we seeded 3 days

    def test_run_has_required_fields(self, client):
        r = client.get("/api/runs")
        run = r.json()[0]
        assert "run_date" in run
        assert "status" in run
        assert "pages_ok" in run
        assert "pages_failed" in run


class TestMethodologyEndpoint:
    def test_returns_methodology(self, client):
        r = client.get("/api/methodology")
        assert r.status_code == 200
        data = r.json()
        assert "routes" in data
        assert "lead_days" in data
        assert "aggregation" in data
        assert data["base_value"] == 100.0

    def test_weights_marked_as_assumptions(self, client):
        r = client.get("/api/methodology")
        data = r.json()
        for route in data["routes"]:
            assert route["weight_assumption"] is True
        for ld in data["lead_days"]:
            assert ld["weight_assumption"] is True


class TestSwaggerDocs:
    def test_docs_renders(self, client):
        r = client.get("/docs")
        assert r.status_code == 200
