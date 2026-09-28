"""
Data Models for Mandatory Checkout Fee Harmonization (§Roadmap Item 6).
"""

from __future__ import annotations
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class CheckoutVerificationStatus(str, Enum):
    VERIFIED_CHECKOUT = "VERIFIED_CHECKOUT"
    UNVERIFIED_LISTING_FARE_RETAINED = "UNVERIFIED_LISTING_FARE_RETAINED"
    SOURCE_API_DISCLOSED = "SOURCE_API_DISCLOSED"


class HarmonizedCheckoutPrice(BaseModel):
    """
    Standardized price breakdown distinguishing search card price from mandatory checkout add-ons.
    Ensures final price includes only mandatory consumer charges according to the frozen product definition.
    Never adds optional baggage, meals, or seat selection.
    """
    search_card_price: Decimal = Field(..., gt=Decimal("0"))
    mandatory_checkout_fee: Optional[Decimal] = None
    unconditional_discount: Decimal = Decimal("0.00")
    final_mandatory_payable_price: Decimal = Field(..., gt=Decimal("0"))
    optional_charges_excluded: Dict[str, Decimal] = Field(default_factory=dict)
    verification_status: CheckoutVerificationStatus
    fee_provenance: str
    reconciliation_rationale: str
