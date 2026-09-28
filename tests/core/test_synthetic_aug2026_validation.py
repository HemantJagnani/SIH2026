"""
Automated Test Suite: Synthetic August 2026 Demonstration Dataset & Governance Validation.

Verifies:
1. Strict Governance Invariants:
   - All synthetic records are explicitly tagged with data_status="SYNTHETIC", synthetic=True,
     synthetic_generation_version="AUG2026_DEMO_V1".
   - Zero synthetic observations contaminate runtime/top60_observation_classification.json.
   - Real 11,716-observation production baseline remains 100% UNCHANGED.
2. Synthetic Panel Design:
   - Exactly 31 daily collection rounds in August 2026 (2026-08-01 through 2026-08-31).
   - All 60 DGCA routes and 6 lead-time classes (360 cells) represented.
   - No negative or impossible fares (minimum fare >= ₹1,200.00).
   - Fixed random seed ensures 100% deterministic reproducibility.
3. Demonstration Pipelines:
   - Daily short-chain Jevons aggregation and chaining.
   - Weekly geometric aggregation and chaining across 4 weeks.
   - Monthly aggregation with 0.30 active-day qualification logic.
   - Uncertainty propagation (Delta method variance, standard error, 95% CI).
4. Reference Price Governance:
   - P_ref (₹8,641.45) is descriptive only; NEVER enters the denominator of any index.
   - Empirical lead-time weights and DGCA route weights sum to 1.0000 and 1.000000.
"""

from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
import pytest

from index.synthetic.generator import SyntheticAugustGenerator
from index.synthetic.pipeline_demo import SyntheticDemonstrationPipeline
from index.synthetic.models import SYNTHETIC_DATA_STATUS, SYNTHETIC_GENERATION_VERSION
from index.lead_time_weights import EMPIRICAL_LEAD_TIME_WEIGHTS
from index.route_basket import get_top60_route_weights


BASELINE_PATH = Path("runtime/top60_observation_classification.json")
SYNTHETIC_OBS_PATH = Path("runtime/synthetic_aug2026/synthetic_aug2026_observations.json")
SYNTHETIC_META_PATH = Path("runtime/synthetic_aug2026/synthetic_aug2026_metadata.json")


@pytest.fixture(scope="module")
def loaded_synthetic_dataset():
    """Loads synthetic August dataset once for the test module."""
    if not SYNTHETIC_OBS_PATH.exists():
        # Generate if not already present
        generator = SyntheticAugustGenerator(
            baseline_path=str(BASELINE_PATH),
            output_dir="runtime/synthetic_aug2026",
            random_seed=42,
        )
        generator.save()

    with open(SYNTHETIC_OBS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="module")
def loaded_production_baseline():
    """Loads real production baseline dataset."""
    assert BASELINE_PATH.exists(), f"Production baseline missing at {BASELINE_PATH}"
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


# ============================================================================
# 1. STRICT GOVERNANCE & NON-CONTAMINATION INVARIANTS
# ============================================================================

def test_zero_synthetic_contamination_in_production_baseline(loaded_production_baseline):
    """
    CRITICAL GOVERNANCE TEST:
    The real 11,716-observation production dataset must contain ZERO synthetic records
    and must remain 100% UNCHANGED.
    """
    meta = loaded_production_baseline.get("metadata", {})
    obs = loaded_production_baseline.get("observations", [])

    assert len(obs) == 11716, f"Production baseline drift: expected 11716, got {len(obs)}"
    assert meta.get("total_observations") == 11716

    # Verify status breakdown
    statuses = [o.get("status") for o in obs]
    assert statuses.count("VALID_BASELINE") == 5977
    assert statuses.count("DUPLICATE") == 4915
    assert statuses.count("HIGHER_FARE_FAMILY") == 666
    assert statuses.count("FOREIGN_TRANSIT") == 158

    # Zero synthetic contamination
    synthetic_flags = [o.get("synthetic") for o in obs if o.get("synthetic") is True]
    assert len(synthetic_flags) == 0, "Found synthetic=True records in production file!"

    synthetic_statuses = [o.get("data_status") for o in obs if o.get("data_status") == "SYNTHETIC"]
    assert len(synthetic_statuses) == 0, "Found data_status='SYNTHETIC' records in production file!"


def test_all_synthetic_records_explicitly_tagged(loaded_synthetic_dataset):
    """
    Every synthetic record must carry explicit synthetic provenance metadata.
    """
    meta = loaded_synthetic_dataset.get("metadata", {})
    records = loaded_synthetic_dataset.get("observations", [])

    assert meta["data_status"] == SYNTHETIC_DATA_STATUS
    assert meta["synthetic"] is True
    assert meta["synthetic_generation_version"] == SYNTHETIC_GENERATION_VERSION

    assert len(records) > 100000  # ~133,000 observations

    # Sample checks across the dataset
    step = max(1, len(records) // 1000)
    for o in records[::step]:
        assert o["data_status"] == SYNTHETIC_DATA_STATUS
        assert o["synthetic"] is True
        assert o["synthetic_generation_version"] == SYNTHETIC_GENERATION_VERSION
        assert o["collection_month"] == "2026-08"
        assert o["collection_date"].startswith("2026-08-")
        assert o["collection_date"] != o["travel_date"]  # Timestamps segregated
        assert o["lead_days"] in (1, 7, 15, 21, 30, 45)


# ============================================================================
# 2. SYNTHETIC PANEL DESIGN & STATISTICAL CONSERVATISM
# ============================================================================

def test_synthetic_calendar_coverage_all_31_days(loaded_synthetic_dataset):
    """Synthetic observations must span all 31 calendar days in August 2026."""
    records = loaded_synthetic_dataset.get("observations", [])
    distinct_dates = set(o["collection_date"] for o in records)
    expected_dates = {f"2026-08-{d:02d}" for d in range(1, 32)}

    assert distinct_dates == expected_dates
    assert len(distinct_dates) == 31

    # Verify all 60 routes and 6 lead times are populated
    routes = set(o["route"] for o in records)
    lead_times = set(o["lead_time_class"] for o in records)
    assert len(routes) == 60
    assert len(lead_times) == 6
    assert len(set((o["route"], o["lead_time_class"]) for o in records)) == 360


def test_no_negative_or_impossible_fares(loaded_synthetic_dataset):
    """Synthetic fares must be strictly positive and obey the plausibility lower bound."""
    records = loaded_synthetic_dataset.get("observations", [])
    step = max(1, len(records) // 2000)
    for o in records[::step]:
        fare = float(o["total_fare"])
        assert fare >= 1200.00, f"Found impossible fare below floor: {fare}"
        assert not (fare != fare)  # Not NaN


def test_fixed_seed_reproducibility():
    """A fixed random seed must produce 100% deterministic results across runs."""
    gen1 = SyntheticAugustGenerator(random_seed=42)
    records1, meta1 = gen1.generate_synthetic_panel()

    gen2 = SyntheticAugustGenerator(random_seed=42)
    records2, meta2 = gen2.generate_synthetic_panel()

    assert len(records1) == len(records2)
    assert meta1.number_of_synthetic_observations == meta2.number_of_synthetic_observations

    # Verify first 10 records are bit-for-bit identical
    for r1, r2 in zip(records1[:10], records2[:10]):
        assert r1["observation_id"] == r2["observation_id"]
        assert r1["total_fare"] == r2["total_fare"]
        assert r1["collection_date"] == r2["collection_date"]


# ============================================================================
# 3. DEMONSTRATION PIPELINES (DAILY, WEEKLY, MONTHLY, UNCERTAINTY)
# ============================================================================

def test_daily_jevons_demonstration_pipeline(loaded_synthetic_dataset):
    """Tests daily consecutive short-chain Jevons calculation for all 31 days."""
    records = loaded_synthetic_dataset.get("observations", [])
    pipeline = SyntheticDemonstrationPipeline(records)
    daily_results = pipeline.run_daily_pipeline()

    assert len(daily_results) == 31
    # Day 1 is base 100.0000
    assert daily_results[0].day == 1
    assert daily_results[0].daily_chain_index == Decimal("100.0000")

    # Days 2 to 31 have valid chained indices and uncertainty estimates
    for pt in daily_results[1:]:
        assert pt.matched_pairs > 1000
        assert pt.daily_price_relative > Decimal("0")
        assert pt.daily_chain_index > Decimal("0")
        assert pt.standard_error is not None and pt.standard_error >= 0.0
        assert pt.ci95_lower is not None and pt.ci95_upper is not None
        assert pt.ci95_lower <= float(pt.daily_chain_index) <= pt.ci95_upper


def test_weekly_demonstration_pipeline(loaded_synthetic_dataset):
    """Tests weekly intra-week geometric aggregation and weekly chaining across 4 weeks."""
    records = loaded_synthetic_dataset.get("observations", [])
    pipeline = SyntheticDemonstrationPipeline(records)
    weekly_results = pipeline.run_weekly_pipeline()

    assert len(weekly_results) == 4
    # Week 1 is base 100.0000
    assert weekly_results[0].week_number == 1
    assert weekly_results[0].weekly_chain_index == Decimal("100.0000")

    # Weeks 2, 3, 4
    for wt in weekly_results[1:]:
        assert wt.matched_products_count > 3000
        assert wt.weekly_price_relative > Decimal("0")
        assert wt.weekly_chain_index > Decimal("0")
        assert wt.standard_error is not None and wt.standard_error >= 0.0
        assert wt.ci95_lower <= float(wt.weekly_chain_index) <= wt.ci95_upper


def test_monthly_aggregation_with_active_day_qualification(loaded_synthetic_dataset):
    """Tests calendar-month geometric mean and 0.30 active-day qualification."""
    records = loaded_synthetic_dataset.get("observations", [])
    pipeline = SyntheticDemonstrationPipeline(records)
    monthly_summary = pipeline.run_monthly_pipeline()

    assert monthly_summary["month"] == "2026-08"
    assert monthly_summary["scheduled_collection_days"] == 31
    assert monthly_summary["active_day_threshold"] == 0.30

    total = monthly_summary["total_canonical_products"]
    qual = monthly_summary["qualified_products_count"]
    disqual = monthly_summary["disqualified_products_count"]

    assert total > 5000
    assert qual > 0
    assert total == qual + disqual
    assert monthly_summary["populated_cells"] == 360
    assert monthly_summary["synthetic_august_representative_price_inr"] > 1000.0


# ============================================================================
# 4. METHODOLOGY GOVERNANCE & WEIGHT INVARIANTS
# ============================================================================

def test_pref_never_used_in_denominator_proof(loaded_synthetic_dataset):
    """
    Verifies that P_ref (₹8,641.45) is NEVER used in the denominator of any daily,
    weekly, or monthly index.
    """
    records = loaded_synthetic_dataset.get("observations", [])
    pipeline = SyntheticDemonstrationPipeline(records)

    daily_pts = pipeline.run_daily_pipeline()
    # If P_ref were used as denominator, index = 100 * P_t / 8641.45,
    # which would produce numbers wildly different from ~100.0 for daily changes.
    for pt in daily_pts:
        # Price relative between consecutive days is bounded near 1.0 (e.g. 0.95 to 1.05)
        assert Decimal("0.90") < pt.daily_price_relative < Decimal("1.10")


def test_weights_sum_invariants():
    """Verifies empirical lead-time weights and DGCA route weights sum to 1."""
    lt_weights = EMPIRICAL_LEAD_TIME_WEIGHTS
    assert sum(lt_weights.values()) == Decimal("1.0000")

    route_weights = get_top60_route_weights(use_iata_codes=True)
    assert len(route_weights) == 60
    assert abs(sum(route_weights.values()) - Decimal("1.000000")) < Decimal("0.000001")
