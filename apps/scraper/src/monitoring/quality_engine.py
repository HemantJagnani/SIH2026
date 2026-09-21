"""
Data Quality Engine — Phase 9.

Evaluates a collection run for completeness, duplicates, yield anomalies,
and fare plausibility. Produces a CollectionRunQualityReport that drives
the ACCEPT / FLAG / QUARANTINE decision.

Design rules (spec Phase 9):
- Deterministic-first: all checks are rule-based; AI is never the
  primary evaluator.
- Outliers are FLAGGED, never silently deleted.
- No hard-coded arbitrary fare thresholds (e.g. ₹1,000 min / ₹50,000 max).
- Relative outlier detection uses group median + configurable multiplier.
- Logical duplicates are flagged, not auto-deleted (may be legitimate).
- CAPTCHA, 403, and all access restrictions are never bypassed.

Spec §43, Phase 9 §1–§5.
"""

from __future__ import annotations

import hashlib
import logging
import statistics
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from models.observation import AvailabilityStatus, FareObservation
from monitoring.models import (
    AnomalySeverity,
    AnomalyType,
    CollectionRunQualityReport,
    QualityDecision,
    QualityFinding,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default configuration (override via function args or config file)
# ---------------------------------------------------------------------------

DEFAULT_OUTLIER_MULTIPLIER = 3.0       # price > N × group median → outlier
DEFAULT_MIN_GROUP_SIZE = 3             # Need at least N obs to compute median
DEFAULT_COMPLETENESS_QUARANTINE_THRESHOLD = 0.50   # < 50% complete → QUARANTINE
DEFAULT_YIELD_DROP_THRESHOLD = 0.25    # yield < 25% of historical → anomaly
DEFAULT_FIELD_POPULATION_QUARANTINE_THRESHOLD = 0.40  # < 40% fare fields → QUARANTINE


def _observation_fingerprint(obs: FareObservation) -> str:
    """
    Create a deterministic fingerprint for technical duplicate detection.
    Uses all fare-relevant fields, excluding observation_id and timestamps.
    """
    parts = "|".join([
        obs.source,
        obs.origin,
        obs.destination,
        str(obs.travel_date),
        obs.airline,
        obs.flight_number or "",
        obs.cabin.value,
        str(obs.passenger_count),
        obs.trip_type.value,
        str(obs.total_fare),
        str(obs.base_fare),
        obs.currency,
    ])
    return hashlib.sha256(parts.encode()).hexdigest()


def _logical_duplicate_key(obs: FareObservation) -> tuple:
    """
    Key for grouping logical duplicates: same flight/route/date/cabin,
    potentially different fares (which may be legitimate, so don't auto-delete).
    """
    return (
        obs.source,
        obs.origin,
        obs.destination,
        str(obs.travel_date),
        obs.airline,
        obs.flight_number or "",
        obs.cabin.value,
        str(obs.passenger_count),
        obs.trip_type.value,
    )


class DataQualityEngine:
    """
    Evaluates a collection run and produces a quality report.

    Usage:
        engine = DataQualityEngine()
        report = engine.evaluate_run(
            collection_run_id=run_id,
            source="cleartrip",
            observations=observations,
            historical_median_yield=80.0,
        )

    The engine is pure and stateless — it does not touch the database.
    """

    def __init__(
        self,
        outlier_multiplier: float = DEFAULT_OUTLIER_MULTIPLIER,
        min_group_size: int = DEFAULT_MIN_GROUP_SIZE,
        completeness_quarantine_threshold: float = DEFAULT_COMPLETENESS_QUARANTINE_THRESHOLD,
        yield_drop_threshold: float = DEFAULT_YIELD_DROP_THRESHOLD,
        field_population_quarantine_threshold: float = DEFAULT_FIELD_POPULATION_QUARANTINE_THRESHOLD,
    ):
        self.outlier_multiplier = outlier_multiplier
        self.min_group_size = min_group_size
        self.completeness_quarantine_threshold = completeness_quarantine_threshold
        self.yield_drop_threshold = yield_drop_threshold
        self.field_population_quarantine_threshold = field_population_quarantine_threshold

    # -----------------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------------

    def evaluate_run(
        self,
        collection_run_id: uuid.UUID,
        source: str,
        observations: Sequence[FareObservation],
        historical_median_yield: float | None = None,
        evaluated_at: datetime | None = None,
    ) -> CollectionRunQualityReport:
        """
        Run all quality checks on a batch of observations.

        Args:
            collection_run_id: UUID of the collection run being evaluated.
            source: Source identifier (e.g. 'cleartrip').
            observations: All FareObservation objects from this run.
            historical_median_yield: Median observation count from prior runs
                                     for the same source/route/lead-time.
                                     None means no baseline available yet.
            evaluated_at: Override timestamp (useful in tests).

        Returns:
            CollectionRunQualityReport with final decision.
        """
        now = evaluated_at or datetime.now(timezone.utc)
        findings: list[QualityFinding] = []
        obs_list = list(observations)

        # 1. Completeness checks
        findings.extend(self._check_completeness(collection_run_id, source, obs_list))

        # 2. Availability tracking
        available_count, sold_out_count = self._count_availability(obs_list)

        # 3. Duplicate detection
        findings.extend(self._check_duplicates(collection_run_id, source, obs_list))

        # 4. Fare plausibility (deterministic, no AI)
        findings.extend(self._check_fare_plausibility(collection_run_id, source, obs_list))

        # 5. Relative outlier detection (group-median based)
        findings.extend(self._check_relative_outliers(collection_run_id, source, obs_list))

        # 6. Yield anomaly detection
        yield_anomaly, yield_finding = self._check_yield_anomaly(
            collection_run_id, source, len(obs_list), historical_median_yield
        )
        if yield_finding:
            findings.append(yield_finding)

        # 7. Field population rates
        field_rates = self._compute_field_population_rates(obs_list)

        # 8. Completeness rate
        completeness_count = sum(
            1 for f in findings
            if f.anomaly_type in (
                AnomalyType.MISSING_FARE,
                AnomalyType.MISSING_AIRLINE,
                AnomalyType.MISSING_ROUTE,
                AnomalyType.MISSING_TRAVEL_DATE,
            )
        )
        missing_fare_count = sum(
            1 for f in findings if f.anomaly_type == AnomalyType.MISSING_FARE
        )
        completeness_rate = (
            1.0 - (missing_fare_count / len(obs_list)) if obs_list else 0.0
        )

        # 9. Final ACCEPT / FLAG / QUARANTINE decision
        decision, quarantine_reason = self._decide(
            findings=findings,
            completeness_rate=completeness_rate,
            field_rates=field_rates,
            yield_anomaly=yield_anomaly,
            total_obs=len(obs_list),
        )

        report = CollectionRunQualityReport(
            collection_run_id=collection_run_id,
            source=source,
            evaluated_at=now,
            total_observations=len(obs_list),
            available_count=available_count,
            sold_out_count=sold_out_count,
            missing_fare_count=missing_fare_count,
            missing_airline_count=sum(
                1 for f in findings if f.anomaly_type == AnomalyType.MISSING_AIRLINE
            ),
            technical_duplicate_count=sum(
                1 for f in findings if f.anomaly_type == AnomalyType.TECHNICAL_DUPLICATE
            ),
            logical_duplicate_count=sum(
                1 for f in findings if f.anomaly_type == AnomalyType.LOGICAL_DUPLICATE
            ),
            outlier_count=sum(
                1 for f in findings if f.anomaly_type == AnomalyType.RELATIVE_FARE_OUTLIER
            ),
            completeness_rate=completeness_rate,
            availability_rate=(
                round(available_count / len(obs_list), 4) if obs_list else 0.0
            ),
            field_population_rates=field_rates,
            historical_median_yield=historical_median_yield,
            current_yield=len(obs_list),
            yield_anomaly_detected=yield_anomaly,
            findings=findings,
            decision=decision,
            quarantine_reason=quarantine_reason,
        )

        logger.info(
            "[%s] Quality report: obs=%d decision=%s critical=%d high=%d "
            "missing_fares=%d outliers=%d duplicates=%d",
            source,
            len(obs_list),
            decision.value,
            report.critical_finding_count,
            report.high_finding_count,
            missing_fare_count,
            report.outlier_count,
            report.logical_duplicate_count,
        )

        return report

    # -----------------------------------------------------------------------
    # Internal checks
    # -----------------------------------------------------------------------

    def _check_completeness(
        self,
        run_id: uuid.UUID,
        source: str,
        observations: list[FareObservation],
    ) -> list[QualityFinding]:
        """Check required fields are present on each observation."""
        findings: list[QualityFinding] = []

        for obs in observations:
            oid = obs.observation_id

            if obs.total_fare is None and obs.availability == AvailabilityStatus.AVAILABLE:
                findings.append(QualityFinding(
                    observation_id=oid,
                    collection_run_id=run_id,
                    source=source,
                    anomaly_type=AnomalyType.MISSING_FARE,
                    severity=AnomalySeverity.HIGH,
                    field_name="total_fare",
                    message=f"total_fare is None for AVAILABLE observation {oid}",
                ))

            if not obs.airline:
                findings.append(QualityFinding(
                    observation_id=oid,
                    collection_run_id=run_id,
                    source=source,
                    anomaly_type=AnomalyType.MISSING_AIRLINE,
                    severity=AnomalySeverity.MEDIUM,
                    field_name="airline",
                    message=f"airline is missing for observation {oid}",
                ))

            if not obs.flight_number and obs.availability == AvailabilityStatus.AVAILABLE:
                findings.append(QualityFinding(
                    observation_id=oid,
                    collection_run_id=run_id,
                    source=source,
                    anomaly_type=AnomalyType.MISSING_FLIGHT_NUMBER,
                    severity=AnomalySeverity.LOW,
                    field_name="flight_number",
                    message=f"flight_number is missing for AVAILABLE observation {oid}",
                ))

        return findings

    def _count_availability(
        self, observations: list[FareObservation]
    ) -> tuple[int, int]:
        """Count AVAILABLE and SOLD_OUT observations."""
        available = sum(
            1 for o in observations if o.availability == AvailabilityStatus.AVAILABLE
        )
        sold_out = sum(
            1 for o in observations if o.availability == AvailabilityStatus.SOLD_OUT
        )
        return available, sold_out

    def _check_duplicates(
        self,
        run_id: uuid.UUID,
        source: str,
        observations: list[FareObservation],
    ) -> list[QualityFinding]:
        """
        Detect technical (exact) and logical (same flight, different fare) duplicates.

        Logical duplicates are flagged but NOT deleted — different fares for the
        same flight at the same time may be legitimate (e.g., different fare families).
        """
        findings: list[QualityFinding] = []
        seen_fingerprints: dict[str, uuid.UUID] = {}
        seen_logical_keys: dict[tuple, list[uuid.UUID]] = {}

        for obs in observations:
            oid = obs.observation_id

            # Technical duplicate
            fp = _observation_fingerprint(obs)
            if fp in seen_fingerprints:
                findings.append(QualityFinding(
                    observation_id=oid,
                    collection_run_id=run_id,
                    source=source,
                    anomaly_type=AnomalyType.TECHNICAL_DUPLICATE,
                    severity=AnomalySeverity.HIGH,
                    message=(
                        f"Observation {oid} is a technical duplicate of "
                        f"{seen_fingerprints[fp]}"
                    ),
                ))
            else:
                seen_fingerprints[fp] = oid

            # Logical duplicate grouping
            key = _logical_duplicate_key(obs)
            seen_logical_keys.setdefault(key, []).append(oid)

        # Flag groups with >1 observation as logical duplicates
        for key, oids in seen_logical_keys.items():
            if len(oids) > 1:
                for oid in oids:
                    findings.append(QualityFinding(
                        observation_id=oid,
                        collection_run_id=run_id,
                        source=source,
                        anomaly_type=AnomalyType.LOGICAL_DUPLICATE,
                        severity=AnomalySeverity.MEDIUM,
                        message=(
                            f"Observation {oid} is part of a logical duplicate group "
                            f"({len(oids)} obs for same route/flight/cabin). "
                            "May be legitimate — investigate before deleting."
                        ),
                    ))

        return findings

    def _check_fare_plausibility(
        self,
        run_id: uuid.UUID,
        source: str,
        observations: list[FareObservation],
    ) -> list[QualityFinding]:
        """
        Deterministic plausibility checks on fare values.

        Rules:
        - negative fare → CRITICAL
        - zero fare for AVAILABLE → HIGH (may be legitimate promo, so not CRITICAL)
        """
        findings: list[QualityFinding] = []

        for obs in observations:
            oid = obs.observation_id

            if obs.total_fare is not None:
                if obs.total_fare < Decimal("0"):
                    findings.append(QualityFinding(
                        observation_id=oid,
                        collection_run_id=run_id,
                        source=source,
                        anomaly_type=AnomalyType.NEGATIVE_FARE,
                        severity=AnomalySeverity.CRITICAL,
                        field_name="total_fare",
                        raw_value=str(obs.total_fare),
                        message=f"Negative total_fare ({obs.total_fare}) is invalid.",
                    ))
                elif (
                    obs.total_fare == Decimal("0")
                    and obs.availability == AvailabilityStatus.AVAILABLE
                ):
                    findings.append(QualityFinding(
                        observation_id=oid,
                        collection_run_id=run_id,
                        source=source,
                        anomaly_type=AnomalyType.ZERO_FARE,
                        severity=AnomalySeverity.HIGH,
                        field_name="total_fare",
                        raw_value="0",
                        message=(
                            "Zero total_fare for AVAILABLE observation — "
                            "flag for investigation (may be error or promo)."
                        ),
                    ))

        return findings

    def _check_relative_outliers(
        self,
        run_id: uuid.UUID,
        source: str,
        observations: list[FareObservation],
    ) -> list[QualityFinding]:
        """
        Detect relative fare outliers within groupings of comparable observations.

        Groups by: source + origin + destination + travel_date + lead_days + cabin.
        Uses group median × self.outlier_multiplier.

        No hard-coded INR thresholds. Only group-relative comparison.
        """
        findings: list[QualityFinding] = []

        # Build groups
        groups: dict[tuple, list[FareObservation]] = {}
        for obs in observations:
            if obs.total_fare is None or obs.availability != AvailabilityStatus.AVAILABLE:
                continue
            key = (
                obs.source,
                obs.origin,
                obs.destination,
                str(obs.travel_date),
                obs.lead_days,
                obs.cabin.value,
            )
            groups.setdefault(key, []).append(obs)

        for group_key, group_obs in groups.items():
            if len(group_obs) < self.min_group_size:
                # Not enough data for a reliable baseline
                continue

            fares = [float(o.total_fare) for o in group_obs]  # type: ignore[arg-type]
            group_median = statistics.median(fares)

            if group_median <= 0:
                continue  # Can't compute multiplier against zero/negative median

            threshold = group_median * self.outlier_multiplier

            for obs in group_obs:
                fare_f = float(obs.total_fare)  # type: ignore[arg-type]
                if fare_f > threshold:
                    findings.append(QualityFinding(
                        observation_id=obs.observation_id,
                        collection_run_id=run_id,
                        source=source,
                        anomaly_type=AnomalyType.RELATIVE_FARE_OUTLIER,
                        severity=AnomalySeverity.HIGH,
                        field_name="total_fare",
                        raw_value=str(obs.total_fare),
                        message=(
                            f"total_fare {obs.total_fare} exceeds "
                            f"{self.outlier_multiplier}× group median "
                            f"({group_median:.2f}) for group {group_key}."
                        ),
                        expected_value=f"<= {threshold:.2f}",
                        actual_value=str(obs.total_fare),
                    ))

        return findings

    def _check_yield_anomaly(
        self,
        run_id: uuid.UUID,
        source: str,
        current_yield: int,
        historical_median_yield: float | None,
    ) -> tuple[bool, QualityFinding | None]:
        """
        Detect sudden drops in observation yield compared to historical baseline.

        Returns (anomaly_detected, finding_or_None).
        If no historical baseline exists, returns (False, None).
        """
        if historical_median_yield is None or historical_median_yield <= 0:
            return False, None

        ratio = current_yield / historical_median_yield

        if ratio < self.yield_drop_threshold:
            severity = (
                AnomalySeverity.CRITICAL
                if ratio < 0.10  # < 10% of historical → very severe
                else AnomalySeverity.HIGH
            )
            finding = QualityFinding(
                collection_run_id=run_id,
                source=source,
                anomaly_type=AnomalyType.YIELD_ANOMALY,
                severity=severity,
                message=(
                    f"PARSER_HEALTH_WARNING: Current yield ({current_yield}) is only "
                    f"{ratio:.1%} of historical median ({historical_median_yield:.1f}). "
                    "This may indicate a parser failure or source change."
                ),
                expected_value=str(historical_median_yield),
                actual_value=str(current_yield),
            )
            return True, finding

        return False, None

    def _compute_field_population_rates(
        self, observations: list[FareObservation]
    ) -> dict[str, float]:
        """Compute the % of observations where each key field is populated."""
        if not observations:
            return {}

        n = len(observations)
        fields = [
            "total_fare", "base_fare", "taxes", "airline",
            "flight_number", "departure_time", "arrival_time",
        ]
        return {
            field: round(
                sum(1 for o in observations if getattr(o, field) is not None) / n,
                4,
            )
            for field in fields
        }

    def _decide(
        self,
        findings: list[QualityFinding],
        completeness_rate: float,
        field_rates: dict[str, float],
        yield_anomaly: bool,
        total_obs: int,
    ) -> tuple[QualityDecision, str | None]:
        """
        Determine the final ACCEPT / FLAG / QUARANTINE decision.

        Quarantine triggers (spec §10 equivalent):
        - Any CRITICAL severity finding
        - Completeness < configured threshold
        - Fare field population rate < configured threshold
        - Yield drops to < 10% of historical (extreme anomaly)
        """
        reasons: list[str] = []

        critical_findings = [f for f in findings if f.severity == AnomalySeverity.CRITICAL]
        if critical_findings:
            reasons.append(
                f"{len(critical_findings)} CRITICAL finding(s): "
                + "; ".join(f.anomaly_type.value for f in critical_findings[:3])
            )

        fare_rate = field_rates.get("total_fare", 1.0)
        if fare_rate < self.field_population_quarantine_threshold:
            reasons.append(
                f"total_fare field population ({fare_rate:.1%}) below "
                f"threshold ({self.field_population_quarantine_threshold:.0%})"
            )

        if completeness_rate < self.completeness_quarantine_threshold:
            reasons.append(
                f"Completeness rate ({completeness_rate:.1%}) below "
                f"threshold ({self.completeness_quarantine_threshold:.0%})"
            )

        if reasons:
            return QualityDecision.QUARANTINE, "; ".join(reasons)

        high_findings = [f for f in findings if f.severity == AnomalySeverity.HIGH]
        if high_findings or yield_anomaly:
            return QualityDecision.FLAG, None

        return QualityDecision.ACCEPT, None
