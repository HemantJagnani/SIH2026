"""
Tests for date normalizers.
"""
import os
import sys
from datetime import date, datetime, timezone, timedelta

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from normalization import NormalizationException, normalize_timestamp, normalize_travel_date

IST_TZ = timezone(timedelta(hours=5, minutes=30), name="IST")


def test_normalize_travel_date():
    """Test YYYY-MM-DD parsing."""
    res = normalize_travel_date("2026-09-21")
    assert res.normalized_value == date(2026, 9, 21)
    
    # Should ignore time if accidentally passed
    res2 = normalize_travel_date("2026-09-21T10:00:00")
    assert res2.normalized_value == date(2026, 9, 21)


def test_normalize_travel_date_invalid():
    """Test invalid date parsing."""
    with pytest.raises(NormalizationException):
        normalize_travel_date("09-21-2026")  # Wrong format
        
    with pytest.raises(NormalizationException):
        normalize_travel_date("")


def test_normalize_timestamp_assumes_ist():
    """Test that timestamps without tzinfo are assumed to be IST."""
    res = normalize_timestamp("2026-09-21T10:00:00")
    val = res.normalized_value
    assert val.year == 2026
    assert val.tzinfo == IST_TZ


def test_normalize_timestamp_preserves_tz():
    """Test that explicit tzinfo is preserved."""
    # +00:00 (UTC)
    res = normalize_timestamp("2026-09-21T10:00:00+00:00")
    assert res.normalized_value.tzinfo == timezone.utc
