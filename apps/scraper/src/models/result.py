"""
CollectionResult — the return value from every source adapter call.

Every call to adapter.collect(request) returns a CollectionResult.
This bundles together the canonical observations, the raw evidence record,
the explicit status, and any error information.

Source: spec §9 (adapter interface), §12 (status), §44 Phase 1.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import CollectionStatus
from .observation import FareObservation
from .raw_observation import RawObservation


class CollectionResult(BaseModel):
    """
    Return value from every adapter.collect() call.

    Design rules (spec §9):
    - Every result has an explicit status. No implicit failures.
    - Do not turn failures into price=NULL. Use the status field.
    - observations may be empty on failure; raw is always present.
    - error_message is for human/diagnostic use only; not for program logic.
    """

    # --- Status ---
    status: CollectionStatus = Field(
        ...,
        description="Explicit outcome of this collection attempt. Never ambiguous.",
    )

    # --- Raw evidence ---
    raw: RawObservation = Field(
        ...,
        description=(
            "Raw evidence record for this collection attempt. "
            "Always present, even on failure, to preserve the audit trail."
        ),
    )

    # --- Canonical observations ---
    observations: list[FareObservation] = Field(
        default_factory=list,
        description=(
            "Zero or more canonical FareObservation records extracted and normalized "
            "from the source response. Empty on failure, sold-out, or no-results."
        ),
    )

    # --- Diagnostics ---
    error_message: str | None = Field(
        default=None,
        description=(
            "Human-readable error description when status is not SUCCESS. "
            "For diagnostic use only — do not use for program control flow."
        ),
    )

    @property
    def is_success(self) -> bool:
        """Convenience: True if the collection status is SUCCESS."""
        return self.status == CollectionStatus.SUCCESS

    @property
    def observation_count(self) -> int:
        """Number of canonical observations returned."""
        return len(self.observations)
