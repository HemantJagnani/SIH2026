"""API v1 router — aggregates all sub-routers."""
from fastapi import APIRouter

from app.api.v1 import health, index, routes, observations, data_quality, ingestion

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(index.router, prefix="/index", tags=["Index"])
api_router.include_router(routes.router, prefix="/routes", tags=["Routes"])
api_router.include_router(observations.router, prefix="/observations", tags=["Observations"])
api_router.include_router(data_quality.router, prefix="/data-quality", tags=["Data Quality"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["Ingestion"])
