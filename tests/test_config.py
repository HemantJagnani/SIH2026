"""
Tests for config.py – Phase 1.

Covers:
- Happy-path loading of the real config.yaml
- Weights-don't-sum-to-1 raises ValueError
- Type checking of the returned AppConfig
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from apix.config import load_config


# ── Helpers ──────────────────────────────────────────────────────────────


def _write_config(tmp_path: Path, overrides: dict) -> Path:
    """Write a minimal valid config to tmp_path, merging overrides."""
    base = {
        "timezone": "Asia/Kolkata",
        "schedule": {"hour": 5, "minute": 0},
        "source": {
            "name": "fixture",
            "user_agent": "test-agent/0.1",
            "min_delay_s": 8,
            "max_delay_s": 15,
        },
        "routes": [
            {"id": "DEL-BOM", "origin": "DEL", "destination": "BOM", "weight": 0.50},
            {"id": "DEL-BLR", "origin": "DEL", "destination": "BLR", "weight": 0.30},
            {"id": "BOM-BLR", "origin": "BOM", "destination": "BLR", "weight": 0.20},
        ],
        "lead_days": [
            {"days": 1,  "weight": 0.25},
            {"days": 7,  "weight": 0.25},
            {"days": 15, "weight": 0.25},
            {"days": 30, "weight": 0.25},
        ],
        "departure_bands": {
            "morning":   ["05:00", "12:00"],
            "afternoon": ["12:00", "18:00"],
            "evening":   ["18:00", "24:00"],
        },
        "item_rules": {
            "fare_class": "economy",
            "nonstop_only": True,
            "price_statistic": "min",
            "exclude_anomalies": False,
        },
        "index": {"base_value": 100, "min_coverage": 0.5},
    }
    base.update(overrides)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(base), encoding="utf-8")
    return cfg_path


# ── Tests ─────────────────────────────────────────────────────────────────


def test_load_real_config():
    """The project config.yaml should load without error."""
    real_path = Path(__file__).parent.parent / "config.yaml"
    cfg = load_config(real_path)
    assert cfg.timezone == "Asia/Kolkata"
    assert len(cfg.routes) == 3
    assert len(cfg.lead_days) == 4


def test_route_weights_sum_to_one(tmp_path):
    """Valid config with routes summing to 1.0 loads fine."""
    cfg_path = _write_config(tmp_path, {})
    cfg = load_config(cfg_path)
    total = sum(r.weight for r in cfg.routes)
    assert abs(total - 1.0) < 1e-6


def test_route_weights_not_one_raises(tmp_path):
    """Routes that don't sum to 1 must raise ValueError with a clear message."""
    bad_routes = [
        {"id": "DEL-BOM", "origin": "DEL", "destination": "BOM", "weight": 0.60},
        {"id": "DEL-BLR", "origin": "DEL", "destination": "BLR", "weight": 0.30},
        {"id": "BOM-BLR", "origin": "BOM", "destination": "BLR", "weight": 0.20},
    ]
    cfg_path = _write_config(tmp_path, {"routes": bad_routes})
    with pytest.raises(ValueError, match="routes"):
        load_config(cfg_path)


def test_lead_weights_not_one_raises(tmp_path):
    """Lead-day weights that don't sum to 1 must raise ValueError."""
    bad_leads = [
        {"days": 1,  "weight": 0.30},
        {"days": 7,  "weight": 0.30},
        {"days": 15, "weight": 0.30},
        {"days": 30, "weight": 0.30},
    ]
    cfg_path = _write_config(tmp_path, {"lead_days": bad_leads})
    with pytest.raises(ValueError, match="lead_days"):
        load_config(cfg_path)


def test_config_immutable(tmp_path):
    """AppConfig and its nested objects should be frozen (immutable)."""
    cfg_path = _write_config(tmp_path, {})
    cfg = load_config(cfg_path)
    with pytest.raises((AttributeError, TypeError)):
        cfg.timezone = "UTC"  # type: ignore[misc]


def test_source_config(tmp_path):
    """Source config fields are read correctly."""
    cfg_path = _write_config(tmp_path, {})
    cfg = load_config(cfg_path)
    assert cfg.source.name == "fixture"
    assert cfg.source.min_delay_s == 8
    assert cfg.source.max_delay_s == 15


def test_index_base_value(tmp_path):
    """Index base value and min_coverage come through correctly."""
    cfg_path = _write_config(tmp_path, {})
    cfg = load_config(cfg_path)
    assert cfg.index.base_value == 100.0
    assert cfg.index.min_coverage == 0.5
