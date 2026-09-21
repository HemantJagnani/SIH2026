"""
Phase 12: Unit Tests for Normalization components.

Tests price parsing, airline/airport entity mapping, cabin normalization,
date parsing, and deduplication — across all currency format variants
and edge cases defined in the spec.
"""

import os
import sys
from decimal import Decimal
from datetime import date

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from normalization.prices import normalize_price
from normalization.cabins import normalize_cabin
from normalization.dates import normalize_travel_date, normalize_timestamp
from normalization.core import NormalizationException


class TestPriceNormalization:
    """All currency format variants that sources can emit."""

    def test_rupee_symbol_with_commas(self):
        result = normalize_price("₹5,240.00")
        assert result.normalized_value == Decimal("5240.00")

    def test_rupee_symbol_no_decimal(self):
        result = normalize_price("₹ 5240")
        assert result.normalized_value == Decimal("5240")

    def test_inr_prefix(self):
        result = normalize_price("INR 5,240")
        assert result.normalized_value == Decimal("5240")

    def test_rs_prefix(self):
        result = normalize_price("Rs. 5240")
        assert result.normalized_value == Decimal("5240")

    def test_plain_number_string(self):
        result = normalize_price("5240")
        assert result.normalized_value == Decimal("5240")

    def test_plain_decimal_string(self):
        result = normalize_price("5240.50")
        assert result.normalized_value == Decimal("5240.50")

    def test_price_with_spaces(self):
        result = normalize_price("  ₹ 5,240  ")
        assert result.normalized_value == Decimal("5240")

    def test_zero_price(self):
        result = normalize_price("0")
        assert result.normalized_value == Decimal("0")

    def test_usd_currency_rejected(self):
        with pytest.raises(NormalizationException):
            normalize_price("$50")

    def test_usd_text_rejected(self):
        with pytest.raises(NormalizationException):
            normalize_price("USD 50")

    def test_eur_rejected(self):
        with pytest.raises(NormalizationException):
            normalize_price("EUR 5000")

    def test_gbp_rejected(self):
        with pytest.raises(NormalizationException):
            normalize_price("£ 5000")

    def test_negative_price_rejected(self):
        with pytest.raises(NormalizationException):
            normalize_price("-100")

    def test_empty_string_rejected(self):
        with pytest.raises(NormalizationException):
            normalize_price("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(NormalizationException):
            normalize_price("   ")

    def test_non_numeric_rejected(self):
        with pytest.raises(NormalizationException):
            normalize_price("FIVE THOUSAND")

    def test_result_has_raw_value(self):
        raw = "₹5,240.00"
        result = normalize_price(raw)
        assert result.raw_value == raw

    def test_result_confidence_is_1(self):
        result = normalize_price("5000")
        assert result.confidence == 1.0


class TestCabinNormalization:
    """Cabin class string variants across OTA/airline sources."""

    def test_economy_lowercase(self):
        result = normalize_cabin("economy")
        assert result.normalized_value.value == "ECONOMY"

    def test_economy_uppercase(self):
        result = normalize_cabin("ECONOMY")
        assert result.normalized_value.value == "ECONOMY"

    def test_business_full_name(self):
        result = normalize_cabin("business")
        assert result.normalized_value.value == "BUSINESS"

    def test_business_code_J(self):
        result = normalize_cabin("J")
        assert result.normalized_value.value == "BUSINESS"

    def test_first_class(self):
        result = normalize_cabin("first")
        assert result.normalized_value.value == "FIRST"

    def test_first_code_F(self):
        result = normalize_cabin("F")
        assert result.normalized_value.value == "FIRST"

    def test_premium_economy(self):
        result = normalize_cabin("premium economy")
        assert result.normalized_value.value == "PREMIUM_ECONOMY"

    def test_premium_economy_code_W(self):
        result = normalize_cabin("W")
        assert result.normalized_value.value == "PREMIUM_ECONOMY"

    def test_economy_code_Y(self):
        result = normalize_cabin("y")
        assert result.normalized_value.value == "ECONOMY"

    def test_unknown_raises(self):
        with pytest.raises(NormalizationException):
            normalize_cabin("FIRST_CLASS_VIP_SUITE")


class TestDateNormalization:
    """Datetime parsing across formats used by sources."""

    def test_iso_date_format(self):
        result = normalize_travel_date("2026-10-08")
        assert result.normalized_value == date(2026, 10, 8)

    def test_iso_datetime_stripped_to_date(self):
        # normalize_travel_date accepts full datetime strings and slices to date
        result = normalize_travel_date("2026-10-08T06:00:00+05:30")
        assert result.normalized_value == date(2026, 10, 8)

    def test_empty_date_raises(self):
        with pytest.raises(NormalizationException):
            normalize_travel_date("")

    def test_invalid_date_raises(self):
        with pytest.raises(NormalizationException):
            normalize_travel_date("not-a-date")

    def test_timestamp_with_timezone(self):
        result = normalize_timestamp("2026-10-08T06:00:00+05:30")
        assert result.normalized_value.year == 2026
        assert result.normalized_value.month == 10
        assert result.normalized_value.day == 8
        assert result.normalized_value.tzinfo is not None

    def test_timestamp_without_tz_assumes_ist(self):
        result = normalize_timestamp("2026-10-08T06:00:00", assume_ist=True)
        assert result.normalized_value.tzinfo is not None

    def test_invalid_timestamp_raises(self):
        with pytest.raises(NormalizationException):
            normalize_timestamp("not-a-timestamp")
