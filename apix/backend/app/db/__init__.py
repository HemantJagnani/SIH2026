"""DB package — imports all models so Alembic can discover them."""
from app.db.models import (  # noqa: F401
    AirfareIndex,
    Airline,
    FareObservation,
    Route,
    RouteIndex,
    RouteDailyPrice,
    Source,
)
from app.db.session import Base, engine, get_db  # noqa: F401
