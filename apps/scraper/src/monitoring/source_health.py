"""
Source Health Tracker — Phase 9.

After each collection run, computes and persists source-level health
metrics into the `source_health` table.

Design rules:
- CAPTCHA, 403, SOLD_OUT, NO_RESULTS, parser errors and network errors
  are tracked as DISTINCT conditions, never collapsed into one bucket.
- Rates are always computed from actuals, never estimated.
- Never silently drops any status category.

Spec §43 (Airfare-specific quality checks), Phase 9.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone
from typing import Sequence

from adapters.models import CollectionResult, CollectionStatus
from monitoring.models import SourceHealthSnapshot

logger = logging.getLogger(__name__)


def compute_source_health(
    source: str,
    results: Sequence[CollectionResult],
    computed_at: datetime | None = None,
) -> SourceHealthSnapshot:
    """
    Compute a SourceHealthSnapshot from a batch of CollectionResult objects.

    This function is pure and stateless — it does not touch the database.
    Persistence is handled by the caller via DatabaseClient.

    Args:
        source: Source identifier (e.g. 'cleartrip').
        results: All CollectionResult objects from this collection run.
        computed_at: Override for the computation timestamp (useful in tests).

    Returns:
        SourceHealthSnapshot with all metrics populated.
    """
    now = computed_at or datetime.now(timezone.utc)

    if not results:
        logger.warning("[%s] compute_source_health called with empty results.", source)
        return SourceHealthSnapshot(source=source, computed_at=now)

    total_jobs = len(results)

    # --- Count each distinct outcome ---
    # Each condition is tracked separately per spec §12.
    successful_jobs = 0
    captcha_count = 0
    access_restricted_count = 0
    rate_limited_count = 0
    timeout_count = 0
    parser_error_count = 0
    normalization_error_count = 0
    validation_error_count = 0
    source_error_count = 0
    http_error_count = 0   # 4xx/5xx that aren't specifically categorized above

    total_observations = 0
    response_times_ms: list[float] = []
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None

    for result in results:
        status = result.status

        if status == CollectionStatus.SUCCESS:
            successful_jobs += 1
            total_observations += len(result.observations)
            if result.collection_timestamp:
                ts = result.collection_timestamp
                if last_success_at is None or ts > last_success_at:
                    last_success_at = ts
        else:
            if result.collection_timestamp:
                ts = result.collection_timestamp
                if last_failure_at is None or ts > last_failure_at:
                    last_failure_at = ts

        # Distinct error classification — do NOT merge these
        if status == CollectionStatus.CAPTCHA_PRESENT:
            captcha_count += 1
        elif status == CollectionStatus.ACCESS_RESTRICTED:
            access_restricted_count += 1
        elif status == CollectionStatus.RATE_LIMITED:
            rate_limited_count += 1
        elif status == CollectionStatus.TIMEOUT:
            timeout_count += 1
        elif status == CollectionStatus.PARSER_ERROR:
            parser_error_count += 1
        elif status == CollectionStatus.NORMALIZATION_ERROR:
            normalization_error_count += 1
        elif status == CollectionStatus.VALIDATION_ERROR:
            validation_error_count += 1
        elif status == CollectionStatus.SOURCE_ERROR:
            source_error_count += 1

        # HTTP errors: any non-SUCCESS result with an HTTP status in 4xx/5xx range
        if result.http_status and result.http_status >= 400:
            http_error_count += 1

        # Collect response times
        if result.response_time_ms is not None:
            response_times_ms.append(float(result.response_time_ms))

    # --- Compute rates ---
    def rate(count: int) -> float:
        return round(count / total_jobs, 4) if total_jobs > 0 else 0.0

    success_rate = rate(successful_jobs)
    failed_jobs = total_jobs - successful_jobs
    obs_yield = (
        round(total_observations / successful_jobs, 2) if successful_jobs > 0 else 0.0
    )

    avg_ms: float | None = None
    median_ms: float | None = None
    if response_times_ms:
        avg_ms = round(statistics.mean(response_times_ms), 1)
        median_ms = round(statistics.median(response_times_ms), 1)

    snapshot = SourceHealthSnapshot(
        source=source,
        computed_at=now,
        total_jobs=total_jobs,
        successful_jobs=successful_jobs,
        failed_jobs=failed_jobs,
        captcha_count=captcha_count,
        access_restricted_count=access_restricted_count,
        rate_limited_count=rate_limited_count,
        timeout_count=timeout_count,
        parser_error_count=parser_error_count,
        normalization_error_count=normalization_error_count,
        validation_error_count=validation_error_count,
        source_error_count=source_error_count,
        success_rate=success_rate,
        captcha_rate=rate(captcha_count),
        access_restricted_rate=rate(access_restricted_count),
        rate_limited_rate=rate(rate_limited_count),
        timeout_rate=rate(timeout_count),
        parser_error_rate=rate(parser_error_count),
        http_error_rate=rate(http_error_count),
        total_observations=total_observations,
        observation_yield_per_success=obs_yield,
        avg_response_time_ms=avg_ms,
        median_response_time_ms=median_ms,
        last_success_at=last_success_at,
        last_failure_at=last_failure_at,
    )

    logger.info(
        "[%s] Source health: jobs=%d success_rate=%.2f yield=%.1f "
        "captcha=%d access_restricted=%d parser_errors=%d",
        source,
        total_jobs,
        success_rate,
        obs_yield,
        captcha_count,
        access_restricted_count,
        parser_error_count,
    )

    return snapshot
