"""
Structured error types for the validation layer.

All validation errors are structured so they can be stored in the
`validation_errors` table (spec §31) and reported in quality metrics.
"""

from __future__ import annotations

from enum import Enum


class ValidationErrorCode(str, Enum):
    # Schema / type errors
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_TYPE = "INVALID_TYPE"
    INVALID_IATA_CODE = "INVALID_IATA_CODE"
    INVALID_CURRENCY = "INVALID_CURRENCY"
    INVALID_UUID = "INVALID_UUID"
    INVALID_ENUM_VALUE = "INVALID_ENUM_VALUE"
    INVALID_DATE = "INVALID_DATE"
    INVALID_DECIMAL = "INVALID_DECIMAL"

    # Business rule errors (spec §20)
    ROUTE_SAME_ORIGIN_DESTINATION = "ROUTE_SAME_ORIGIN_DESTINATION"
    TRAVEL_DATE_IN_PAST = "TRAVEL_DATE_IN_PAST"
    LEAD_DAYS_MISMATCH = "LEAD_DAYS_MISMATCH"
    NEGATIVE_PRICE = "NEGATIVE_PRICE"
    ZERO_PASSENGER_COUNT = "ZERO_PASSENGER_COUNT"
    FARE_ARITHMETIC_MISMATCH = "FARE_ARITHMETIC_MISMATCH"
    SOLD_OUT_WITH_ZERO_PRICE = "SOLD_OUT_WITH_ZERO_PRICE"
    INVALID_SCHEMA_VERSION = "INVALID_SCHEMA_VERSION"
    MISSING_TOTAL_FARE = "MISSING_TOTAL_FARE"
    CURRENCY_NOT_INR = "CURRENCY_NOT_INR"


class ValidationError:
    """
    A single structured validation failure.
    Can be persisted to the `validation_errors` table.
    """
    __slots__ = ("field_name", "raw_value", "error_code", "error_message")

    def __init__(
        self,
        field_name: str,
        raw_value: object,
        error_code: ValidationErrorCode,
        error_message: str,
    ):
        self.field_name = field_name
        self.raw_value = str(raw_value) if raw_value is not None else None
        self.error_code = error_code
        self.error_message = error_message

    def __repr__(self) -> str:
        return (
            f"ValidationError(field={self.field_name!r}, "
            f"code={self.error_code.value}, msg={self.error_message!r})"
        )


class ValidationResult:
    """
    Aggregated result of running all validation checks against one FareObservation.
    """

    def __init__(self):
        self.errors: list[ValidationError] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(
        self,
        field_name: str,
        raw_value: object,
        error_code: ValidationErrorCode,
        error_message: str,
    ) -> None:
        self.errors.append(ValidationError(field_name, raw_value, error_code, error_message))

    def __repr__(self) -> str:
        if self.is_valid:
            return "ValidationResult(VALID)"
        return f"ValidationResult(INVALID, errors={self.errors!r})"
