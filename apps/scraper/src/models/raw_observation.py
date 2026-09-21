"""
RawObservation — the raw evidence record for every collection attempt.

Every collection attempt, whether successful or not, must produce a
RawObservation. This is the audit trail that ties the canonical
FareObservation back to what was actually received from the source.

Source: spec §11, §44 Phase 1.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, UUID4

from .enums import CollectionMode


class RawObservation(BaseModel):
    """
    Raw evidence record preserved for every collection attempt.

    PostgreSQL stores this structured record.
    The actual raw payload (JSON / XML / HTML / screenshot) lives in
    object storage and is referenced via raw_evidence_uri.

    Source: spec §11.
    """

    # --- Correlation ---
    collection_run_id: UUID4 = Field(
        ...,
        description="Identifier for the parent collection run (one run covers many jobs).",
    )
    request_id: UUID4 = Field(
        ...,
        description="Identifier from the FareSearchRequest that triggered this attempt.",
    )

    # --- Source ---
    source: str = Field(
        ...,
        description="Source identifier (e.g. 'indigo', 'cleartrip').",
    )

    # --- Timing ---
    collection_timestamp: datetime = Field(
        ...,
        description="UTC datetime when this collection attempt was made.",
    )
    response_time_ms: int | None = Field(
        default=None,
        ge=0,
        description="Round-trip response time in milliseconds.",
    )

    # --- Request context ---
    request_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized copy of the request parameters sent to the source. No secrets or PII.",
    )
    collection_method: CollectionMode = Field(
        ...,
        description="Collection mode actually used (API / HTTP / BROWSER).",
    )
    source_url_or_endpoint_reference: str | None = Field(
        default=None,
        description="URL or documented endpoint reference. Must not contain credentials.",
    )

    # --- HTTP response ---
    http_status: int | None = Field(
        default=None,
        ge=100,
        le=599,
        description="HTTP status code returned by the source.",
    )
    content_type: str | None = Field(
        default=None,
        description="Content-Type header of the source response.",
    )

    # --- Raw evidence ---
    raw_evidence_uri: str | None = Field(
        default=None,
        description=(
            "URI pointing to the raw payload in object storage "
            "(e.g. s3://bucket/raw/indigo/2026-09-21/<run_id>/response_001.json). "
            "Must not contain credentials."
        ),
    )

    # --- Versioning ---
    parser_version: str = Field(
        ...,
        description="Semver of the parser that processed this response.",
    )
    adapter_version: str = Field(
        ...,
        description="Semver of the adapter that produced this record.",
    )
