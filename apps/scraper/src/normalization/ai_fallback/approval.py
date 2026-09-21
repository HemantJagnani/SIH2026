"""
Candidate → Approval flow for AI-resolved entity mappings.

Spec §17:
- Do not immediately mutate the master mapping.
- Store AI candidate in normalization_exceptions with status = AI_RESOLVED.
- Apply confidence policy: auto-approve above threshold, else MANUAL_REVIEW.
- Implement approval/rejection/ignore transitions.
- On approval: promote to permanent entity_mappings.
- On failure to resolve: QUARANTINED.

Spec §47 (critical): Automatic acceptance of AI normalization must not be
changed without explicit user approval. The threshold is configurable via
AI_FALLBACK_AUTO_APPROVE_THRESHOLD env var.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from enum import Enum

from normalization.ai_fallback.models import AiResolutionResponse
from normalization.core import NormalizationException
from storage.models import EntityMapping
from storage.models import NormalizationException as NormalizationExceptionRecord
from storage.postgres import DatabaseClient

logger = logging.getLogger(__name__)

# Default auto-approve threshold — read from env so it is configurable
_DEFAULT_THRESHOLD = float(os.environ.get("AI_FALLBACK_AUTO_APPROVE_THRESHOLD", "0.95"))


class ResolutionStatus(str, Enum):
    """Status values for normalization_exceptions table."""
    PENDING = "PENDING"
    AI_RESOLVED = "AI_RESOLVED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"
    IGNORED = "IGNORED"


async def handle_normalization_exception(
    exc: NormalizationException,
    source: str,
    ai_response: AiResolutionResponse | None,
    db_client: DatabaseClient,
    observation_id: uuid.UUID | None = None,
    auto_approve_threshold: float = _DEFAULT_THRESHOLD,
) -> ResolutionStatus:
    """
    Persist the normalization exception and AI candidate to the database.
    Apply the approval policy based on confidence.

    Args:
        exc: The NormalizationException from the deterministic normalizer.
        source: The source name (e.g. 'indigo').
        ai_response: The AI's structured response, or None if AI also failed.
        db_client: Async DB client.
        observation_id: UUID of the related observation, if known.
        auto_approve_threshold: Confidence >= this auto-promotes the mapping.

    Returns:
        The final ResolutionStatus assigned to this exception.
    """
    now = datetime.now(timezone.utc)

    if ai_response is None:
        # AI could not resolve — QUARANTINE
        status = ResolutionStatus.QUARANTINED
        record = NormalizationExceptionRecord(
            exception_id=uuid.uuid4(),
            observation_id=observation_id,
            source=source,
            field_name=exc.field_name,
            raw_value=exc.raw_value,
            error_message=exc.message,
            ai_attempted=True,
            ai_candidate=None,
            ai_confidence=None,
            resolution_status=status.value,
        )
        logger.warning(
            "QUARANTINED: AI could not resolve field=%s, raw_value=%r, source=%s",
            exc.field_name, exc.raw_value, source,
        )

    elif ai_response.confidence >= auto_approve_threshold and not ai_response.needs_review:
        # High-confidence, no review needed — AUTO-APPROVE and promote to entity_mappings
        status = ResolutionStatus.APPROVED
        record = NormalizationExceptionRecord(
            exception_id=uuid.uuid4(),
            observation_id=observation_id,
            source=source,
            field_name=exc.field_name,
            raw_value=exc.raw_value,
            error_message=exc.message,
            ai_attempted=True,
            ai_candidate=ai_response.candidate_value,
            ai_confidence=ai_response.confidence,
            resolution_status=status.value,
            resolved_by="AI_AUTO",
            resolved_at=now,
        )
        logger.info(
            "AUTO-APPROVED: AI resolved field=%s, raw_value=%r -> %r (confidence=%.2f)",
            exc.field_name, exc.raw_value, ai_response.candidate_value, ai_response.confidence,
        )
        # Promote to permanent entity_mappings
        await _promote_to_mapping(
            source=source,
            field_name=exc.field_name,
            raw_value=exc.raw_value,
            canonical_value=ai_response.candidate_value,
            db_client=db_client,
        )

    else:
        # Below threshold or needs_review=True — MANUAL_REVIEW
        status = ResolutionStatus.MANUAL_REVIEW
        record = NormalizationExceptionRecord(
            exception_id=uuid.uuid4(),
            observation_id=observation_id,
            source=source,
            field_name=exc.field_name,
            raw_value=exc.raw_value,
            error_message=exc.message,
            ai_attempted=True,
            ai_candidate=ai_response.candidate_value,
            ai_confidence=ai_response.confidence,
            resolution_status=status.value,
        )
        logger.info(
            "MANUAL_REVIEW: AI candidate=%r for field=%s, raw_value=%r (confidence=%.2f, needs_review=%s)",
            ai_response.candidate_value,
            exc.field_name,
            exc.raw_value,
            ai_response.confidence,
            ai_response.needs_review,
        )

    # Persist to DB (best effort — never let persistence failure crash the pipeline)
    try:
        async with db_client.session() as session:
            session.add(record)
    except Exception as e:
        logger.error("Failed to persist normalization exception record: %s", e)

    return status


async def approve_exception(
    exception_id: uuid.UUID,
    approved_by: str,
    db_client: DatabaseClient,
) -> None:
    """
    Human approves an AI candidate. Promote mapping to entity_mappings.
    """
    from sqlalchemy import select
    now = datetime.now(timezone.utc)

    async with db_client.session() as session:
        result = await session.execute(
            select(NormalizationExceptionRecord).where(
                NormalizationExceptionRecord.exception_id == exception_id
            )
        )
        rec = result.scalar_one_or_none()
        if rec is None:
            raise ValueError(f"Exception {exception_id} not found.")
        if rec.ai_candidate is None:
            raise ValueError(f"Exception {exception_id} has no AI candidate to approve.")

        rec.resolution_status = ResolutionStatus.APPROVED.value
        rec.resolved_by = approved_by
        rec.resolved_at = now

    # Promote to entity_mappings
    entity_type = _field_to_entity_type(rec.field_name)
    await _promote_to_mapping(
        source=rec.source,
        field_name=rec.field_name,
        raw_value=rec.raw_value,
        canonical_value=rec.ai_candidate,
        db_client=db_client,
        entity_type=entity_type,
    )
    logger.info(
        "APPROVED by %s: exception_id=%s, %s=%r -> %r",
        approved_by, exception_id, rec.field_name, rec.raw_value, rec.ai_candidate,
    )


async def reject_exception(
    exception_id: uuid.UUID,
    rejected_by: str,
    db_client: DatabaseClient,
) -> None:
    """Human rejects an AI candidate."""
    from sqlalchemy import select
    now = datetime.now(timezone.utc)

    async with db_client.session() as session:
        result = await session.execute(
            select(NormalizationExceptionRecord).where(
                NormalizationExceptionRecord.exception_id == exception_id
            )
        )
        rec = result.scalar_one_or_none()
        if rec is None:
            raise ValueError(f"Exception {exception_id} not found.")

        rec.resolution_status = ResolutionStatus.REJECTED.value
        rec.resolved_by = rejected_by
        rec.resolved_at = now

    logger.info("REJECTED by %s: exception_id=%s", rejected_by, exception_id)


async def list_quarantined(db_client: DatabaseClient) -> list[NormalizationExceptionRecord]:
    """Return all records in QUARANTINED status for human review."""
    from sqlalchemy import select

    async with db_client.session() as session:
        result = await session.execute(
            select(NormalizationExceptionRecord).where(
                NormalizationExceptionRecord.resolution_status == ResolutionStatus.QUARANTINED.value
            )
        )
        return list(result.scalars().all())


async def _promote_to_mapping(
    source: str,
    field_name: str,
    raw_value: str,
    canonical_value: str,
    db_client: DatabaseClient,
    entity_type: str | None = None,
) -> None:
    """Insert or update an EntityMapping record."""
    from sqlalchemy import select
    now = datetime.now(timezone.utc)
    etype = entity_type or _field_to_entity_type(field_name)

    async with db_client.session() as session:
        result = await session.execute(
            select(EntityMapping).where(
                EntityMapping.entity_type == etype,
                EntityMapping.source == source,
                EntityMapping.raw_value == raw_value.lower(),
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.canonical_value = canonical_value
            existing.approval_status = "APPROVED"
            existing.approved_at = now
        else:
            session.add(EntityMapping(
                entity_type=etype,
                source=source,
                raw_value=raw_value.lower(),
                canonical_value=canonical_value,
                confidence=1.0,
                approval_status="APPROVED",
                created_at=now,
                approved_at=now,
                version=1,
            ))


def _field_to_entity_type(field_name: str) -> str:
    """Map a field name to an entity type for mapping promotion."""
    field_lower = field_name.lower()
    if "airline" in field_lower:
        return "AIRLINE"
    if "airport" in field_lower or "origin" in field_lower or "destination" in field_lower:
        return "AIRPORT"
    return field_name.upper()
