"""
Business rule validator for FareObservation.

Spec §20: After schema validation, apply airfare-specific domain rules.

Rules implemented here:
- Route: origin exists, destination exists, origin != destination
- Date: travel_date >= collection_date; lead_days = travel_date - collection_date
- Price: total_fare >= 0
- Passenger: passenger_count >= 1
- Fare arithmetic: base_fare + taxes + fees - discount ≈ total_fare (configurable tolerance)
- Availability: SOLD_OUT != price=0

These rules run AFTER Pydantic validation succeeds. They receive a fully
constructed FareObservation (not raw dicts), so types are guaranteed.
"""

from __future__ import annotations

from decimal import Decimal

from models.enums import AvailabilityStatus
from models.observation import FareObservation
from validation.errors import ValidationErrorCode, ValidationResult

# Rounding tolerance for fare arithmetic check (spec §20)
# Source fares often have rounding, so we allow a small delta by default.
_DEFAULT_FARE_TOLERANCE = Decimal("1.00")  # INR 1.00


def validate_business_rules(
    obs: FareObservation,
    fare_tolerance: Decimal = _DEFAULT_FARE_TOLERANCE,
) -> ValidationResult:
    """
    Run all airfare business rules against a schema-valid FareObservation.

    Args:
        obs: A fully validated FareObservation (schema validation already passed).
        fare_tolerance: Allowed rounding delta for fare arithmetic check.

    Returns:
        ValidationResult — check is_valid and inspect errors.
    """
    result = ValidationResult()

    _check_route(obs, result)
    _check_dates(obs, result)
    _check_price(obs, result)
    _check_passengers(obs, result)
    _check_fare_arithmetic(obs, result, fare_tolerance)
    _check_availability(obs, result)

    return result


# ---------------------------------------------------------------------------
# Individual rule implementations
# ---------------------------------------------------------------------------

def _check_route(obs: FareObservation, result: ValidationResult) -> None:
    """Spec §20 Route: origin != destination."""
    # origin != destination is also in the Pydantic model_validator, but
    # we defensively check here as well in case validation is called standalone.
    if obs.origin == obs.destination:
        result.add_error(
            field_name="origin/destination",
            raw_value=f"{obs.origin} == {obs.destination}",
            error_code=ValidationErrorCode.ROUTE_SAME_ORIGIN_DESTINATION,
            error_message="origin and destination must be different airports.",
        )


def _check_dates(obs: FareObservation, result: ValidationResult) -> None:
    """Spec §20 Date: travel_date >= collection_date, lead_days = travel_date - collection_date."""
    collection_date = obs.collected_at.date()

    if obs.travel_date < collection_date:
        result.add_error(
            field_name="travel_date",
            raw_value=str(obs.travel_date),
            error_code=ValidationErrorCode.TRAVEL_DATE_IN_PAST,
            error_message=(
                f"travel_date ({obs.travel_date}) must be >= "
                f"collection date ({collection_date})."
            ),
        )

    expected_lead_days = (obs.travel_date - collection_date).days
    if obs.lead_days != expected_lead_days:
        result.add_error(
            field_name="lead_days",
            raw_value=str(obs.lead_days),
            error_code=ValidationErrorCode.LEAD_DAYS_MISMATCH,
            error_message=(
                f"lead_days ({obs.lead_days}) does not match "
                f"travel_date - collection_date ({expected_lead_days})."
            ),
        )


def _check_price(obs: FareObservation, result: ValidationResult) -> None:
    """Spec §20 Price: total_fare >= 0."""
    if obs.total_fare is not None and obs.total_fare < Decimal("0"):
        result.add_error(
            field_name="total_fare",
            raw_value=str(obs.total_fare),
            error_code=ValidationErrorCode.NEGATIVE_PRICE,
            error_message="total_fare must be >= 0.",
        )


def _check_passengers(obs: FareObservation, result: ValidationResult) -> None:
    """Spec §20 Passenger: passenger_count >= 1."""
    if obs.passenger_count < 1:
        result.add_error(
            field_name="passenger_count",
            raw_value=str(obs.passenger_count),
            error_code=ValidationErrorCode.ZERO_PASSENGER_COUNT,
            error_message="passenger_count must be >= 1.",
        )


def _check_fare_arithmetic(
    obs: FareObservation,
    result: ValidationResult,
    tolerance: Decimal,
) -> None:
    """
    Spec §20 Fare arithmetic: base_fare + taxes + fees - discount ≈ total_fare.
    Only runs when ALL four components AND total_fare are present.
    """
    if all(
        v is not None
        for v in (obs.base_fare, obs.taxes, obs.fees, obs.discount, obs.total_fare)
    ):
        expected = obs.base_fare + obs.taxes + obs.fees - obs.discount  # type: ignore[operator]
        delta = abs(obs.total_fare - expected)  # type: ignore[operator]
        if delta > tolerance:
            result.add_error(
                field_name="total_fare",
                raw_value=str(obs.total_fare),
                error_code=ValidationErrorCode.FARE_ARITHMETIC_MISMATCH,
                error_message=(
                    f"total_fare ({obs.total_fare}) does not match "
                    f"base_fare + taxes + fees - discount = {expected} "
                    f"(delta={delta}, tolerance={tolerance})."
                ),
            )


def _check_availability(obs: FareObservation, result: ValidationResult) -> None:
    """
    Spec §20 Availability: SOLD_OUT must never be represented as zero price.
    A SOLD_OUT fare with total_fare=0 is always a data error.
    """
    if obs.availability == AvailabilityStatus.SOLD_OUT and obs.total_fare == Decimal("0"):
        result.add_error(
            field_name="availability/total_fare",
            raw_value=f"availability={obs.availability}, total_fare={obs.total_fare}",
            error_code=ValidationErrorCode.SOLD_OUT_WITH_ZERO_PRICE,
            error_message=(
                "SOLD_OUT must not be represented as total_fare=0. "
                "Set total_fare=None for sold-out fares."
            ),
        )
