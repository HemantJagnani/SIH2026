"""
Unit tests for the APIx index engine.

Tests verify:
1.  Route weights sum to 1
2.  Lead-time weights sum to 1
3.  Median aggregation
4.  Outlier detection
5.  Missing-price handling
6.  Route index formula
7.  Overall APIx formula (golden test)
8.  Daily change calculation
9.  Monthly change calculation
10. Base-period behaviour (index = 100)
"""
import pytest
from app.services.index_engine.calculator import (
    calculate_airfare_index,
    calculate_daily_change,
    calculate_median_fare,
    calculate_monthly_index,
    calculate_period_change,
    calculate_route_index,
    calculate_route_price,
    detect_outlier,
)
from app.core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Route weights sum to 1
# ─────────────────────────────────────────────────────────────────────────────

def test_route_weights_sum_to_one():
    total = sum(settings.ROUTE_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"Route weights sum to {total}, expected 1.0"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Lead-time weights sum to 1
# ─────────────────────────────────────────────────────────────────────────────

def test_lead_time_weights_sum_to_one():
    total = sum(settings.LEAD_TIME_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"Lead-time weights sum to {total}, expected 1.0"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Median aggregation
# ─────────────────────────────────────────────────────────────────────────────

def test_median_fare_odd_count():
    fares = [4900.0, 5000.0, 5100.0]
    assert calculate_median_fare(fares) == 5000.0


def test_median_fare_even_count():
    fares = [4900.0, 5100.0]
    assert calculate_median_fare(fares) == 5000.0


def test_median_fare_single():
    assert calculate_median_fare([4500.0]) == 4500.0


def test_median_fare_two_values():
    assert calculate_median_fare([8500.0, 6250.0]) == pytest.approx(7375.0)


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Outlier detection
# ─────────────────────────────────────────────────────────────────────────────

def test_outlier_exceeds_threshold():
    fare = 20000.0
    median = 5000.0
    is_out, reason = detect_outlier(fare, median, threshold=3.0)
    assert is_out is True
    assert reason is not None
    assert "outlier" in reason.lower() or "median" in reason.lower()


def test_outlier_within_threshold():
    fare = 5500.0
    median = 5000.0
    is_out, reason = detect_outlier(fare, median, threshold=3.0)
    assert is_out is False
    assert reason is None


def test_outlier_exactly_threshold():
    fare = 15000.0
    median = 5000.0
    # 15000 == 3 * 5000 — NOT greater than, so not an outlier
    is_out, reason = detect_outlier(fare, median, threshold=3.0)
    assert is_out is False


def test_outlier_zero_median():
    fare = 5000.0
    is_out, reason = detect_outlier(fare, 0.0)
    assert is_out is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Missing-price handling
# ─────────────────────────────────────────────────────────────────────────────

def test_median_fare_empty_returns_none():
    result = calculate_median_fare([])
    assert result is None


def test_route_price_all_missing():
    lead_time_fares = {1: None, 7: None, 30: None}
    lead_time_weights = {1: 1/3, 7: 1/3, 30: 1/3}
    result = calculate_route_price(lead_time_fares, lead_time_weights)
    assert result is None


def test_route_index_missing_price():
    result = calculate_route_index(None, 6000.0)
    assert result is None


def test_airfare_index_all_none():
    result = calculate_airfare_index(
        {"DEL-BOM": None, "DEL-BLR": None, "BOM-BLR": None},
        {"DEL-BOM": 0.5, "DEL-BLR": 0.3, "BOM-BLR": 0.2},
    )
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Route index formula
# ─────────────────────────────────────────────────────────────────────────────

def test_route_index_formula():
    """RouteIndex = (6583.33 / 6000) × 100 = 109.7222"""
    result = calculate_route_index(6583.33, 6000.0)
    assert result == pytest.approx(109.7222, abs=0.01)


def test_route_index_base_period():
    """At base period, price == base_price → index == 100.0"""
    result = calculate_route_index(6000.0, 6000.0)
    assert result == pytest.approx(100.0)


def test_route_index_price_increase():
    result = calculate_route_index(7500.0, 5000.0)
    assert result == pytest.approx(150.0)


def test_route_index_price_decrease():
    result = calculate_route_index(4000.0, 5000.0)
    assert result == pytest.approx(80.0)


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Overall APIx formula — GOLDEN CALCULATION TEST
# ─────────────────────────────────────────────────────────────────────────────

def test_golden_apix_calculation():
    """
    Golden test — verifies the exact APIx formula from the master spec §34.

    Input:
        DEL-BOM = 109.72, weight 0.50
        DEL-BLR = 112.42, weight 0.30
        BOM-BLR = 105.00, weight 0.20

    Expected:
        0.50(109.72) + 0.30(112.42) + 0.20(105.00)
        = 54.86 + 33.726 + 21.00
        = 109.586
        ≈ 109.59 (rounded to 2 dp)
    """
    route_indices = {
        "DEL-BOM": 109.72,
        "DEL-BLR": 112.42,
        "BOM-BLR": 105.00,
    }
    route_weights = {
        "DEL-BOM": 0.50,
        "DEL-BLR": 0.30,
        "BOM-BLR": 0.20,
    }

    result = calculate_airfare_index(route_indices, route_weights)
    assert result is not None

    # Raw value should be 109.586
    assert result == pytest.approx(109.586, abs=0.001)

    # Rounded to 2 decimal places should be 109.59
    assert round(result, 2) == 109.59


def test_apix_partial_routes():
    """Test that missing routes are handled by re-normalising weights."""
    route_indices = {"DEL-BOM": 110.0, "DEL-BLR": None, "BOM-BLR": 105.0}
    route_weights = {"DEL-BOM": 0.50, "DEL-BLR": 0.30, "BOM-BLR": 0.20}
    result = calculate_airfare_index(route_indices, route_weights)
    # Should re-normalise over weight 0.50 + 0.20 = 0.70
    expected = (0.50 * 110.0 + 0.20 * 105.0) / 0.70
    assert result == pytest.approx(expected, abs=0.001)


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Daily change calculation
# ─────────────────────────────────────────────────────────────────────────────

def test_daily_change_positive():
    """
    (114.33 - 109.59) / 109.59 × 100 = 4.3255...%
    """
    result = calculate_daily_change(114.33, 109.59)
    assert result == pytest.approx(4.3255, abs=0.01)


def test_daily_change_negative():
    result = calculate_daily_change(100.0, 110.0)
    assert result == pytest.approx(-9.0909, abs=0.01)


def test_daily_change_no_change():
    result = calculate_daily_change(100.0, 100.0)
    assert result == pytest.approx(0.0)


def test_daily_change_none_previous():
    result = calculate_daily_change(100.0, None)
    assert result is None


def test_daily_change_zero_previous():
    result = calculate_daily_change(100.0, 0.0)
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Monthly change
# ─────────────────────────────────────────────────────────────────────────────

def test_monthly_index_mean():
    """POC monthly index = mean of valid daily values."""
    daily_values = [100.0, 110.0, 120.0]
    result = calculate_monthly_index(daily_values)
    assert result == pytest.approx(110.0)


def test_monthly_index_empty():
    result = calculate_monthly_index([])
    assert result is None


def test_period_change_mom():
    """MoM = (116.20 - 112.00) / 112.00 × 100 = 3.75%"""
    result = calculate_period_change(116.20, 112.00)
    assert result == pytest.approx(3.75, abs=0.01)


def test_period_change_yoy():
    """YoY = (116.20 - 104.00) / 104.00 × 100 = 11.73%"""
    result = calculate_period_change(116.20, 104.00)
    assert result == pytest.approx(11.73, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Base-period behaviour
# ─────────────────────────────────────────────────────────────────────────────

def test_base_period_all_routes_equal_100():
    """
    At base period, current price == base price for all routes.
    APIx should equal 100.0 (or very close due to floating point).
    """
    base_prices = settings.BASE_PRICES
    route_weights = settings.ROUTE_WEIGHTS

    route_indices = {
        route: calculate_route_index(price, price)
        for route, price in base_prices.items()
    }

    apix = calculate_airfare_index(route_indices, route_weights)
    assert apix == pytest.approx(100.0, abs=0.001)


def test_route_price_equal_weighted_average():
    """
    With equal lead-time weights (1/3 each), route price = simple mean.
    """
    lead_time_fares = {1: 8500.0, 7: 6250.0, 30: 5000.0}
    lead_time_weights = {1: 1/3, 7: 1/3, 30: 1/3}
    result = calculate_route_price(lead_time_fares, lead_time_weights)
    expected = (8500.0 + 6250.0 + 5000.0) / 3
    assert result == pytest.approx(expected, abs=0.01)


def test_route_price_partial_lead_times():
    """If one lead time has no data, remaining weights are re-normalised."""
    lead_time_fares = {1: 8500.0, 7: None, 30: 5000.0}
    lead_time_weights = {1: 1/3, 7: 1/3, 30: 1/3}
    result = calculate_route_price(lead_time_fares, lead_time_weights)
    # Re-normalised: (1/3 * 8500 + 1/3 * 5000) / (2/3)
    expected = (8500.0 + 5000.0) / 2
    assert result == pytest.approx(expected, abs=0.01)
