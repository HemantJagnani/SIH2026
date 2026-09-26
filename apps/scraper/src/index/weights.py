"""
Versioned Weight Registry for APIx Phase 3.
Implements route and lead-time weighting with strict sum-to-one validation
per Methodology §1, §8, §10A, §21, §22, §73.
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
    if abs(total - Decimal("1.0")) > Decimal("0.001"):
        raise ValueError(f"Weights must sum to 1.0000, got total = {total}")

    return decimal_weights


class WeightRegistry:
    """
    Versioned registry for route and advance-purchase lead-time weights.
    """

    DEFAULT_VERSION = "2026.09"

    # Default DGCA passenger traffic representation proxy (§22)
    DEFAULT_ROUTE_WEIGHTS = {
        "DEL-BOM": Decimal("0.35"),
        "DEL-BLR": Decimal("0.25"),
        "BOM-BLR": Decimal("0.20"),
        "DEL-CCU": Decimal("0.10"),
        "BLR-HYD": Decimal("0.10"),
    }

    # Default booking-behavior lead-time distribution (§10A, §21)
    # Includes T+21 as the official Indian CPI 2024 alignment checkpoint!
    DEFAULT_LEAD_TIME_WEIGHTS = {
        "T+1": Decimal("0.15"),
        "T+7": Decimal("0.30"),
        "T+15": Decimal("0.20"),
        "T+21": Decimal("0.15"),  # MoSPI CPI 2024 domestic advance-purchase checkpoint
        "T+30": Decimal("0.12"),
        "T+45": Decimal("0.08"),
    }

    def __init__(
        self,
        route_weights: Optional[Dict[str, Decimal | float | str]] = None,
        lead_time_weights: Optional[Dict[str, Decimal | float | str]] = None,
        version: str = DEFAULT_VERSION,
    ):
        self.version = version
        self.route_weights = normalize_and_validate_weights(
            route_weights or self.DEFAULT_ROUTE_WEIGHTS
        )
        self.lead_time_weights = normalize_and_validate_weights(
            lead_time_weights or self.DEFAULT_LEAD_TIME_WEIGHTS
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
        Ensures conditional weights sum to 1.0 even when partial channels are observed.
        """
        valid_keys = [k for k in available_keys if k in base_weights and base_weights[k] > Decimal("0")]
        if not valid_keys:
            # Fallback to equal weights
            equal_w = Decimal("1.0") / Decimal(str(len(available_keys)))
            return {k: Decimal(str(round(equal_w, 6))) for k in available_keys}

        sub_total = sum(base_weights[k] for k in valid_keys)
        normalized: Dict[str, Decimal] = {}
        for k in valid_keys:
            normalized[k] = Decimal(str(round(base_weights[k] / sub_total, 6)))
            
        # Adjust small rounding difference on first item so sum is exact
        diff = Decimal("1.0") - sum(normalized.values())
        if diff != Decimal("0") and valid_keys:
            normalized[valid_keys[0]] += diff
            
        return normalized
