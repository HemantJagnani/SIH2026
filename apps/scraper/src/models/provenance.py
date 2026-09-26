"""
Field Provenance and Extraction Modes.

Every important optional field must distinguish:
1. observed
2. unavailable
3. parser failure
4. not applicable
5. not yet enriched

Do NOT represent all cases merely as NULL.

Source: Phase 3, Phase 4 specs.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FieldStatus(str, Enum):
    """Status of an extracted or observed field."""
    OBSERVED = "OBSERVED"
    UNAVAILABLE = "UNAVAILABLE"
    PARSER_FAILURE = "PARSER_FAILURE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_YET_ENRICHED = "NOT_YET_ENRICHED"


class MissingReason(str, Enum):
    """Reason why an expected field is not present."""
    NOT_PRESENT_IN_DOM = "NOT_PRESENT_IN_DOM"
    NOT_PRESENT_AFTER_EXPANSION = "NOT_PRESENT_AFTER_EXPANSION"
    SOURCE_TOTAL_ONLY = "SOURCE_TOTAL_ONLY"
    REQUIRES_ENRICHMENT = "REQUIRES_ENRICHMENT"
    PARTNER_ONLY = "PARTNER_ONLY"
    PARSER_FAILURE = "PARSER_FAILURE"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"
    BLOCKED_BEFORE_EXTRACTION = "BLOCKED_BEFORE_EXTRACTION"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class ExtractionMode(str, Enum):
    """
    Scraper extraction mode.
    
    CORE_ONLY: search results only, fastest, no deep interaction.
    CORE_AND_DETAILS: selected observations get details/fare/baggage enrichment.
    FULL_AUDIT: controlled small sample, maximum permitted enrichment + evidence.
    """
    CORE_ONLY = "CORE_ONLY"
    CORE_AND_DETAILS = "CORE_AND_DETAILS"
    FULL_AUDIT = "FULL_AUDIT"


class FieldProvenance(BaseModel):
    """
    Metadata recording provenance for an individual data field.
    """
    model_config = ConfigDict(frozen=True)

    field_name: str
    status: FieldStatus
    source: Optional[str] = None
    missing_reason: Optional[MissingReason] = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            f"{self.field_name}_status": self.status.value,
            f"{self.field_name}_source": self.source,
            f"{self.field_name}_missing_reason": self.missing_reason.value if self.missing_reason else None,
        }
