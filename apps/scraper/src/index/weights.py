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
"""

from __future__ import annotations
from decimal import Decimal
from typing import Dict, Optional


def normalize_and_validate_weights(raw_weights: Dict[str, Decimal | float | str]) -> Dict[str, Decimal]:
    """
    Validates that weights sum to exactly 1.0000 (within Decimal epsilon).
    Raises ValueError if weights are negative or do not sum to 1.
    """
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
    LEAD_TIME_WEIGHT_TYPE = "PROVISIONAL EQUAL LEAD-TIME WEIGHTS"
    ROUTE_WEIGHT_TYPE = "DGCA PASSENGER TRAFFIC SHARE PROXY"

    # Phase 29 §5: Provisional equal lead-time weights (w_L = 1/6)
    # T+21 is the MoSPI domestic advance-purchase reference checkpoint
    PROVISIONAL_EQUAL_LEAD_TIME_WEIGHTS = {
        "T+1": Decimal("0.166667"),
        "T+7": Decimal("0.166667"),
        "T+15": Decimal("0.166667"),
        "T+21": Decimal("0.166667"),  # MoSPI CPI 2024 domestic advance-purchase reference
        "T+30": Decimal("0.166666"),
        "T+45": Decimal("0.166666"),
    }

    # Single-route pilot weight (DEL-BOM = 1.0000)
    SINGLE_ROUTE_WEIGHTS = {
        "DEL-BOM": Decimal("1.000000"),
    }

    # National DGCA passenger traffic representation proxy (§13)
    MULTI_ROUTE_DGCA_PROXY_WEIGHTS = {
        "DEL-BOM": Decimal("0.35"),
        "DEL-BLR": Decimal("0.25"),
        "BOM-BLR": Decimal("0.20"),
        "DEL-CCU": Decimal("0.10"),
        "BLR-HYD": Decimal("0.10"),
    }

    def __init__(
        self,
        route_weights: Optional[Dict[str, Decimal | float | str]] = None,
        lead_time_weights: Optional[Dict[str, Decimal | float | str]] = None,
        version: str = DEFAULT_VERSION,
        is_single_route_pilot: bool = True,
    ):
        self.version = version
        default_route = self.SINGLE_ROUTE_WEIGHTS if is_single_route_pilot else self.MULTI_ROUTE_DGCA_PROXY_WEIGHTS
        self.route_weights = normalize_and_validate_weights(
            route_weights or default_route
        )
        self.lead_time_weights = normalize_and_validate_weights(
            lead_time_weights or self.PROVISIONAL_EQUAL_LEAD_TIME_WEIGHTS
        )

    def get_route_weight(self, route: str) -> Decimal:
        return self.route_weights.get(route, Decimal("0.0"))

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
        """
        if not available_keys:
            return {}

        valid_keys = [k for k in available_keys if k in base_weights and base_weights[k] > Decimal("0")]
        if not valid_keys:
            equal_w = Decimal("1.0") / Decimal(str(len(available_keys)))
            res = {k: Decimal(str(round(equal_w, 6))) for k in available_keys}
            diff = Decimal("1.0") - sum(res.values())
            if diff != Decimal("0"):
                res[available_keys[0]] += diff
            return res

        sub_total = sum(base_weights[k] for k in valid_keys)
        normalized: Dict[str, Decimal] = {}
        for k in valid_keys:
            normalized[k] = Decimal(str(round(base_weights[k] / sub_total, 6)))

        # Adjust small rounding difference on first item so sum is exact 1.000000
        diff = Decimal("1.0") - sum(normalized.values())
        if diff != Decimal("0") and valid_keys:
            normalized[valid_keys[0]] += diff

        return normalized
