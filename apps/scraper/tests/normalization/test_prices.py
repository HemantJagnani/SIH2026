"""
Tests for price normalization.
"""
import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from normalization import NormalizationException, normalize_price


def test_normalize_price_valid_formats():
    """Test parsing standard price variants."""
    assert normalize_price("₹5,240").normalized_value == Decimal("5240.00")
    assert normalize_price("INR 5,240").normalized_value == Decimal("5240.00")
    assert normalize_price("5,240 INR").normalized_value == Decimal("5240.00")
    assert normalize_price("RS. 5240").normalized_value == Decimal("5240.00")
    assert normalize_price(" 5,240.50 ").normalized_value == Decimal("5240.50")
    assert normalize_price("₹ 5,240.00").normalized_value == Decimal("5240.00")


def test_normalize_price_raw_value_preserved():
    """Spec §15: Never overwrite raw string."""
    res = normalize_price("₹ 5,240")
    assert res.raw_value == "₹ 5,240"
    assert res.normalized_value == Decimal("5240.00")


def test_normalize_price_non_inr_rejected():
    """Spec: Reject non-INR explicit currencies deterministically."""
    with pytest.raises(NormalizationException) as exc:
        normalize_price("$5,240")
    assert "Non-INR" in str(exc.value)

    with pytest.raises(NormalizationException):
        normalize_price("USD 5,240")


def test_normalize_price_empty_or_invalid():
    """Test exceptions on unparseable data."""
    with pytest.raises(NormalizationException):
        normalize_price("")
        
    with pytest.raises(NormalizationException):
        normalize_price("₹")
        
    with pytest.raises(NormalizationException):
        normalize_price("-5240")  # No negative prices
