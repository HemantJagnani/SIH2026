"""Application configuration via Pydantic Settings."""
from datetime import date
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_ENV: Literal["development", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://apix:apix_secret@localhost:5432/apix_db"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://apix:apix_secret@localhost:5432/apix_db"

    # API
    API_BASE_URL: str = "http://localhost:8000"
    NEXT_PUBLIC_API_BASE_URL: str = "http://localhost:8000"

    # Index configuration (all illustrative POC values)
    BASE_DATE: date = date(2026, 6, 1)
    RANDOM_SEED: int = 42

    # Illustrative POC route weights — NOT official weights
    ROUTE_WEIGHTS: dict[str, float] = Field(
        default={
            "DEL-BOM": 0.50,
            "DEL-BLR": 0.30,
            "BOM-BLR": 0.20,
        }
    )

    # Illustrative POC lead-time weights — NOT official weights
    LEAD_TIME_WEIGHTS: dict[int, float] = Field(
        default={
            1: 1 / 3,
            7: 1 / 3,
            30: 1 / 3,
        }
    )

    # Illustrative POC base prices (INR) — NOT official base prices
    BASE_PRICES: dict[str, float] = Field(
        default={
            "DEL-BOM": 9200.0,
            "DEL-BLR": 8500.0,
            "BOM-BLR": 7800.0,
        }
    )

    # Synthetic data generation
    SYNTHETIC_DAYS: int = 90


settings = Settings()
