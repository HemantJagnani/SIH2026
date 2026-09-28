"""
Centralized Product Definition Policy for APIx Production Pipeline.
Governance Standard: APIx_PRODUCT_DEF_v2.0_FROZEN / APIX_METHODOLOGY_V1
"""

from typing import Set, Tuple, Optional
import re

# Complete Authoritative Foreign/International Carriers
# (Foreign transit cabotage violation - domestic carriage prohibited under DGCA regulations)
INTERNATIONAL_CARRIERS: Set[str] = {
    "Kuwait Airways",
    "Emirates",
    "Etihad",
    "SriLankan",
    "Oman Air",
    "Saudia",
    "Gulf Air",
    "Qatar Airways",
    "Air Arabia",
    "Flydubai",
    "Malaysia Airlines",
    "Singapore Airlines",
    "Thai Airways",
    "Biman",
}

_NORMALIZED_INTERNATIONAL_CARRIERS: Set[str] = {
    c.upper() for c in INTERNATIONAL_CARRIERS
}

# Centralized Higher Fare Family Exclusion Keywords
# Fare families containing these terms are excluded from the baseline index
HIGHER_FARE_FAMILY_KEYWORDS: Tuple[str, ...] = (
    "FLEX",
    "UPFRONT",
    "BUSINESS",
    "PREMIUM",
    "EXCLUSIVE",
    "MAX",
    "CLASSIC",
)


def is_foreign_transit_carrier(airline: Optional[str]) -> bool:
    """
    Checks whether an airline is an international carrier without DGCA domestic cabotage rights.
    """
    if not airline:
        return False
    norm = airline.strip().upper()
    return norm in _NORMALIZED_INTERNATIONAL_CARRIERS


def is_higher_fare_family(fare_family: Optional[str]) -> bool:
    """
    Checks whether a fare family belongs to higher/bundled fare families (e.g. FlexiPlus, Business, UpFront).
    Standard/Saver unbundled economy tiers return False.
    """
    if not fare_family or fare_family in (
        "NOT_PROVIDED",
        "UNKNOWN",
        "STANDARD",
        "SAVER",
        "VALUE",
        "SPICESAVER",
    ):
        return False
    ff_upper = fare_family.upper()
    return any(k in ff_upper for k in HIGHER_FARE_FAMILY_KEYWORDS)
