"""
Mandatory Checkout Fee Harmonization Engine (§Roadmap Item 6).

Reconciles search card pricing with final mandatory checkout payable pricing.
Conforms to:
- Final price includes only mandatory consumer charges according to the frozen product definition.
- Never adds optional baggage/seats/meals/insurance.
- If checkout cannot be verified, does NOT invent a fee; retains available price with explicit status.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict, Optional

from .models import CheckoutVerificationStatus, HarmonizedCheckoutPrice


class CheckoutHarmonizationEngine:
    """
    Standardizes and harmonizes mandatory out-of-pocket prices payable by consumers.
    """

    PROHIBITED_OPTIONAL_KEYS = {
        "MEAL", "SEAT", "INSURANCE", "EXTRA_BAGGAGE", "PRIORITY_BOARDING", "LOUNGE"
    }

    def reconcile_checkout_price(
        self,
        search_card_price: Decimal | float | int | str,
        mandatory_checkout_fee: Optional[Decimal | float | int | str] = None,
        unconditional_discount: Optional[Decimal | float | int | str] = None,
        raw_optional_charges: Optional[Dict[str, Decimal | float | int | str]] = None,
        source: str = "google_flights",
    ) -> HarmonizedCheckoutPrice:
        """
        Reconciles mandatory checkout components.
        Never fabricates a fee if checkout was unverified.
        """
        card_p = Decimal(str(search_card_price))
        if card_p <= Decimal("0"):
            raise ValueError(f"Search card price must be > 0, got {card_p}")

        disc = Decimal(str(unconditional_discount or "0.00"))
        if disc < Decimal("0"):
            raise ValueError("Unconditional discount cannot be negative")

        # Segregate optional charges
        opt_charges: Dict[str, Decimal] = {}
        if raw_optional_charges:
            for k, v in raw_optional_charges.items():
                d_val = Decimal(str(v))
                opt_charges[k] = d_val

        # If checkout fee is NOT verified / not captured, do NOT invent one!
        if mandatory_checkout_fee is None:
            return HarmonizedCheckoutPrice(
                search_card_price=card_p,
                mandatory_checkout_fee=None,
                unconditional_discount=Decimal("0.00"),
                final_mandatory_payable_price=card_p,
                optional_charges_excluded=opt_charges,
                verification_status=CheckoutVerificationStatus.UNVERIFIED_LISTING_FARE_RETAINED,
                fee_provenance=f"SOURCE_LISTING_CARD_{source.upper()}",
                reconciliation_rationale=(
                    f"Checkout screen unverified. Retained listing price ₹{card_p:,.2f} without invented fee. "
                    "Conforms to non-fabrication rule."
                ),
            )

        fee = Decimal(str(mandatory_checkout_fee))
        if fee < Decimal("0"):
            raise ValueError("Mandatory checkout fee cannot be negative")

        final_payable = card_p + fee - disc
        if final_payable <= Decimal("0"):
            raise ValueError(f"Final mandatory payable price must be > 0, got {final_payable}")

        return HarmonizedCheckoutPrice(
            search_card_price=card_p,
            mandatory_checkout_fee=fee,
            unconditional_discount=disc,
            final_mandatory_payable_price=final_payable,
            optional_charges_excluded=opt_charges,
            verification_status=CheckoutVerificationStatus.VERIFIED_CHECKOUT,
            fee_provenance=f"VERIFIED_CHECKOUT_SCREEN_{source.upper()}",
            reconciliation_rationale=(
                f"Verified mandatory checkout fee of ₹{fee:,.2f} added (discount ₹{disc:,.2f}). "
                f"Final mandatory payable price = ₹{final_payable:,.2f}. Optional add-ons excluded."
            ),
        )
