from .index_repo import get_latest_airfare_index, get_airfare_index_history
from .route_repo import (
    get_all_routes,
    get_route_by_code,
    get_route_indices_for_date,
    get_route_daily_prices_for_date,
    get_route_index_history,
)
from .obs_repo import get_observations
from .data_quality_repo import get_data_quality_stats
from .persistence_repo import (
    persist_observations,
    get_observations_as_dicts,
    upsert_route_daily_price,
    upsert_route_index,
    upsert_airfare_index,
)

__all__ = [
    "get_latest_airfare_index",
    "get_airfare_index_history",
    "get_all_routes",
    "get_route_by_code",
    "get_route_indices_for_date",
    "get_route_daily_prices_for_date",
    "get_route_index_history",
    "get_observations",
    "get_data_quality_stats",
    "persist_observations",
    "get_observations_as_dicts",
    "upsert_route_daily_price",
    "upsert_route_index",
    "upsert_airfare_index",
]
