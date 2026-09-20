"""
Tests for clean.py – Phase 3.

Covers:
1. Price parsing: ₹ symbol, commas, plain floats, None, unparseable
2. Carrier normalisation
3. dep_time normalisation (HH:MM, AM/PM)
4. dep_band assignment
5. sold_out preserved as True
6. Anomaly flagging (with mocked DB history)
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from apix.clean import (
    assign_dep_band,
    clean_quotes,
    normalise_carrier,
    normalise_dep_time,
    parse_price,
)
from apix.models import Quote


# ── Price parsing tests ────────────────────────────────────────────────────

class TestParsePrice:
    def test_plain_int(self):
        assert parse_price(5000) == 5000.0

    def test_plain_float(self):
        assert parse_price(4321.50) == 4321.50

    def test_string_with_rupee_and_comma(self):
        assert parse_price("₹ 5,220") == 5220.0

    def test_string_plain(self):
        assert parse_price("4650") == 4650.0

    def test_string_comma_only(self):
        assert parse_price("5,200.00") == 5200.0

    def test_none_returns_none(self):
        assert parse_price(None) is None

    def test_unparseable_returns_none(self):
        result = parse_price("SOLD OUT")
        assert result is None

    def test_empty_string_returns_none(self):
        assert parse_price("") is None


# ── dep_time normalisation ────────────────────────────────────────────────

class TestNormaliseDepTime:
    def test_already_hhmm(self):
        assert normalise_dep_time("06:30") == "06:30"

    def test_single_digit_hour(self):
        assert normalise_dep_time("6:30") == "06:30"

    def test_am_suffix(self):
        assert normalise_dep_time("06:30 AM") == "06:30"

    def test_pm_suffix(self):
        assert normalise_dep_time("06:30 PM") == "18:30"

    def test_noon_pm(self):
        assert normalise_dep_time("12:00 PM") == "12:00"

    def test_midnight_am(self):
        assert normalise_dep_time("12:00 AM") == "00:00"

    def test_none_returns_none(self):
        assert normalise_dep_time(None) is None

    def test_garbage_returns_none(self):
        assert normalise_dep_time("EARLY MORNING") is None


# ── dep_band assignment ───────────────────────────────────────────────────

class TestAssignDepBand:
    def test_morning(self):
        assert assign_dep_band("05:00") == "morning"
        assert assign_dep_band("11:59") == "morning"

    def test_afternoon(self):
        assert assign_dep_band("12:00") == "afternoon"
        assert assign_dep_band("17:59") == "afternoon"

    def test_evening(self):
        assert assign_dep_band("18:00") == "evening"
        assert assign_dep_band("23:59") == "evening"

    def test_none_returns_none(self):
        assert assign_dep_band(None) is None

    def test_pre_morning_returns_none(self):
        # Before 05:00 → no band assigned
        assert assign_dep_band("03:00") is None


# ── Carrier normalisation ──────────────────────────────────────────────────

class TestNormaliseCarrier:
    def test_indigo_alias(self):
        assert normalise_carrier("indigo") == "IndiGo"
        assert normalise_carrier("IndiGo") == "IndiGo"

    def test_air_india(self):
        assert normalise_carrier("air india") == "Air India"

    def test_unknown_preserved(self):
        assert normalise_carrier("SomeNewAirline") == "SomeNewAirline"

    def test_none_returns_unknown(self):
        assert normalise_carrier(None) == "Unknown"


# ── Full clean_quotes pipeline ─────────────────────────────────────────────

def _make_quote(**kwargs) -> Quote:
    defaults = dict(
        run_id=1,
        obs_date=date(2026, 1, 10),
        source="fixture",
        route="DEL-BOM",
        origin="DEL",
        destination="BOM",
        travel_date=date(2026, 1, 17),
        lead_days=7,
        carrier="indigo",
        flight_no="6E-101",
        dep_time="06:30",
        dep_band=None,
        stops=0,
        fare_class="economy",
        base_fare=None,
        taxes=None,
        total_fare=5000,
        sold_out=False,
        parse_ok=True,
        anomaly_flag=False,
        is_synthetic=False,
    )
    defaults.update(kwargs)
    return Quote(**defaults)


class TestCleanQuotes:
    def test_normal_quote_cleaned(self):
        q = _make_quote(carrier="indigo", dep_time="06:30", total_fare=5000)
        [cleaned] = clean_quotes([q])
        assert cleaned.carrier == "IndiGo"
        assert cleaned.dep_time == "06:30"
        assert cleaned.dep_band == "morning"
        assert cleaned.total_fare == 5000.0
        assert cleaned.parse_ok is True

    def test_rupee_price_parsed(self):
        q = _make_quote(total_fare="₹ 5,220")
        [cleaned] = clean_quotes([q])
        assert cleaned.total_fare == 5220.0

    def test_unparseable_price_sets_parse_ok_false(self):
        q = _make_quote(total_fare="SOLD OUT TEXT")
        [cleaned] = clean_quotes([q])
        assert cleaned.parse_ok is False
        assert cleaned.total_fare is None

    def test_sold_out_preserved(self):
        q = _make_quote(sold_out=True, total_fare=None)
        [cleaned] = clean_quotes([q])
        assert cleaned.sold_out is True

    def test_none_price_not_a_parse_failure(self):
        """None total_fare (already null) should not set parse_ok to False."""
        q = _make_quote(total_fare=None, sold_out=True)
        [cleaned] = clean_quotes([q])
        assert cleaned.parse_ok is True

    def test_pm_time_converted(self):
        q = _make_quote(dep_time="6:30 PM")
        [cleaned] = clean_quotes([q])
        assert cleaned.dep_time == "18:30"
        assert cleaned.dep_band == "evening"

    def test_anomaly_flag_set_when_outlier(self):
        """A price 3× the median should be flagged as an anomaly."""
        from apix.clean import flag_anomalies

        q = _make_quote(total_fare=15000.0, obs_date=date(2026, 1, 10), dep_band="morning")

        # Provide 5 days of history with median ~5000
        mock_rows = [
            {"price": 5000},
            {"price": 5100},
            {"price": 5050},
            {"price": 4900},
            {"price": 5200},
        ]
        mock_con = MagicMock()
        with patch("apix.clean.get_items_before", return_value=mock_rows):
            result = flag_anomalies([q], con=mock_con)
        assert result[0].anomaly_flag is True

    def test_no_anomaly_flag_when_insufficient_history(self):
        """Less than 5 days of history → no flagging."""
        from apix.clean import flag_anomalies

        q = _make_quote(total_fare=15000.0, dep_band="morning")
        mock_rows = [{"price": 5000}, {"price": 5100}]  # only 2 days
        mock_con = MagicMock()
        with patch("apix.clean.get_items_before", return_value=mock_rows):
            result = flag_anomalies([q], con=mock_con)
        assert result[0].anomaly_flag is False
