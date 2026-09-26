"""
APIx Statistical Index Compilation Package (Phase 3).
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
]
