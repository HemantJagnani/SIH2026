"""
Production Regression Audit on Top 60 Matrix Dataset (11,430 observations).
Governance: APIx_PRODUCT_DEF_v2.0_FROZEN / APIX_METHODOLOGY_V1
"""

import json
from collections import defaultdict
from pathlib import Path
import pytest

from reconciliation.pipeline import CrossSourceReconciliationPipeline
from index.route_basket import get_dgca_cy2024_top60_basket

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLASSIFICATION_PATH = PROJECT_ROOT / "runtime" / "top60_observation_classification.json"
IMMUTABLE_11430_PATH = PROJECT_ROOT / "runtime" / "top60_observation_classification_11430_immutable.json"


def test_production_invariants_11430_immutable_snapshot():
    """
    Verify immutable pre-merge snapshot remains 100% intact:
    - Raw observations = 11,430
    - Valid APIx baseline = 5,834
    - Duplicates = 4,772
    - Higher fare family = 666
    - Foreign transit = 158
    - 5,834 + 4,772 + 666 + 158 = 11,430
    - Populated cells = 347/360
    - DGCA-weighted coverage = 97.5232%
    """
    assert IMMUTABLE_11430_PATH.exists(), f"Missing {IMMUTABLE_11430_PATH}"

    with open(IMMUTABLE_11430_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_obs = data.get("observations", [])
    assert len(raw_obs) == 11430, f"Expected 11,430 raw observations, got {len(raw_obs)}"

    pipeline = CrossSourceReconciliationPipeline()
    valid_apix, excluded, diag = pipeline.run(raw_obs)

    # 1. Total counts
    valid_count = len(valid_apix)
    dup_count = sum(diag.duplicates_by_source.values())
    higher_count = diag.higher_fare_family_exclusions
    foreign_count = diag.foreign_transit_exclusions

    assert valid_count == 5834, f"Expected 5,834 valid baseline observations, got {valid_count}"
    assert dup_count == 4772, f"Expected 4,772 duplicate observations, got {dup_count}"
    assert higher_count == 666, f"Expected 666 higher fare family exclusions, got {higher_count}"
    assert foreign_count == 158, f"Expected 158 foreign transit exclusions, got {foreign_count}"

    # 2. Mathematical invariant
    assert valid_count + dup_count + higher_count + foreign_count == 11430

    # 3. Populated cells (347/360)
    cells = set((o.route, o.lead_time) for o in valid_apix)
    assert len(cells) == 347, f"Expected 347 populated cells, got {len(cells)}"

    # 4. DGCA-weighted basket coverage (97.5232%)
    basket = get_dgca_cy2024_top60_basket()
    routes_populated = defaultdict(int)
    for o in valid_apix:
        routes_populated[o.route] += 1

    weighted_cov = sum(
        r.route_weight
        for r in basket.routes
        if routes_populated[r.route_id] > 0
        or routes_populated[f"{r.route_id.split('-')[1]}-{r.route_id.split('-')[0]}"] > 0
    )
    cov_pct = round(float(weighted_cov) * 100, 4)
    assert cov_pct == 97.5232, f"Expected 97.5232% DGCA-weighted coverage, got {cov_pct}%"


def test_production_invariants_360_cells_11716():
    """
    Verify complete finalized production matrix (360/360 populated cells, 0 missing):
    - Raw observations = 11,716 (11,430 base + 270 GAU + 16 IDR-BOM T+7)
    - Valid APIx baseline = 5,977 (5,834 base + 135 GAU + 8 IDR-BOM T+7)
    - Duplicates = 4,915 (4,772 base + 135 GAU + 8 IDR-BOM T+7)
    - Higher fare family = 666
    - Foreign transit = 158
    - 5,977 + 4,915 + 666 + 158 = 11,716
    - Populated cells = 360/360 (100.0%)
    - Missing cells = 0
    - DGCA-weighted coverage = 100.0000%
    """
    assert CLASSIFICATION_PATH.exists(), f"Missing {CLASSIFICATION_PATH}"

    with open(CLASSIFICATION_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_obs = data.get("observations", [])
    assert len(raw_obs) == 11716, f"Expected 11,716 raw observations, got {len(raw_obs)}"

    pipeline = CrossSourceReconciliationPipeline()
    valid_apix, excluded, diag = pipeline.run(raw_obs)

    # 1. Total counts
    valid_count = len(valid_apix)
    dup_count = sum(diag.duplicates_by_source.values())
    higher_count = diag.higher_fare_family_exclusions
    foreign_count = diag.foreign_transit_exclusions

    assert valid_count == 5977, f"Expected 5,977 valid baseline observations, got {valid_count}"
    assert dup_count == 4915, f"Expected 4,915 duplicate observations, got {dup_count}"
    assert higher_count == 666, f"Expected 666 higher fare family exclusions, got {higher_count}"
    assert foreign_count == 158, f"Expected 158 foreign transit exclusions, got {foreign_count}"

    # 2. Mathematical invariant
    assert valid_count + dup_count + higher_count + foreign_count == 11716

    # 3. Populated cells (360/360)
    cells = set((o.route, o.lead_time) for o in valid_apix)
    assert len(cells) == 360, f"Expected 360 populated cells, got {len(cells)}"

    # 4. DGCA-weighted basket coverage (100.0%)
    basket = get_dgca_cy2024_top60_basket()
    routes_populated = defaultdict(int)
    for o in valid_apix:
        routes_populated[o.route] += 1

    weighted_cov = sum(
        r.route_weight
        for r in basket.routes
        if routes_populated[r.route_id] > 0
        or routes_populated[f"{r.route_id.split('-')[1]}-{r.route_id.split('-')[0]}"] > 0
    )
    cov_pct = round(float(weighted_cov) * 100, 4)
    assert cov_pct == 100.0, f"Expected 100.0% DGCA-weighted coverage, got {cov_pct}%"


def test_classify_batch_invariants():
    """Verify classify_batch generates the exact 360-cell production status summary with 0 discrepancy."""
    with open(CLASSIFICATION_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_obs = data.get("observations", [])
    pipeline = CrossSourceReconciliationPipeline()
    cls_summary = pipeline.classify_batch(raw_obs)

    summary = cls_summary["status_summary"]
    assert summary["VALID_BASELINE"] == 5977
    assert summary["DUPLICATE"] == 4915
    assert summary["HIGHER_FARE_FAMILY"] == 666
    assert summary["FOREIGN_TRANSIT"] == 158
    assert cls_summary["total_observations"] == 11716
    assert cls_summary["discrepancy"] == 0
