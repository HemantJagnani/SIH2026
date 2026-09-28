"""
DGCA Annual Route-Weight Update & Basket Governance Registry (§Roadmap Item 10).

Manages immutable historical baskets (CY2024) and provides formal ingestion
and transition analysis for future DGCA passenger volume releases:
    W_(r,y) = Pax_(r,y) / sum_k(Pax_(k,y))

Invariants:
- CY2024 Top-60 basket remains immutable and active.
- Future years remain PENDING_OFFICIAL_DGCA_PUBLICATION until verified DGCA publication.
- Route weights strictly sum to 1.000000.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from index.route_basket import (
    BASKET_ID as BASKET_ID_CY2024,
    REFERENCE_PERIOD as REF_PERIOD_CY2024,
    COVERAGE_PERCENT as COVERAGE_CY2024,
    TOTAL_BASKET_PASSENGER_VOLUME as PAX_BASKET_CY2024,
    TOTAL_ALL_INDIA_PASSENGER_VOLUME as PAX_NATIONAL_CY2024,
    get_top60_route_weights,
)
from .models import AnnualRouteBasket, RouteTransitionStatus, RouteWeightTransitionRecord


class DGCARouteWeightRegistry:
    """
    Versioned registry for DGCA scheduled domestic passenger volume baskets.
    """

    def __init__(self):
        self._baskets: Dict[str, AnnualRouteBasket] = {}
        self._initialize_cy2024_immutable_basket()

    def _initialize_cy2024_immutable_basket(self) -> None:
        """Initializes frozen CY2024 production basket."""
        weights = get_top60_route_weights(use_iata_codes=True)
        basket_2024 = AnnualRouteBasket(
            basket_id=BASKET_ID_CY2024,
            reference_year=REF_PERIOD_CY2024,
            status="ACTIVE_PRODUCTION",
            route_count=len(weights),
            total_basket_passengers=PAX_BASKET_CY2024,
            total_national_passengers=PAX_NATIONAL_CY2024,
            coverage_percent=COVERAGE_CY2024,
            weights=weights,
            transitions=[],
            published_date="2026-09-27",
            provenance_reference="DGCA Scheduled Domestic Passenger Traffic Annual Report (CY2024)",
        )
        self._baskets["CY2024"] = basket_2024

    def get_basket(self, year_label: str = "CY2024") -> AnnualRouteBasket:
        """Retrieves a versioned route basket."""
        if year_label not in self._baskets:
            raise KeyError(
                f"Route basket for '{year_label}' is not registered. "
                "Future annual baskets remain PENDING_OFFICIAL_DGCA_PUBLICATION."
            )
        return self._baskets[year_label]

    def register_annual_traffic_report(
        self,
        year_label: str,  # e.g., 'CY2025'
        city_pair_passenger_volumes: Dict[str, int],
        total_national_passengers: int,
        published_date: str,
        provenance_reference: str,
        activate_immediately: bool = False,
    ) -> AnnualRouteBasket:
        """
        Ingests a new annual DGCA domestic passenger volume report.
        Extracts Top-60 city-pairs, normalizes weights, and calculates basket transition churn.
        """
        if not city_pair_passenger_volumes:
            raise ValueError("Passenger volumes cannot be empty")

        # Sort routes by passenger volume descending
        sorted_pairs = sorted(
            city_pair_passenger_volumes.items(), key=lambda x: x[1], reverse=True
        )
        top60 = sorted_pairs[:60]
        basket_pax = sum(vol for _, vol in top60)

        # Calculate exact weights
        raw_weights: Dict[str, Decimal] = {}
        for r, vol in top60:
            share = Decimal(str(vol)) / Decimal(str(basket_pax))
            raw_weights[r] = Decimal(str(round(share, 6)))

        # Adjust small rounding difference on first route so sum = exactly 1.000000
        diff = Decimal("1.000000") - sum(raw_weights.values())
        if diff != Decimal("0") and raw_weights:
            first_r = next(iter(raw_weights))
            raw_weights[first_r] += diff

        coverage = (Decimal(str(basket_pax)) / Decimal(str(total_national_passengers))) * Decimal("100")

        # Calculate basket transitions against CY2024 baseline
        prev_weights = self._baskets["CY2024"].weights
        transitions: List[RouteWeightTransitionRecord] = []

        curr_routes = set(raw_weights.keys())
        prev_routes = set(prev_weights.keys())

        # Retained and new routes
        for rank, (r, _) in enumerate(top60, 1):
            w_new = raw_weights[r]
            if r in prev_routes:
                w_old = prev_weights[r]
                transitions.append(
                    RouteWeightTransitionRecord(
                        route=r,
                        new_rank=rank,
                        previous_weight=w_old,
                        new_weight=w_new,
                        delta_weight=w_new - w_old,
                        transition_status=RouteTransitionStatus.RETAINED,
                    )
                )
            else:
                transitions.append(
                    RouteWeightTransitionRecord(
                        route=r,
                        new_rank=rank,
                        previous_weight=None,
                        new_weight=w_new,
                        delta_weight=w_new,
                        transition_status=RouteTransitionStatus.NEW_ENTRANT,
                    )
                )

        # Exited routes
        for r in sorted(prev_routes - curr_routes):
            w_old = prev_weights[r]
            transitions.append(
                RouteWeightTransitionRecord(
                    route=r,
                    previous_weight=w_old,
                    new_weight=None,
                    delta_weight=-w_old,
                    transition_status=RouteTransitionStatus.EXIT,
                )
            )

        status = "ACTIVE_PRODUCTION" if activate_immediately else "PENDING_OFFICIAL_DGCA_PUBLICATION"

        new_basket = AnnualRouteBasket(
            basket_id=f"DGCA_{year_label}_TOP60",
            reference_year=year_label,
            status=status,
            route_count=len(raw_weights),
            total_basket_passengers=basket_pax,
            total_national_passengers=total_national_passengers,
            coverage_percent=Decimal(str(round(coverage, 4))),
            weights=raw_weights,
            transitions=transitions,
            published_date=published_date,
            provenance_reference=provenance_reference,
        )

        self._baskets[year_label] = new_basket
        return new_basket
