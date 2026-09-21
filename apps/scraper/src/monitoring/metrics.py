"""
Prometheus Metrics Configuration for the India Airfare Index.

Spec Phase 11 (§36):
- Exposes Prometheus metrics tracking job success/failure and data quality.
"""

from prometheus_client import Counter, Histogram, CollectorRegistry

# We use a custom registry so it can be cleanly exported or tested
registry = CollectorRegistry()

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

collection_success_total = Counter(
    "collection_success_total",
    "Total number of successful collection jobs",
    ["source", "route", "lead_days"],
    registry=registry,
)

collection_failure_total = Counter(
    "collection_failure_total",
    "Total number of failed collection jobs",
    ["source", "route", "lead_days", "error_type"],
    registry=registry,
)

observations_extracted_total = Counter(
    "observations_extracted_total",
    "Total number of raw observations extracted",
    ["source"],
    registry=registry,
)

observations_valid_total = Counter(
    "observations_valid_total",
    "Total number of validated, canonical observations produced",
    ["source"],
    registry=registry,
)

normalization_exception_total = Counter(
    "normalization_exception_total",
    "Total number of normalization exceptions (AI fallbacks)",
    ["source", "entity_type"],
    registry=registry,
)

validation_failure_total = Counter(
    "validation_failure_total",
    "Total number of validation errors",
    ["source", "error_code"],
    registry=registry,
)

source_restriction_total = Counter(
    "source_restriction_total",
    "Total number of times a source blocked access (CAPTCHA, 403, bot challenge)",
    ["source", "restriction_type"],
    registry=registry,
)

parser_error_total = Counter(
    "parser_error_total",
    "Total number of parser exceptions",
    ["source"],
    registry=registry,
)

# ---------------------------------------------------------------------------
# Histograms
# ---------------------------------------------------------------------------

collection_duration_seconds = Histogram(
    "collection_duration_seconds",
    "Time spent in the collection phase per job",
    ["source"],
    registry=registry,
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float("inf")),
)
