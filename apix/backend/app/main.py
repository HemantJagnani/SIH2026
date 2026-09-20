"""
Airfare Price Index (APIx) — FastAPI Application Entry Point.

DISCLAIMER: This is an experimental POC using synthetic data.
Not an official CPI index. Illustrative methodology only.
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine
from app.db import models  # noqa: F401 — ensure models are registered

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    configure_logging()
    logger.info(
        "apix_startup",
        env=settings.APP_ENV,
        log_level=settings.LOG_LEVEL,
    )
    yield
    logger.info("apix_shutdown")


app = FastAPI(
    title="India Airfare Price Index — APIx",
    description=(
        "Experimental POC API for the Real-time Airfare Price Index.\n\n"
        "**DISCLAIMER**: This POC uses synthetic data. "
        "Weights and methodology are illustrative only. "
        "Not an official CPI index."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount versioned API router
app.include_router(api_router, prefix="/api/v1")
