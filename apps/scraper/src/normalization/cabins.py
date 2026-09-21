"""
Cabin Class normalizer.

Uses pre-defined dictionary mapping since cabin class sets are very small.
"""

from models.enums import CabinClass
from normalization.core import NormalizationException, NormalizationResult


CABIN_MAP = {
    "economy": CabinClass.ECONOMY,
    "eco": CabinClass.ECONOMY,
    "y": CabinClass.ECONOMY,
    "premium_economy": CabinClass.PREMIUM_ECONOMY,
    "premium economy": CabinClass.PREMIUM_ECONOMY,
    "premiumeco": CabinClass.PREMIUM_ECONOMY,
    "w": CabinClass.PREMIUM_ECONOMY,
    "business": CabinClass.BUSINESS,
    "biz": CabinClass.BUSINESS,
    "j": CabinClass.BUSINESS,
    "first": CabinClass.FIRST,
    "f": CabinClass.FIRST,
}


def normalize_cabin(raw_cabin: str, field_name: str = "cabin") -> NormalizationResult[CabinClass]:
    if not raw_cabin or not raw_cabin.strip():
        raise NormalizationException(field_name, raw_cabin, "Empty cabin string")

    cleaned = raw_cabin.strip().lower()
    
    if cleaned in CABIN_MAP:
        return NormalizationResult(
            raw_value=raw_cabin,
            normalized_value=CABIN_MAP[cleaned],
            is_success=True,
            confidence=1.0,
        )

    raise NormalizationException(field_name, raw_cabin, f"Unknown cabin class variant: {cleaned}")
