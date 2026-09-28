"""
Empirical Lead-Time Weights for APIx.

Source Methodology:
- Empirical booking dataset: Clean_Dataset.csv
- Interpretation: Treat `days_left` as booking lead time, based on verified dataset
  interpretation that each row represents an individual booking.
- Six lead-time classes:
    T+1:  0.0509 ( 5.09%)
    T+7:  0.1350 (13.50%)
    T+15: 0.1491 (14.91%)
    T+21: 0.1519 (15.19%)
    T+30: 0.2588 (25.88%)
    T+45: 0.2543 (25.43%)
  Sum = 1.0000 (100.00%)

Key Invariants:
1. Methodology Status: EMPIRICAL_DATASET_DERIVED_LEAD_TIME_WEIGHTS.
2. Distinct from Official Statistics: These weights are derived from the supplied
   Clean_Dataset.csv booking dataset and are NOT official Indian national booking weights.
3. Strict Tri-Layer Separation:
   - DGCA CY2024 Top-60 Route Basket: route representativeness weights (passenger traffic)
   - Empirical Lead-Time Weights: booking lead-time profile weights (booking behavior)
   - MoSPI CPI 2024 Airfare Weight (0.02951% / 0.0002951): household expenditure weight
4. Equal lead-time weighting (w_L = 1/6) is strictly preserved as a sensitivity-analysis
   configuration (SENSITIVITY_EQUAL_LEAD_TIME_WEIGHTS).
5. Anti-contamination guards fail loudly if CPI expenditure weights or route weights are
   ever passed as lead-time weights.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

# Methodology Identifiers
METHODOLOGY_STATUS_EMPIRICAL = "EMPIRICAL_DATASET_DERIVED_LEAD_TIME_WEIGHTS"
METHODOLOGY_STATUS_SENSITIVITY = "SENSITIVITY_EQUAL_LEAD_TIME_WEIGHTS"
METHODOLOGY_STATUS_PROVISIONAL_EQUAL = "PROVISIONAL EQUAL LEAD-TIME WEIGHTS"

SOURCE_DATASET = "Clean_Dataset.csv"
SOURCE_INTERPRETATION = (
    "Treat days_left as booking lead time, based on verified dataset interpretation "
    "that each row represents an individual booking."
)
DISCLAIMER = (
    "These lead-time weights are derived from the supplied Clean_Dataset.csv booking dataset "
    "and are not official Indian national booking weights."
)

LEAD_TIME_CLASSES: List[str] = ["T+1", "T+7", "T+15", "T+21", "T+30", "T+45"]

# Verified Empirical Lead-Time Weights from Clean_Dataset.csv
# Days left -> Lead-time class mapping:
# T+1:  0.0509 (5.09%)
# T+7:  0.1350 (13.50%)
# T+15: 0.1491 (14.91%)
# T+21: 0.1519 (15.19%)
# T+30: 0.2588 (25.88%)
# T+45: 0.2543 (25.43%)
# Sum:  1.0000 (100.00%)
EMPIRICAL_LEAD_TIME_WEIGHTS: Dict[str, Decimal] = {
    "T+1": Decimal("0.0509"),
    "T+7": Decimal("0.1350"),
    "T+15": Decimal("0.1491"),
    "T+21": Decimal("0.1519"),
    "T+30": Decimal("0.2588"),
    "T+45": Decimal("0.2543"),
}

# Preserved Sensitivity-Analysis Equal Lead-Time Weights (w_L = 1/6)
EQUAL_LEAD_TIME_WEIGHTS: Dict[str, Decimal] = {
    "T+1": Decimal("0.166667"),
    "T+7": Decimal("0.166667"),
    "T+15": Decimal("0.166667"),
    "T+21": Decimal("0.166667"),
    "T+30": Decimal("0.166666"),
    "T+45": Decimal("0.166666"),
}

# Prohibited identifiers and values to prevent CPI expenditure weights
# or route weights from contaminating lead-time weights
PROHIBITED_CPI_KEYS: Set[str] = {
    "07.3.3.1.2.01",
    "07.3.3.1.01",
    "07.3.3.1",
    "CPI_AIRFARE_WEIGHT",
    "CPI_AIRFARE_EXPENDITURE_WEIGHT",
}

PROHIBITED_CPI_VALUES: Set[Decimal] = {
    Decimal("0.02951"),
    Decimal("0.0002951"),
    Decimal("0.001850"),
}


class LeadTimeWeightItem(BaseModel):
    """Individual lead-time class weight specification."""
    lead_time_class: str = Field(..., description="Lead time class, e.g. T+1, T+7")
    lead_days: int = Field(..., gt=0, description="Nominal days prior to departure")
    weight: Decimal = Field(..., gt=Decimal("0"), description="Normalized weight (sums to 1.0)")
    weight_percent: Decimal = Field(..., gt=Decimal("0"), description="Weight as percentage (e.g. 5.09%)")
    methodology: str = Field(default=METHODOLOGY_STATUS_EMPIRICAL, description="Methodology status")
    source_dataset: str = Field(default=SOURCE_DATASET, description="Source dataset name")


class LeadTimeWeightConfig(BaseModel):
    """Complete versioned configuration for APIx lead-time weighting."""
    methodology_status: str = Field(default=METHODOLOGY_STATUS_EMPIRICAL)
    source_dataset: str = Field(default=SOURCE_DATASET)
    source_interpretation: str = Field(default=SOURCE_INTERPRETATION)
    is_official_national_weights: bool = Field(default=False)
    disclaimer: str = Field(default=DISCLAIMER)
    lead_time_count: int = Field(default=6)
    weights: Dict[str, Decimal] = Field(default_factory=dict)
    items: List[LeadTimeWeightItem] = Field(default_factory=list)


def assert_no_cpi_contamination(weights: Dict[str, Any]) -> None:
    """
    Enforces that MoSPI CPI expenditure weights (0.02951% / 0.0002951)
    or CPI item codes are NEVER injected into lead-time weights.
    """
    for k, v in weights.items():
        k_str = str(k).strip()
        if k_str in PROHIBITED_CPI_KEYS or "07.3.3" in k_str:
            raise ValueError(
                f"CRITICAL METHODOLOGICAL VIOLATION: CPI expenditure item code '{k}' "
                "cannot be used as a lead-time weight! Lead-time weights must reflect booking horizons."
            )
        try:
            d_val = Decimal(str(v))
        except (ValueError, TypeError, ArithmeticError):
            continue

        for prohibited in PROHIBITED_CPI_VALUES:
            if abs(d_val - prohibited) < Decimal("0.0000001"):
                raise ValueError(
                    f"CRITICAL METHODOLOGICAL VIOLATION: Weight value {d_val} for '{k}' matches "
                    f"CPI airfare expenditure weight ({prohibited}). CPI expenditure weights must NOT "
                    "be used as lead-time weights!"
                )


def validate_lead_time_weights(weights: Dict[str, Any]) -> Dict[str, Decimal]:
    """
    Validates that:
    1. Exactly 6 lead-time classes are present (T+1, T+7, T+15, T+21, T+30, T+45).
    2. All weights are strictly positive (> 0).
    3. Weights sum to exactly 1.0000 within strict Decimal tolerance.
    4. Anti-contamination guards reject CPI expenditure weights and route keys.
    """
    if not weights:
        raise ValueError("Lead-time weights cannot be empty.")

    # Guard against CPI contamination
    assert_no_cpi_contamination(weights)

    # Check for route key confusion (e.g. DEL-BOM passed as lead-time)
    for k in weights.keys():
        if "-" in str(k) and len(str(k)) == 7 and not str(k).startswith("T+"):
            raise ValueError(
                f"CRITICAL METHODOLOGICAL VIOLATION: Route identifier '{k}' detected in lead-time weights. "
                "Route weights must not be mixed with lead-time weights."
            )

    decimal_weights: Dict[str, Decimal] = {}
    for k, v in weights.items():
        k_str = str(k).strip()
        try:
            d_val = Decimal(str(v))
        except Exception as e:
            raise ValueError(f"Invalid weight format for '{k}': {v} ({e})")
        if d_val <= Decimal("0"):
            raise ValueError(f"Lead-time weight for '{k}' must be strictly positive: {d_val}")
        decimal_weights[k_str] = d_val

    # Validate class coverage
    missing = set(LEAD_TIME_CLASSES) - set(decimal_weights.keys())
    if missing:
        raise ValueError(f"Lead-time weights missing mandatory classes: {sorted(missing)}")

    extra = set(decimal_weights.keys()) - set(LEAD_TIME_CLASSES)
    if extra:
        raise ValueError(f"Lead-time weights contain unexpected classes: {sorted(extra)}")

    total = sum(decimal_weights.values())
    if abs(total - Decimal("1.0")) > Decimal("0.0001"):
        raise ValueError(f"Lead-time weights must sum to 1.0000, got total = {total}")

    # Micro-adjust first key if rounding difference exists
    diff = Decimal("1.0") - total
    if diff != Decimal("0") and decimal_weights:
        first_key = next(iter(decimal_weights))
        decimal_weights[first_key] += diff

    return decimal_weights


def get_empirical_lead_time_weights() -> Dict[str, Decimal]:
    """Returns validated empirical lead-time weights derived from Clean_Dataset.csv."""
    return validate_lead_time_weights(dict(EMPIRICAL_LEAD_TIME_WEIGHTS))


def get_equal_lead_time_weights() -> Dict[str, Decimal]:
    """Returns validated equal lead-time weights (w_L = 1/6) for sensitivity analysis."""
    return validate_lead_time_weights(dict(EQUAL_LEAD_TIME_WEIGHTS))


def get_lead_time_weight_config(mode: str = "empirical") -> LeadTimeWeightConfig:
    """
    Returns a complete LeadTimeWeightConfig object.
    
    Args:
        mode: 'empirical' for primary empirical dataset derived weights,
              'equal' or 'sensitivity' for sensitivity analysis equal weights.
    """
    days_map = {"T+1": 1, "T+7": 7, "T+15": 15, "T+21": 21, "T+30": 30, "T+45": 45}
    if mode in ("equal", "sensitivity", "provisional"):
        weights = get_equal_lead_time_weights()
        status = METHODOLOGY_STATUS_SENSITIVITY
        source = "Hypothetical equal-weight benchmark (sensitivity stress-test only; not production)"
        interp = "Equal provisional weighting (w_L = 1/6) across 6 lead-time horizons"
        disclaimer = "Sensitivity-analysis configuration: equal lead-time weights (w_L = 1/6) used solely for robustness stress testing. Production APIx does not assign equal lead-time weights."
    else:
        weights = get_empirical_lead_time_weights()
        status = METHODOLOGY_STATUS_EMPIRICAL
        source = SOURCE_DATASET
        interp = SOURCE_INTERPRETATION
        disclaimer = DISCLAIMER

    items = []
    for cls in LEAD_TIME_CLASSES:
        w = weights[cls]
        items.append(
            LeadTimeWeightItem(
                lead_time_class=cls,
                lead_days=days_map[cls],
                weight=w,
                weight_percent=Decimal(str(round(w * Decimal("100"), 4))),
                methodology=status,
                source_dataset=source,
            )
        )

    return LeadTimeWeightConfig(
        methodology_status=status,
        source_dataset=source,
        source_interpretation=interp,
        is_official_national_weights=False,
        disclaimer=disclaimer,
        lead_time_count=len(LEAD_TIME_CLASSES),
        weights=weights,
        items=items,
    )
