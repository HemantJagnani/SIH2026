"""
Bridge module for APIx statistical index compilation engine.
"""

import sys
from pathlib import Path

# Add apps/scraper/src to sys.path if not present
scraper_src = Path(__file__).resolve().parent.parent.parent / "apps" / "scraper" / "src"
if str(scraper_src) not in sys.path:
    sys.path.insert(0, str(scraper_src))

from index import (
    MonthlyProductPrice,
    MatchedProduct,
    ElementaryIndexResult,
    LeadTimeIndexResult,
    RouteIndexResult,
    APIxSeriesResult,
    compute_monthly_product_prices,
    ProductMatchingEngine,
    JevonsEngine,
    WeightRegistry,
    normalize_and_validate_weights,
    IndexAggregationEngine,
    APIxEngine,
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
]
