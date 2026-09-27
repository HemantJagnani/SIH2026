"""
APIx Product Definition & Offer Selection Engine for Phase 29.

Implements:
1. Frozen Headline APIx Product Definition:
   "Lowest qualifying mandatory-payable domestic one-way adult economy airfare for a defined itinerary/product stratum."
2. Selection Rule:
   selected_offer = MIN(all qualifying fare offers per itinerary and lead-time class)
3. Statistical Invariant:
   One itinerary must contribute at most ONE headline qualifying baseline price.
   Higher fare families (e.g. Flexi, Plus, UpFront) must NOT receive additional headline statistical weight.
   All non-selected/higher offers are preserved for analytical sub-indices.
4. Price Structure Separation:
   Maintains displayed_price, mandatory_payable_price, base_fare, taxes, fees, discounts.
   Never fabricates missing price components (stores None / NULL).
5. 14 Key Quality Characteristics retained per Eurostat HICP standards.
"""

from __future__ import annotations
import hashlib
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple
from pydantic import BaseModel, Field


PRODUCT_DEFINITION_VERSION = "APIx_PRODUCT_DEF_v2.0_FROZEN"
SELECTION_RULE = "MIN_QUALIFYING_FARE_PER_ITINERARY"


class PriceBreakdown(BaseModel):
    """
    Consumer-payable price components per Phase 29 §8.
    Never fabricates missing components: store None if not explicitly exposed.
    """
    displayed_price: Decimal = Field(..., description="Face price displayed on search card")
    mandatory_payable_price: Decimal = Field(..., description="Total mandatory payable fare in INR")
    base_fare: Optional[Decimal] = Field(default=None, description="Base airline fare if exposed, else None")
    taxes: Optional[Decimal] = Field(default=None, description="Mandatory government taxes/GST if exposed, else None")
    mandatory_fees: Optional[Decimal] = Field(default=None, description="Airport development / UDF fees if exposed, else None")
    optional_fees: Optional[Decimal] = Field(default=None, description="Optional add-ons (meals, seat, extra baggage)")
    discount_amount: Optional[Decimal] = Field(default=None, description="Unconditional discount applied to consumer price")
    discount_type: Optional[str] = Field(default=None, description="e.g. PROMO_CODE, INSTANT_BANK, NONE")
    discount_conditions: Optional[str] = Field(default=None, description="Conditions for discount validity")
    currency: str = "INR"


class QualityCharacteristics(BaseModel):
    """
    The 14 airfare quality characteristics required per Phase 29 §10 and Eurostat HICP 2024.
    Must be assessed before treating price changes as pure inflation.
    """
    airline: str
    flight_number: str
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    stops: int = 0
    cabin: str = "ECONOMY"
    fare_family: str = "STANDARD"
    baggage_allowance_kg: Optional[int] = 15
    cabin_baggage_kg: Optional[int] = 7
    refundability: str = "UNKNOWN"
    changeability: str = "UNKNOWN"
    route: str = "DEL-BOM"
    travel_date: str
    lead_time_class: str


class FareOffer(BaseModel):
    """A single commercial fare offer detected on a search result card."""
    offer_id: str
    itinerary_id: str
    source: str
    characteristics: QualityCharacteristics
    price: PriceBreakdown
    is_qualifying: bool = True
    rejection_reason: Optional[str] = None


class ItinerarySelectionResult(BaseModel):
    """
    The output of product selection for a single itinerary at a specific lead time.
    Enforces: exactly 1 selected offer for the headline index, with all other offers preserved.
    """
    itinerary_id: str
    lead_time_class: str
    route: str
    product_definition_version: str = PRODUCT_DEFINITION_VERSION
    selection_rule: str = SELECTION_RULE
    selected_offer: FareOffer
    rejected_offers: List[FareOffer] = Field(default_factory=list)

    @property
    def selected_offer_id(self) -> str:
        return self.selected_offer.offer_id

    @property
    def rejected_offer_ids(self) -> List[str]:
        return [o.offer_id for o in self.rejected_offers]

    @property
    def headline_price_inr(self) -> Decimal:
        return self.selected_offer.price.mandatory_payable_price


class ProductSelectionEngine:
    """
    Selects the lowest qualifying mandatory-payable fare offer per itinerary.
    Guarantees that each itinerary contributes at most ONE headline observation.
    """

    def __init__(self, definition_version: str = PRODUCT_DEFINITION_VERSION):
        self.definition_version = definition_version
        self.selection_rule = SELECTION_RULE

    def select_headline_offers(
        self,
        offers: Sequence[FareOffer]
    ) -> Tuple[List[ItinerarySelectionResult], List[FareOffer]]:
        """
        Groups offers by (itinerary_id, lead_time_class) and selects the minimum qualifying fare.
        
        Returns:
            Tuple of:
            - List of ItinerarySelectionResult (headline selections)
            - List of all rejected/higher offers preserved for analytical purposes
        """
        # Group offers by (itinerary_id, lead_time_class)
        grouped: Dict[Tuple[str, str], List[FareOffer]] = {}
        for o in offers:
            key = (o.itinerary_id, o.characteristics.lead_time_class)
            grouped.setdefault(key, []).append(o)

        selections: List[ItinerarySelectionResult] = []
        all_rejected: List[FareOffer] = []

        for (itin_id, lt_class), offer_list in sorted(grouped.items()):
            # Filter qualifying offers
            qualifying = [o for o in offer_list if o.is_qualifying and o.price.mandatory_payable_price > Decimal("0")]
            if not qualifying:
                continue

            # Sort by mandatory payable price ascending
            # If prices are tied, choose the standard/saver fare family, else first offer_id for determinism
            def sort_key(o: FareOffer):
                fam = o.characteristics.fare_family.upper()
                priority = 0 if any(k in fam for k in ["SAVER", "VALUE", "STANDARD", "SPICESAVER"]) else 1
                return (o.price.mandatory_payable_price, priority, o.offer_id)

            sorted_offers = sorted(qualifying, key=sort_key)
            selected = sorted_offers[0]
            rejected = sorted_offers[1:] + [o for o in offer_list if not o.is_qualifying]

            # Mark rejection reasons
            for r in sorted_offers[1:]:
                r.rejection_reason = f"HIGHER_FARE_FAMILY_OF_ITINERARY (Selected {selected.characteristics.fare_family} at INR {selected.price.mandatory_payable_price})"

            all_rejected.extend(rejected)

            res = ItinerarySelectionResult(
                itinerary_id=itin_id,
                lead_time_class=lt_class,
                route=selected.characteristics.route,
                product_definition_version=self.definition_version,
                selection_rule=self.selection_rule,
                selected_offer=selected,
                rejected_offers=rejected,
            )
            selections.append(res)

        return selections, all_rejected
