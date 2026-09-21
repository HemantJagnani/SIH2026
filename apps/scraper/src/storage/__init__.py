"""
Storage layer for Airfare Index.
"""

from .models import (
    AdapterVersion,
    Base,
    CollectionJob,
    CollectionRun,
    EntityMapping,
    FareObservationRecord,
    NormalizationException,
    QualityMetric,
    RawObservationRecord,
    SchemaVersion,
    Source,
    SourceHealth,
    ValidationErrorRecord,
)
from .object_store import ObjectStoreClient, S3ObjectStoreClient
from .postgres import DatabaseClient

__all__ = [
    # Core
    "DatabaseClient",
    "ObjectStoreClient",
    "S3ObjectStoreClient",
    # Models
    "Base",
    "Source",
    "CollectionRun",
    "CollectionJob",
    "RawObservationRecord",
    "FareObservationRecord",
    "EntityMapping",
    "NormalizationException",
    "ValidationErrorRecord",
    "QualityMetric",
    "SourceHealth",
    "SchemaVersion",
    "AdapterVersion",
]
