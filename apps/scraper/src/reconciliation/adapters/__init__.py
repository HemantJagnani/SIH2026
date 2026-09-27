"""
Source adapters for normalizing source-specific raw records into CanonicalOffer.
"""

from .base import BaseReconciliationAdapter
from .google_flights import GoogleFlightsReconciliationAdapter
from .easemytrip import EaseMyTripReconciliationAdapter
from .ixigo import IxigoReconciliationAdapter

__all__ = [
    "BaseReconciliationAdapter",
    "GoogleFlightsReconciliationAdapter",
    "EaseMyTripReconciliationAdapter",
    "IxigoReconciliationAdapter",
]
