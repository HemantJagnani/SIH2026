"""
Tests for business rule validation (spec §20).

Each test maps 1:1 to a rule in the spec.
"""
import os
import sys
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from models.enums import AvailabilityStatus
from validation import ValidationErrorCode, validate_observation
from tests.validation.conftest import make_valid_payload


# ---------------------------------------------------------------------------
# Route rules
# ---------------------------------------------------------------------------

def test_valid_observation_passes_all_rules():
    payload = make_valid_payload()
    obs, result = validate_observation(payload)
    assert result.is_valid, f"Expected valid but got errors: {result.errors}"
    assert obs is not None


# ---------------------------------------------------------------------------
# Date rules
# ---------------------------------------------------------------------------

def test_travel_date_in_past_fails():
    """Spec §20: travel_date must be >= collection date."""
    payload = make_valid_payload(
        travel_date="2026-09-10",  # Before collected_at (2026-09-21)
        lead_days=0,
    )
    obs, result = validate_observation(payload)
    assert not result.is_valid
    codes = {e.error_code for e in result.errors}
    assert ValidationErrorCode.TRAVEL_DATE_IN_PAST in codes


def test_lead_days_mismatch_fails():
    """Spec §20: lead_days must equal travel_date - collection_date."""
    payload = make_valid_payload(lead_days=99)  # Should be 7
    obs, result = validate_observation(payload)
    assert not result.is_valid
    codes = {e.error_code for e in result.errors}
    assert ValidationErrorCode.LEAD_DAYS_MISMATCH in codes


def test_correct_lead_days_passes():
    payload = make_valid_payload(lead_days=7, travel_date="2026-09-28")
    obs, result = validate_observation(payload)
    assert result.is_valid


# ---------------------------------------------------------------------------
# Price rules
# ---------------------------------------------------------------------------

def test_positive_price_passes():
    payload = make_valid_payload(total_fare=Decimal("3500.00"))
    obs, result = validate_observation(payload)
    assert result.is_valid


def test_zero_price_passes():
    """Zero is allowed for promotions/free fares, just not with SOLD_OUT."""
    payload = make_valid_payload(total_fare=Decimal("0.00"))
    obs, result = validate_observation(payload)
    assert result.is_valid


# ---------------------------------------------------------------------------
# Passenger rules
# ---------------------------------------------------------------------------

def test_zero_passengers_fails_at_schema_level():
    """Pydantic ge=1 constraint fires first."""
    payload = make_valid_payload(passenger_count=0)
    obs, result = validate_observation(payload)
    assert not result.is_valid


# ---------------------------------------------------------------------------
# Fare arithmetic rules
# ---------------------------------------------------------------------------

def test_fare_arithmetic_correct_passes():
    payload = make_valid_payload(
        base_fare=Decimal("4000.00"),
        taxes=Decimal("800.00"),
        fees=Decimal("500.00"),
        discount=Decimal("60.00"),
        total_fare=Decimal("5240.00"),  # 4000 + 800 + 500 - 60 = 5240
    )
    obs, result = validate_observation(payload)
    assert result.is_valid


def test_fare_arithmetic_mismatch_fails():
    payload = make_valid_payload(
        base_fare=Decimal("4000.00"),
        taxes=Decimal("800.00"),
        fees=Decimal("500.00"),
        discount=Decimal("60.00"),
        total_fare=Decimal("9999.00"),  # Obviously wrong
    )
    obs, result = validate_observation(payload)
    assert not result.is_valid
    codes = {e.error_code for e in result.errors}
    assert ValidationErrorCode.FARE_ARITHMETIC_MISMATCH in codes


def test_fare_arithmetic_within_tolerance_passes():
    """A 0.50 rounding delta is within INR 1.00 default tolerance."""
    payload = make_valid_payload(
        base_fare=Decimal("4000.00"),
        taxes=Decimal("800.00"),
        fees=Decimal("500.00"),
        discount=Decimal("60.00"),
        total_fare=Decimal("5240.50"),  # 0.50 off, within tolerance
    )
    obs, result = validate_observation(payload)
    assert result.is_valid


def test_fare_arithmetic_skipped_when_components_missing():
    """Arithmetic check only runs when ALL components are present."""
    payload = make_valid_payload(
        base_fare=None,
        taxes=None,
        fees=None,
        discount=None,
        total_fare=Decimal("5240.00"),
    )
    obs, result = validate_observation(payload)
    assert result.is_valid


# ---------------------------------------------------------------------------
# Availability rules
# ---------------------------------------------------------------------------

def test_sold_out_with_zero_price_fails():
    """Spec §20: SOLD_OUT must not be represented as total_fare=0."""
    payload = make_valid_payload(
        availability=AvailabilityStatus.SOLD_OUT,
        total_fare=Decimal("0.00"),
    )
    obs, result = validate_observation(payload)
    assert not result.is_valid
    codes = {e.error_code for e in result.errors}
    assert ValidationErrorCode.SOLD_OUT_WITH_ZERO_PRICE in codes


def test_sold_out_with_none_price_passes():
    """Correct: SOLD_OUT with total_fare=None is valid."""
    payload = make_valid_payload(
        availability=AvailabilityStatus.SOLD_OUT,
        total_fare=None,
    )
    obs, result = validate_observation(payload)
    assert result.is_valid
