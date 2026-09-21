"""
Pydantic schema validator for FareObservation.

Spec §19: Pydantic is the structure/type gatekeeper.
It validates required fields, types, dates, decimals, enums, and basic
constraints. Domain logic lives in business_rules.py, not here.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from models.observation import FareObservation
from models.version import SCHEMA_VERSION
from validation.errors import ValidationError, ValidationErrorCode, ValidationResult

# Valid IATA airport code pattern
import re
_IATA_PATTERN = re.compile(r'^[A-Z]{3}$')


def validate_schema(raw_data: dict[str, Any]) -> tuple[FareObservation | None, ValidationResult]:
    """
    Attempt to construct a FareObservation from raw_data via Pydantic.

    Returns:
        (FareObservation, ValidationResult with no errors) on success.
        (None, ValidationResult with errors) on failure.

    Spec §19: Never put domain normalization rules in here.
    """
    result = ValidationResult()

    # Run Pydantic construction — it handles types, required fields, enums
    try:
        obs = FareObservation.model_validate(raw_data)
    except PydanticValidationError as e:
        for err in e.errors():
            loc = ".".join(str(l) for l in err["loc"])
            raw_val = raw_data.get(err["loc"][0]) if err["loc"] else None
            code = _map_pydantic_error_type(err["type"], pydantic_msg=err["msg"], loc=loc)
            result.add_error(
                field_name=loc,
                raw_value=raw_val,
                error_code=code,
                error_message=err["msg"],
            )
        return None, result

    # --- Additional checks that Pydantic cannot express as field validators ---

    # IATA code format
    for field in ("origin", "destination"):
        val = getattr(obs, field)
        if not _IATA_PATTERN.match(val):
            result.add_error(
                field_name=field,
                raw_value=val,
                error_code=ValidationErrorCode.INVALID_IATA_CODE,
                error_message=f"'{val}' is not a valid 3-letter IATA code.",
            )

    # Currency must be INR
    if obs.currency != "INR":
        result.add_error(
            field_name="currency",
            raw_value=obs.currency,
            error_code=ValidationErrorCode.CURRENCY_NOT_INR,
            error_message=f"Only INR is supported; got '{obs.currency}'.",
        )

    # Schema version must match the constant
    if obs.schema_version != SCHEMA_VERSION:
        result.add_error(
            field_name="schema_version",
            raw_value=obs.schema_version,
            error_code=ValidationErrorCode.INVALID_SCHEMA_VERSION,
            error_message=f"schema_version must be '{SCHEMA_VERSION}'; got '{obs.schema_version}'.",
        )

    if not result.is_valid:
        return None, result

    return obs, result


def _map_pydantic_error_type(pydantic_type: str, pydantic_msg: str = "", loc: str = "") -> ValidationErrorCode:
    """Map Pydantic error type strings to our structured error codes."""
    # location-based overrides for model_validator errors
    if "schema_version" in loc and "value_error" in pydantic_type:
        return ValidationErrorCode.INVALID_SCHEMA_VERSION
    if "travel_date" in loc and "value_error" in pydantic_type:
        return ValidationErrorCode.TRAVEL_DATE_IN_PAST

    # message-based overrides
    msg_lower = pydantic_msg.lower()
    if "schema_version" in msg_lower:
        return ValidationErrorCode.INVALID_SCHEMA_VERSION
    if "travel_date" in msg_lower or "travel date" in msg_lower:
        return ValidationErrorCode.TRAVEL_DATE_IN_PAST
    if "origin and destination" in msg_lower:
        return ValidationErrorCode.ROUTE_SAME_ORIGIN_DESTINATION

    mapping = {
        "missing": ValidationErrorCode.MISSING_REQUIRED_FIELD,
        "value_error": ValidationErrorCode.INVALID_TYPE,
        "enum": ValidationErrorCode.INVALID_ENUM_VALUE,
        "datetime_parsing": ValidationErrorCode.INVALID_DATE,
        "date_parsing": ValidationErrorCode.INVALID_DATE,
        "uuid_parsing": ValidationErrorCode.INVALID_UUID,
        "decimal_parsing": ValidationErrorCode.INVALID_DECIMAL,
        "string_too_short": ValidationErrorCode.INVALID_IATA_CODE,
        "string_too_long": ValidationErrorCode.INVALID_IATA_CODE,
        "greater_than_equal": ValidationErrorCode.NEGATIVE_PRICE,
    }
    for key, code in mapping.items():
        if key in pydantic_type:
            return code
    return ValidationErrorCode.INVALID_TYPE
