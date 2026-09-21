"""
Quality models for Phase 9 monitoring.

Defines the data structures used internally by the quality engine,
source health tracker, and AI verifier. These are Pydantic models
for in-memory use; database persistence uses the SQLAlchemy models
already defined in storage/models.py.

Spec §43, Phase 9.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Quality Assessment Enums
# ---------------------------------------------------------------------------

class AnomalyType(str, Enum):
    """Classification of detected anomalies."""
    MISSING_FARE = "MISSING_FARE"
    MISSING_AIRLINE = "MISSING_AIRLINE"
    MISSING_FLIGHT_NUMBER = "MISSING_FLIGHT_NUMBER"
    MISSING_ROUTE = "MISSING_ROUTE"
    MISSING_TRAVEL_DATE = "MISSING_TRAVEL_DATE"
    MISSING_CABIN = "MISSING_CABIN"
    MISSING_CURRENCY = "MISSING_CURRENCY"
    NEGATIVE_FARE = "NEGATIVE_FARE"
    ZERO_FARE = "ZERO_FARE"
    RELATIVE_FARE_OUTLIER = "RELATIVE_FARE_OUTLIER"
    TECHNICAL_DUPLICATE = "TECHNICAL_DUPLICATE"
    LOGICAL_DUPLICATE = "LOGICAL_DUPLICATE"
    YIELD_ANOMALY = "YIELD_ANOMALY"
    PARSER_HEALTH_WARNING = "PARSER_HEALTH_WARNING"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"


class AnomalySeverity(str, Enum):
    """Severity level of a quality anomaly."""
    CRITICAL = "CRITICAL"    # Must quarantine — index cannot use this data
    HIGH = "HIGH"            # Must flag and investigate before use
    MEDIUM = "MEDIUM"        # Flag, but index may still use with caveats
    LOW = "LOW"              # Informational; log and continue


class QualityDecision(str, Enum):
    """Final quality engine decision for a collection run."""
    ACCEPT = "ACCEPT"
    FLAG = "FLAG"
    QUARANTINE = "QUARANTINE"


class AIVerificationAssessment(str, Enum):
    """Structured assessment values from Gemini verification."""
    PLAUSIBLE = "PLAUSIBLE"
    SUPPORTED_BY_SOURCE = "SUPPORTED_BY_SOURCE"
    SUSPICIOUS = "SUSPICIOUS"
    UNRESOLVED = "UNRESOLVED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RefetchOutcome(str, Enum):
    """What happened when we tried to refetch a suspicious observation."""
    CONSISTENT = "CONSISTENT"         # Refetch confirmed original fare
    CHANGED = "CHANGED"               # Refetch returned different fare
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"  # 403, bot challenge blocked us
    CAPTCHA_BLOCKED = "CAPTCHA_BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    NO_RESULTS = "NO_RESULTS"
    ERROR = "ERROR"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"


# ---------------------------------------------------------------------------
# Quality Finding / Anomaly Record
# ---------------------------------------------------------------------------

class QualityFinding(BaseModel):
    """
    A single quality issue detected by the DataQualityEngine.

    Findings are cumulative within a run — multiple findings may exist
    for the same observation (e.g., missing fare AND logical duplicate).
    """
    model_config = ConfigDict(frozen=True)

    finding_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    observation_id: uuid.UUID | None = None        # None for run-level findings
    collection_run_id: uuid.UUID
    source: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    field_name: str | None = None                  # Which field triggered this
    raw_value: str | None = None                   # Raw value that caused the issue
    message: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    # Comparison context (for outlier / yield anomalies)
    expected_value: str | None = None
    actual_value: str | None = None


# ---------------------------------------------------------------------------
# Refetch Result
# ---------------------------------------------------------------------------

class RefetchResult(BaseModel):
    """
    Records the outcome of a controlled refetch triggered by an anomaly.

    The refetch must obey all source access conditions. CAPTCHA/403 must
    never be bypassed. Spec Phase 9 §6.
    """
    model_config = ConfigDict(frozen=True)

    observation_id: uuid.UUID
    original_total_fare: Decimal | None
    refetched_total_fare: Decimal | None = None
    outcome: RefetchOutcome
    http_status: int | None = None
    attempts: int = 1
    max_attempts: int = 1
    error_message: str | None = None
    refetched_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# AI Verification Result
# ---------------------------------------------------------------------------

class AIVerificationResult(BaseModel):
    """
    Structured output from Gemini-assisted anomaly verification.

    Gemini is ONLY invoked after deterministic checks and optional refetch
    have not resolved the anomaly. Gemini cannot modify the original fare.
    Spec Phase 9 §7, §9.
    """
    observation_id: uuid.UUID
    assessment: AIVerificationAssessment
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    evidence_references: list[str] = Field(default_factory=list)
    model_name: str
    verified_at: datetime = Field(default_factory=datetime.utcnow)

    # Context passed to Gemini for auditability
    original_fare: Decimal | None = None
    refetch_outcome: RefetchOutcome = RefetchOutcome.NOT_ATTEMPTED
    route_summary: str | None = None


# ---------------------------------------------------------------------------
# Collection Run Quality Report
# ---------------------------------------------------------------------------

class CollectionRunQualityReport(BaseModel):
    """
    Aggregated quality assessment for one complete collection run.

    This is the output of DataQualityEngine.evaluate_run(). It drives
    the final quarantine/accept decision.
    """
    collection_run_id: uuid.UUID
    source: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

    # Counts
    total_observations: int = 0
    available_count: int = 0
    sold_out_count: int = 0
    missing_fare_count: int = 0
    missing_airline_count: int = 0
    technical_duplicate_count: int = 0
    logical_duplicate_count: int = 0
    outlier_count: int = 0

    # Rates (0.0–1.0)
    completeness_rate: float = 0.0      # % of obs with required fields
    availability_rate: float = 0.0      # % AVAILABLE
    field_population_rates: dict[str, float] = Field(default_factory=dict)

    # Yield anomaly
    historical_median_yield: float | None = None
    current_yield: int = 0
    yield_anomaly_detected: bool = False

    # All findings
    findings: list[QualityFinding] = Field(default_factory=list)

    # Final decision
    decision: QualityDecision = QualityDecision.ACCEPT
    quarantine_reason: str | None = None

    @property
    def critical_finding_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AnomalySeverity.CRITICAL)

    @property
    def high_finding_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AnomalySeverity.HIGH)


# ---------------------------------------------------------------------------
# Source Health Snapshot
# ---------------------------------------------------------------------------

class SourceHealthSnapshot(BaseModel):
    """
    Computed health metrics for one source after a collection run.

    Written to the source_health table via DatabaseClient.
    """
    source: str
    computed_at: datetime = Field(default_factory=datetime.utcnow)

    # Job counts (within window or per-run)
    total_jobs: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0

    # Error breakdown — these are distinct conditions (spec §12)
    captcha_count: int = 0
    access_restricted_count: int = 0
    rate_limited_count: int = 0
    timeout_count: int = 0
    parser_error_count: int = 0
    normalization_error_count: int = 0
    validation_error_count: int = 0
    source_error_count: int = 0

    # Rates (0.0–1.0), computed from above
    success_rate: float = 0.0
    captcha_rate: float = 0.0
    access_restricted_rate: float = 0.0
    rate_limited_rate: float = 0.0
    timeout_rate: float = 0.0
    parser_error_rate: float = 0.0
    http_error_rate: float = 0.0

    # Observation metrics
    total_observations: int = 0
    observation_yield_per_success: float = 0.0

    # Response timing (milliseconds)
    avg_response_time_ms: float | None = None
    median_response_time_ms: float | None = None

    # Timestamps
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
