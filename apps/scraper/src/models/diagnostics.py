"""
Generic Diagnostics and Protection State models.

Source: Phase 17, Phase 18 specs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProtectionState(str, Enum):
    """
    Standard protection states observed across sources.
    Source: Phase 18 spec.
    """
    NORMAL = "NORMAL"
    CHALLENGE_DETECTED = "CHALLENGE_DETECTED"
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    ACCESS_BLOCKED = "ACCESS_BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    SERVER_ERROR = "SERVER_ERROR"
    UNKNOWN = "UNKNOWN"


class SourceRunDiagnostics(BaseModel):
    """
    Machine-readable run diagnostics produced for every source execution.
    Source: Phase 17 spec.
    """
    source: str
    run_id: str
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    protection_state: ProtectionState = ProtectionState.NORMAL

    # Search execution
    searches_attempted: int = 0
    searches_succeeded: int = 0
    searches_failed: int = 0

    # DOM / Card parsing metrics
    cards_detected: int = 0
    cards_parsed: int = 0
    cards_rejected: int = 0

    # Output observations
    observations_created: int = 0

    # Field yield metrics
    prices_found: int = 0
    airlines_found: int = 0
    flight_numbers_found: int = 0

    # Enrichment metrics
    enrichment_attempted: int = 0
    enrichment_success: int = 0
    enrichment_partial: int = 0
    enrichment_failed: int = 0

    # Protection & error signals
    captcha_detected: int = 0
    blocked_detected: int = 0
    timeouts: int = 0
    parser_errors: int = 0
    selector_errors: int = 0

    # Additional diagnostic metadata
    error_details: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def save_json(self, output_path: str | Path) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
