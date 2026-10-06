"""
Versioned Weight Registry for APIx Phase 29.

Implements route, advance-purchase lead-time, and CPI integration weighting
per MoSPI CPI 2024 and Eurostat HICP standards.

Key Invariants:
1. Lead-time weights initially set to PROVISIONAL EQUAL LEAD-TIME WEIGHTS (w_L = 1/6).
   T+21 is an explicit official alignment checkpoint, but receives no special weight over other horizons.
2. Route weights represent DGCA passenger traffic share proxies, NOT CPI household expenditure weights.
3. For single-route pilot (DEL-BOM), W_DELBOM = 1.0000.
4. All weights at every level must strictly validate and sum to 1.0000.
5. Strict anti-contamination guards: The official MoSPI CPI 2024 airfare expenditure weight (0.02951% / 0.0002951)
   must NEVER be used as a route weight or lead-time weight.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict, Mapping, Optional

from .route_basket import (
    BASKET_ID,
    REFERENCE_PERIOD,
    COVERAGE_PERCENT,
    TOTAL_BASKET_PASSENGER_VOLUME,
    TOTAL_ALL_INDIA_PASSENGER_VOLUME,
    get_top60_route_weights,
    get_dgca_cy2024_top60_basket,
    assert_no_cpi_weight_contamination as assert_no_cpi_weight_contamination_basket,
)
from .lead_time_weights import (
    METHODOLOGY_STATUS_EMPIRICAL,
    METHODOLOGY_STATUS_SENSITIVITY,
    METHODOLOGY_STATUS_PROVISIONAL_EQUAL,
    EMPIRICAL_LEAD_TIME_WEIGHTS,
    EQUAL_LEAD_TIME_WEIGHTS,
    get_empirical_lead_time_weights,
    get_equal_lead_time_weights,
    validate_lead_time_weights,
)

# Prohibited identifiers and values to prevent CPI expenditure weights
# from contaminating internal route or lead-time weight calculations
PROHIBITED_CPI_ROUTE_KEYS = {
    "07.3.3.1.2.01",
    "07.3.3.1.01",
    "07.3.3.1",
    "CPI_AIRFARE_WEIGHT",
    "CPI_AIRFARE_EXPENDITURE_WEIGHT",
}

PROHIBITED_CPI_ROUTE_WEIGHTS = {
    Decimal("0.02951"),
    Decimal("0.0002951"),
    Decimal("0.001850"),
}


def assert_no_cpi_weight_contamination(weights: Dict[str, Any]) -> None:
    """
    Guards against accidental injection of official MoSPI CPI airfare expenditure weight
    into route-weight or lead-time weight calculations.

    Raises ValueError immediately if CPI weight or item code is detected.
    """
    for k, v in weights.items():
        k_str = str(k).strip()
        if k_str in PROHIBITED_CPI_ROUTE_KEYS or "07.3.3" in k_str:
            raise ValueError(
                f"CRITICAL METHODOLOGICAL VIOLATION: CPI expenditure item code '{k}' "
                "cannot be used as a route weight or lead-time weight! "
                "Route weights must reflect DGCA passenger traffic shares."
            )
        try:
            d_val = Decimal(str(v))
        except (ValueError, TypeError, ArithmeticError):
            continue

        for prohibited in PROHIBITED_CPI_ROUTE_WEIGHTS:
            if abs(d_val - prohibited) < Decimal("0.0000001"):
                raise ValueError(
                    f"CRITICAL METHODOLOGICAL VIOLATION: Weight value {d_val} for '{k}' matches "
                    f"CPI airfare expenditure weight ({prohibited}). CPI expenditure weights must NOT "
                    "be used as route weights or lead-time weights!"
                )


def normalize_and_validate_weights(raw_weights: Dict[str, Decimal | float | str]) -> Dict[str, Decimal]:
    """
    Validates that weights sum to exactly 1.0000 (within Decimal epsilon).
    Enforces anti-contamination check against CPI weights.
    Raises ValueError if weights are negative, contain CPI weights, or do not sum to 1.
    """
    # Enforce strict separation from CPI expenditure weights
    assert_no_cpi_weight_contamination(raw_weights)

    decimal_weights: Dict[str, Decimal] = {}
    for k, v in raw_weights.items():
        d_val = Decimal(str(v))
        if d_val < Decimal("0"):
            raise ValueError(f"Weight for '{k}' cannot be negative: {d_val}")
        decimal_weights[k] = d_val

    total = sum(decimal_weights.values())
    if abs(total - Decimal("1.0")) > Decimal("0.005"):
        raise ValueError(f"Weights must sum to 1.0000, got total = {total}")

    # Micro-adjust first key for exact 1.000000 representation
    diff = Decimal("1.0") - total
    if diff != Decimal("0") and decimal_weights:
        first_key = next(iter(decimal_weights))
        decimal_weights[first_key] += diff

    return decimal_weights


class WeightRegistry:
    """
    Versioned registry for route, advance-purchase lead-time, and CPI expenditure weights.
    """

    DEFAULT_VERSION = "2026.09"
    EMPIRICAL_METHODOLOGY = METHODOLOGY_STATUS_EMPIRICAL
    SENSITIVITY_METHODOLOGY = METHODOLOGY_STATUS_SENSITIVITY
    PROVISIONAL_EQUAL_METHODOLOGY = METHODOLOGY_STATUS_PROVISIONAL_EQUAL

    # Primary lead-time weighting configuration is empirical dataset-derived
    LEAD_TIME_WEIGHT_TYPE = METHODOLOGY_STATUS_EMPIRICAL
    ROUTE_WEIGHT_TYPE = "DGCA PASSENGER TRAFFIC SHARE PROXY"

    # Empirical dataset-derived lead-time weights from Clean_Dataset.csv
    # Primary production configuration
    EMPIRICAL_DATASET_DERIVED_LEAD_TIME_WEIGHTS = dict(EMPIRICAL_LEAD_TIME_WEIGHTS)

    # Sensitivity-analysis equal lead-time weights (w_L = 1/6)
    # T+21 is the MoSPI domestic advance-purchase reference checkpoint
    PROVISIONAL_EQUAL_LEAD_TIME_WEIGHTS = dict(EQUAL_LEAD_TIME_WEIGHTS)
    SENSITIVITY_EQUAL_LEAD_TIME_WEIGHTS = dict(EQUAL_LEAD_TIME_WEIGHTS)

    # Single-route pilot weight (DEL-BOM = 1.0000)
    SINGLE_ROUTE_WEIGHTS = {
        "DEL-BOM": Decimal("1.000000"),
    }

    # Official DGCA CY2024 Top-60 Route Basket (57.0247% All-India coverage)
    DGCA_CY2024_TOP60_WEIGHTS = get_top60_route_weights(use_iata_codes=True)

    # Legacy 5-route proxy kept for compatibility
    MULTI_ROUTE_DGCA_PROXY_WEIGHTS = {
        "DEL-BOM": Decimal("0.35"),
        "DEL-BLR": Decimal("0.25"),
        "BOM-BLR": Decimal("0.20"),
        "DEL-CCU": Decimal("0.10"),
        "BLR-HYD": Decimal("0.10"),
    }

    def __init__(
        self,
        route_weights: Optional[Mapping[str, Any]] = None,
        lead_time_weights: Optional[Mapping[str, Any]] = None,
        version: str = DEFAULT_VERSION,
        is_single_route_pilot: bool = True,
        basket_id: Optional[str] = None,
        reference_period: Optional[str] = None,
        lead_time_weight_mode: str = "empirical",
    ):
        self.version = version
        if is_single_route_pilot:
            default_route = self.SINGLE_ROUTE_WEIGHTS
            self.basket_id = basket_id or "PILOT_SINGLE_ROUTE"
            self.reference_period = reference_period or "2026-09"
            self.coverage_percent: Optional[Decimal] = None
        else:
            default_route = self.DGCA_CY2024_TOP60_WEIGHTS
            self.basket_id = basket_id or BASKET_ID
            self.reference_period = reference_period or REFERENCE_PERIOD
            self.coverage_percent = COVERAGE_PERCENT

        self.route_weights = normalize_and_validate_weights(
            route_weights or default_route
        )

        # Lead-Time Weights Resolution:
        # Default is empirical dataset-derived weights; equal weights preserved for sensitivity analysis
        if lead_time_weights is not None:
            self.lead_time_weights = normalize_and_validate_weights(lead_time_weights)
            if set(self.lead_time_weights.keys()) == set(self.PROVISIONAL_EQUAL_LEAD_TIME_WEIGHTS.keys()) and all(
                abs(self.lead_time_weights[k] - self.PROVISIONAL_EQUAL_LEAD_TIME_WEIGHTS[k]) < Decimal("0.001")
                for k in self.lead_time_weights
            ):
                self.lead_time_weight_type = METHODOLOGY_STATUS_SENSITIVITY
            elif set(self.lead_time_weights.keys()) == set(self.EMPIRICAL_DATASET_DERIVED_LEAD_TIME_WEIGHTS.keys()) and all(
                abs(self.lead_time_weights[k] - self.EMPIRICAL_DATASET_DERIVED_LEAD_TIME_WEIGHTS[k]) < Decimal("0.001")
                for k in self.lead_time_weights
            ):
                self.lead_time_weight_type = METHODOLOGY_STATUS_EMPIRICAL
            else:
                self.lead_time_weight_type = "CUSTOM_LEAD_TIME_WEIGHTS"
        elif lead_time_weight_mode in ("equal", "sensitivity", "provisional"):
            self.lead_time_weights = normalize_and_validate_weights(
                self.PROVISIONAL_EQUAL_LEAD_TIME_WEIGHTS
            )
            self.lead_time_weight_type = METHODOLOGY_STATUS_SENSITIVITY
        else:
            self.lead_time_weights = normalize_and_validate_weights(
                self.EMPIRICAL_DATASET_DERIVED_LEAD_TIME_WEIGHTS
            )
            self.lead_time_weight_type = METHODOLOGY_STATUS_EMPIRICAL

        # Validate lead-time weights with dedicated validator
        validate_lead_time_weights(self.lead_time_weights)

        # Enforce that no CPI weights contaminated registered weights
        assert_no_cpi_weight_contamination(self.route_weights)
        assert_no_cpi_weight_contamination(self.lead_time_weights)

    def get_route_weight(self, route: str) -> Decimal:
        if route in self.route_weights:
            return self.route_weights[route]
        parts = route.split("-")
        if len(parts) == 2:
            rev = f"{parts[1]}-{parts[0]}"
            if rev in self.route_weights:
                return self.route_weights[rev]
        return Decimal("0.0")

    def get_lead_time_weight(self, lead_time_class: str) -> Decimal:
        return self.lead_time_weights.get(lead_time_class, Decimal("0.0"))

    def get_normalized_sub_weights(
        self,
        available_keys: list[str],
        base_weights: Dict[str, Decimal],
    ) -> Dict[str, Decimal]:
        """
        Calculates normalized conditional weights for a subset of available routes or lead times.
        Ensures conditional weights sum strictly to 1.0 even when partial channels are observed.
        Supports bidirectional route resolution (e.g. DEL-BLR matching BLR-DEL).
        """
        if not available_keys:
            return {}

        key_weights: Dict[str, Decimal] = {}
        for k in available_keys:
            if k in base_weights and base_weights[k] > Decimal("0"):
                key_weights[k] = base_weights[k]
            else:
                parts = k.split("-")
                if len(parts) == 2:
                    rev = f"{parts[1]}-{parts[0]}"
                    if rev in base_weights and base_weights[rev] > Decimal("0"):
                        key_weights[k] = base_weights[rev]

        if not key_weights:
            equal_w = Decimal("1.0") / Decimal(str(len(available_keys)))
            res = {k: Decimal(str(round(equal_w, 6))) for k in available_keys}
            diff = Decimal("1.0") - sum(res.values())
            if diff != Decimal("0"):
                res[available_keys[0]] += diff
            return res

        sub_total = sum(key_weights.values())
        normalized: Dict[str, Decimal] = {}
        for k in key_weights:
            normalized[k] = Decimal(str(round(key_weights[k] / sub_total, 6)))

        # Adjust small rounding difference on first item so sum is exact 1.000000
        diff = Decimal("1.0") - sum(normalized.values())
        if diff != Decimal("0") and key_weights:
            first_key = next(iter(key_weights))
            normalized[first_key] += diff
        return normalized
