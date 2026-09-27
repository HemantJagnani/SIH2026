"""
APIx Statistical Index Compilation Package (Phase 29: MoSPI CPI 2024 + Eurostat HICP Aligned).
"""

from .models import (
    MonthlyProductPrice,
    MatchedProduct,
    ElementaryIndexResult,
    LeadTimeIndexResult,
    RouteIndexResult,
    APIxSeriesResult,
)
from .monthly_pricing import compute_monthly_product_prices
from .matching import ProductMatchingEngine
from .jevons import JevonsEngine
from .weights import WeightRegistry, normalize_and_validate_weights
from .aggregation import IndexAggregationEngine
from .engine import APIxEngine
from .classification import COICOPClassification, CPIIntegrationLayer
from .product_definition import (
    FareOffer,
    PriceBreakdown,
    QualityCharacteristics,
    ProductSelectionEngine,
    ItinerarySelectionResult,
    PRODUCT_DEFINITION_VERSION,
    SELECTION_RULE,
)
from .quality_adjustment import (
    QualityAdjustmentEngine,
    ReplacementAuditRecord,
    QualityAdjustmentRecord,
    ObservationStatus,
    ReplacementTreatment,
)

__all__ = [
    "MonthlyProductPrice",
    "MatchedProduct",
    "ElementaryIndexResult",
    "LeadTimeIndexResult",
    "RouteIndexResult",
    "APIxSeriesResult",
    "compute_monthly_product_prices",
    "ProductMatchingEngine",
    "JevonsEngine",
    "WeightRegistry",
    "normalize_and_validate_weights",
    "IndexAggregationEngine",
    "APIxEngine",
    "COICOPClassification",
    "CPIIntegrationLayer",
    "FareOffer",
    "PriceBreakdown",
    "QualityCharacteristics",
    "ProductSelectionEngine",
    "ItinerarySelectionResult",
    "PRODUCT_DEFINITION_VERSION",
    "SELECTION_RULE",
    "QualityAdjustmentEngine",
    "ReplacementAuditRecord",
    "QualityAdjustmentRecord",
    "ObservationStatus",
    "ReplacementTreatment",
]
