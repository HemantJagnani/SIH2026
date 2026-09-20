"""
Tests for index_math.py – Phase 4.

Required tests (with exact expected values):
1. Worked example: band relatives [5460/5200, 5916/5800, 5250/5000]
   → Jevons ≈ 1.0399; then full aggregation → Index ≈ 101.02
2. Scale invariance: all prices × k → Index_t = 100 * k^t
3. Order invariance: shuffled quotes give same output
4. Missing quote: removing non-cheapest quote doesn't change index
5. Naive-average trap: one carrier missing on day 2 doesn't produce fake fall
"""
from __future__ import annotations

import math
from datetime import date

import pytest

from apix.index_math import (
    aggregate_index,
    aggregate_route_index,
    compute_coverage,
    jevons_mean,
    item_price,
    weighted_arith_mean,
    weighted_geomean,
)


# ── Unit tests for elementary functions ───────────────────────────────────

class TestJevonsMean:
    def test_single_value(self):
        assert jevons_mean([1.05]) == pytest.approx(1.05, rel=1e-8)

    def test_empty_returns_none(self):
        assert jevons_mean([]) is None

    def test_worked_example(self):
        # From the build guide: [5460/5200, 5916/5800, 5250/5000]
        relatives = [5460 / 5200, 5916 / 5800, 5250 / 5000]
        result = jevons_mean(relatives)
        assert result == pytest.approx(1.0399, rel=1e-4)

    def test_equal_weights(self):
        # For uniform relatives the geometric mean equals the arithmetic mean
        rels = [1.0, 1.0, 1.0]
        assert jevons_mean(rels) == pytest.approx(1.0)


class TestWeightedGeomean:
    def test_equal_weights_matches_geomean(self):
        vals = [1.05, 1.02]
        wts = [0.5, 0.5]
        expected = math.exp((math.log(1.05) + math.log(1.02)) / 2)
        assert weighted_geomean(vals, wts) == pytest.approx(expected, rel=1e-8)

    def test_renormalises_missing_weights(self):
        # With one zero weight, only the non-zero item contributes
        vals = [1.05, 1.02]
        wts = [1.0, 0.0]
        assert weighted_geomean(vals, wts) == pytest.approx(1.05)

    def test_empty_returns_none(self):
        assert weighted_geomean([], []) is None

    def test_worked_example_lead_level(self):
        # From the build guide: Jevons_A ≈ 1.0399, item_B = 1.01
        # weights 0.3, 0.7 → route relative ≈ 1.0189
        rel_a = jevons_mean([5460 / 5200, 5916 / 5800, 5250 / 5000])
        rel_b = 1.01
        result = weighted_geomean([rel_a, rel_b], [0.3, 0.7])
        assert result == pytest.approx(1.0189, rel=1e-4)


class TestWeightedArithMean:
    def test_simple(self):
        assert weighted_arith_mean([1.0, 2.0], [0.5, 0.5]) == pytest.approx(1.5)

    def test_renormalises(self):
        # Only first weight is non-zero
        assert weighted_arith_mean([3.0, 5.0], [1.0, 0.0]) == pytest.approx(3.0)

    def test_empty_returns_none(self):
        assert weighted_arith_mean([], []) is None


class TestItemPrice:
    def test_min(self):
        assert item_price([5000, 4500, 6000], "min") == 4500

    def test_median_odd(self):
        assert item_price([4000, 5000, 6000], "median") == 5000

    def test_empty_returns_none(self):
        assert item_price([], "min") is None

    def test_invalid_statistic_raises(self):
        with pytest.raises(ValueError):
            item_price([5000], "mean")


class TestCoverage:
    def test_full_coverage(self):
        assert compute_coverage(36, 36) == pytest.approx(1.0)

    def test_partial_coverage(self):
        assert compute_coverage(18, 36) == pytest.approx(0.5)

    def test_zero_expected(self):
        assert compute_coverage(0, 0) == 0.0


# ── Full worked example (from build guide) ────────────────────────────────

class TestWorkedExample:
    """
    Band relatives [5460/5200, 5916/5800, 5250/5000] → Jevons ≈ 1.0399
    Lead-time item A (above) with weight 0.3, item B = 1.01 with weight 0.7
    → route relative ≈ 1.0189
    Second route relative = 0.990, route weights 0.7 and 0.3
    → overall relative ≈ 1.0102
    → Index = 100 × 1.0102 ≈ 101.02
    """

    def _build_relatives(self) -> dict[tuple[str, int, str], float]:
        """Build the item_relatives dict matching the worked example."""
        # Route DEL-BOM: lead 7, three bands
        jevons_a = jevons_mean([5460 / 5200, 5916 / 5800, 5250 / 5000])
        # lead 15 on the same route: jevons = 1.01 (the build guide's 'item B')
        jevons_b = 1.01

        # Route DEL-BLR: only one lead window; route relative = 0.990
        # We need one item that gives a geometric mean of 0.990
        return {
            ("DEL-BOM", 7,  "morning"):   jevons_a,   # band relatives compressed into one
            ("DEL-BOM", 15, "morning"):   jevons_b,
            ("DEL-BLR", 7,  "morning"):   0.990,
        }

    def test_overall_index_to_4dp(self):
        relatives = self._build_relatives()
        route_weights = {"DEL-BOM": 0.7, "DEL-BLR": 0.3}
        lead_weights = {7: 0.3, 15: 0.7}

        level, coverage = aggregate_index(
            item_relatives=relatives,
            route_weights=route_weights,
            lead_weights=lead_weights,
            prev_level=100.0,
            min_coverage=0.0,  # don't apply coverage threshold for this test
            n_routes=2,
            n_leads=2,
            n_bands=1,
        )
        assert level == pytest.approx(101.02, rel=1e-4)

    def test_jevons_to_4dp(self):
        result = jevons_mean([5460 / 5200, 5916 / 5800, 5250 / 5000])
        assert result == pytest.approx(1.0399, rel=1e-4)

    def test_route_relative_to_4dp(self):
        jevons_a = jevons_mean([5460 / 5200, 5916 / 5800, 5250 / 5000])
        result = weighted_geomean([jevons_a, 1.01], [0.3, 0.7])
        assert result == pytest.approx(1.0189, rel=1e-4)

    def test_overall_relative_to_4dp(self):
        jevons_a = jevons_mean([5460 / 5200, 5916 / 5800, 5250 / 5000])
        route_a = weighted_geomean([jevons_a, 1.01], [0.3, 0.7])
        result = weighted_arith_mean([route_a, 0.990], [0.7, 0.3])
        assert result == pytest.approx(1.0102, rel=1e-4)


# ── Scale invariance ──────────────────────────────────────────────────────

class TestScaleInvariance:
    """If all prices are multiplied by k, Index_t = 100 × k^t."""

    def test_scale_invariance(self):
        k = 1.10
        # Day 1: all prices × k → all relatives = k → index = 100k
        relatives_d1 = {("DEL-BOM", 7, "morning"): k}
        level_d1, _ = aggregate_index(
            item_relatives=relatives_d1,
            route_weights={"DEL-BOM": 1.0},
            lead_weights={7: 1.0},
            prev_level=100.0,
            min_coverage=0.0,
            n_routes=1,
            n_leads=1,
            n_bands=1,
        )
        assert level_d1 == pytest.approx(100 * k**1, rel=1e-8)

        # Day 2: again multiplied by k → index = 100k²
        relatives_d2 = {("DEL-BOM", 7, "morning"): k}
        level_d2, _ = aggregate_index(
            item_relatives=relatives_d2,
            route_weights={"DEL-BOM": 1.0},
            lead_weights={7: 1.0},
            prev_level=level_d1,
            min_coverage=0.0,
            n_routes=1,
            n_leads=1,
            n_bands=1,
        )
        assert level_d2 == pytest.approx(100 * k**2, rel=1e-8)


# ── Order invariance ──────────────────────────────────────────────────────

class TestOrderInvariance:
    def test_shuffled_jevons_same_result(self):
        rels = [1.05, 1.02, 0.98]
        import random
        rng = random.Random(0)
        shuffled = rels[:]
        rng.shuffle(shuffled)
        assert jevons_mean(rels) == pytest.approx(jevons_mean(shuffled))

    def test_shuffled_arith_mean_same_result(self):
        vals = [1.05, 0.99, 1.02]
        wts = [0.4, 0.3, 0.3]
        paired = list(zip(vals, wts))
        import random
        rng = random.Random(1)
        rng.shuffle(paired)
        v2, w2 = zip(*paired)
        assert weighted_arith_mean(vals, wts) == pytest.approx(weighted_arith_mean(v2, w2))


# ── Missing quote ─────────────────────────────────────────────────────────

class TestMissingQuote:
    def test_removing_non_cheapest_quote_no_change(self):
        """
        Item price = min. Removing a non-cheapest quote should leave
        item_price (and thus the relative) unchanged.
        """
        fares_all = [5000, 5500, 6000]
        fares_without_non_cheapest = [5000, 6000]
        assert item_price(fares_all, "min") == item_price(fares_without_non_cheapest, "min")

    def test_removing_entire_item_renormalises_coverage(self):
        """
        When one item is missing, coverage drops and weights renormalise.
        The index should NOT produce a fake jump.
        """
        # Day with two items
        rels_full = {
            ("DEL-BOM", 7, "morning"): 1.02,
            ("DEL-BOM", 7, "afternoon"): 1.03,
        }
        # Day with only one item (one carrier's page fails)
        rels_missing = {
            ("DEL-BOM", 7, "morning"): 1.02,
        }

        level_full, _ = aggregate_index(
            item_relatives=rels_full,
            route_weights={"DEL-BOM": 1.0},
            lead_weights={7: 1.0},
            prev_level=100.0,
            min_coverage=0.0,
            n_routes=1,
            n_leads=1,
            n_bands=2,
        )
        level_missing, _ = aggregate_index(
            item_relatives=rels_missing,
            route_weights={"DEL-BOM": 1.0},
            lead_weights={7: 1.0},
            prev_level=100.0,
            min_coverage=0.0,
            n_routes=1,
            n_leads=1,
            n_bands=2,
        )
        # Both reflect only the observed items; the "missing" case
        # uses only its own Jevons, not a naive mean of all.
        assert level_missing == pytest.approx(100.0 * 1.02, rel=1e-6)
        assert level_full != level_missing  # they differ because full uses 2 rels

    def test_low_coverage_suppresses_level(self):
        relatives = {("DEL-BOM", 7, "morning"): 1.10}
        level, coverage = aggregate_index(
            item_relatives=relatives,
            route_weights={"DEL-BOM": 1.0},
            lead_weights={7: 1.0},
            prev_level=100.0,
            min_coverage=0.9,  # high threshold
            n_routes=2,
            n_leads=2,
            n_bands=3,
        )
        assert level is None
        assert coverage < 0.9


# ── Naive-average trap ────────────────────────────────────────────────────

class TestNaiveAverageTrap:
    """
    On day 2, one carrier's page fails → that carrier's quote is absent.
    The relative must come from the matched item, not from a naive mean
    of all remaining fares (which would show a false fall).
    """

    def test_matched_item_not_naive_mean(self):
        # Day 1: two fares, item price (min) = 5000
        day1_fares = [5000, 5500]
        day1_min = item_price(day1_fares, "min")  # 5000

        # Day 2: one carrier absent, remaining fare = 5500 (not cheaper)
        # Naive mean would be 5500 → apparent 10% rise
        # But item min is still 5500 (only fare present), so relative = 5500/5000 = 1.10
        # NOT the naive mean of (5000+5500)/2 vs 5500
        day2_fares = [5500]
        day2_min = item_price(day2_fares, "min")

        relative = day2_min / day1_min
        assert relative == pytest.approx(1.10, rel=1e-6)

        # Contrast: naive mean of day 1 = 5250, vs day 2 = 5500 → 1.0476
        naive_day1 = sum(day1_fares) / len(day1_fares)
        naive_relative = day2_fares[0] / naive_day1
        assert naive_relative != pytest.approx(relative)
