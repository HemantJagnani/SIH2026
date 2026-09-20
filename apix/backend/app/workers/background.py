"""
Background task runner — no Celery/Redis required.

Runs the pipeline as a plain async function in a FastAPI BackgroundTask.
This keeps the architecture clean while eliminating external broker dependencies.
"""
from __future__ import annotations

import uuid
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Simple in-memory task state store (sufficient for POC)
_task_store: dict[str, dict] = {}


def get_task_status(task_id: str) -> dict:
    return _task_store.get(task_id, {"status": "NOT_FOUND", "result": None})


async def run_pipeline_background(
    task_id: str,
    num_days: Optional[int] = None,
    seed: Optional[int] = None,
) -> None:
    """Runs the full ingestion + index pipeline asynchronously."""
    from app.workers.tasks import _run_pipeline_async

    _task_store[task_id] = {"status": "RUNNING", "result": None}
    logger.info("background_task_started", task_id=task_id)
    try:
        result = await _run_pipeline_async(
            num_days=num_days,
            seed=seed,
            task_id=task_id,
        )
        _task_store[task_id] = {"status": "SUCCESS", "result": result}
        logger.info("background_task_succeeded", task_id=task_id)
    except Exception as exc:
        logger.exception("background_task_failed", task_id=task_id, error=str(exc))
        _task_store[task_id] = {"status": "FAILURE", "result": str(exc)}


def make_task_id() -> str:
    return str(uuid.uuid4())
