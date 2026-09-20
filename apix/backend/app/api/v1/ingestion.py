"""Ingestion API endpoint — uses FastAPI BackgroundTasks (no Celery/Redis required)."""
from fastapi import APIRouter, BackgroundTasks, Body

from app.workers.background import run_pipeline_background, get_task_status, make_task_id
from app.schemas import IngestionRunRequest, IngestionRunResponse

router = APIRouter()


@router.post("/run", response_model=IngestionRunResponse)
async def run_ingestion(
    background_tasks: BackgroundTasks,
    request: IngestionRunRequest = Body(default=IngestionRunRequest()),
):
    """
    POST /api/v1/ingestion/run

    Triggers the synthetic data ingestion and index calculation pipeline.
    This demonstrates the architecture:
        mock source adapter → validation → cleaning → DB → index engine → APIx

    For the POC, the mock source generates synthetic fare data.
    In production, this would connect to real airline/OTA data sources.
    """
    task_id = make_task_id()
    background_tasks.add_task(
        run_pipeline_background,
        task_id=task_id,
        num_days=request.days,
        seed=request.seed,
    )
    return IngestionRunResponse(
        task_id=task_id,
        message=(
            "Ingestion pipeline started. "
            "This will generate synthetic fare data, clean it, "
            "and calculate the Airfare Price Index."
        ),
        status="PENDING",
    )


@router.get("/status/{task_id}")
async def get_ingestion_status(task_id: str):
    """
    GET /api/v1/ingestion/status/{task_id}

    Returns the status of a running ingestion task.
    """
    state = get_task_status(task_id)
    return {
        "task_id": task_id,
        "status": state["status"],
        "result": state["result"],
    }
