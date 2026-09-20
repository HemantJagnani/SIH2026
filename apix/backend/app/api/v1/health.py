"""Health check endpoint."""
from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas import HealthResponse
from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """GET /api/v1/health — returns service health status."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc),
    )
