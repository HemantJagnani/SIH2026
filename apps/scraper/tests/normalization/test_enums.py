"""
Tests for enum normalizers (cabin, trip type).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from models.enums import CabinClass, TripType
from normalization import NormalizationException, normalize_cabin, normalize_trip_type


def test_normalize_cabin():
    assert normalize_cabin("economy").normalized_value == CabinClass.ECONOMY
    assert normalize_cabin("ECONOMY").normalized_value == CabinClass.ECONOMY
    assert normalize_cabin("eco").normalized_value == CabinClass.ECONOMY
    assert normalize_cabin("Y").normalized_value == CabinClass.ECONOMY
    
    assert normalize_cabin("Premium Economy").normalized_value == CabinClass.PREMIUM_ECONOMY
    assert normalize_cabin("business").normalized_value == CabinClass.BUSINESS
    assert normalize_cabin("FIRST").normalized_value == CabinClass.FIRST

def test_normalize_cabin_invalid():
    with pytest.raises(NormalizationException):
        normalize_cabin("unknown_cabin")


def test_normalize_trip_type():
    assert normalize_trip_type("One Way").normalized_value == TripType.ONE_WAY
    assert normalize_trip_type("ONEWAY").normalized_value == TripType.ONE_WAY
    assert normalize_trip_type("one-way").normalized_value == TripType.ONE_WAY
    
    assert normalize_trip_type("Round Trip").normalized_value == TripType.ROUND_TRIP
    assert normalize_trip_type("rt").normalized_value == TripType.ROUND_TRIP

def test_normalize_trip_type_invalid():
    with pytest.raises(NormalizationException):
        normalize_trip_type("multi-city")
