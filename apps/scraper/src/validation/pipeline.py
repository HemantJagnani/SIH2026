"""
Full validation pipeline: schema → business rules.

Combines Pydantic schema validation (§19) and airfare business rules (§20)
into a single callable that returns structured results for storage.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from models.observation import FareObservation
from validation.business_rules import validate_business_rules
from validation.errors import ValidationResult
from validation.schemas import validate_schema


def validate_observation(
    raw_data: dict[str, Any],
    fare_tolerance: Decimal = Decimal("1.00"),
) -> tuple[FareObservation | None, ValidationResult]:
    """
    Run the full two-stage validation pipeline:
        1. Pydantic schema validation (spec §19)
        2. Business rule validation (spec §20)

    Pipeline per spec:
        Normalized candidate
            ↓
        Pydantic (structure/types) ── FAIL ──> return errors
            ↓
        Business rules (domain logic) ── FAIL ──> return errors
            ↓
        Valid FareObservation

    Args:
        raw_data: Dict of fields to construct a FareObservation from.
        fare_tolerance: Rounding tolerance for fare arithmetic check.

    Returns:
        (FareObservation, ValidationResult) where ValidationResult.is_valid
        tells you whether both stages passed.
    """
    # Stage 1: Pydantic
    obs, schema_result = validate_schema(raw_data)
    if not schema_result.is_valid:
        return None, schema_result

    # Stage 2: Business rules
    biz_result = validate_business_rules(obs, fare_tolerance=fare_tolerance)
    return (obs if biz_result.is_valid else None), biz_result
