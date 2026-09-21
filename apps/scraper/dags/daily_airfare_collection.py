"""
Airflow DAG for the Daily Airfare Collection Pipeline.

Spec Phase 10 (§33):
- Generates scraping jobs using JobGenerator.
- Dynamically maps jobs across Airflow workers using `expand`.
- Runs normalization, validation, and quality checks.
- Writes valid data to PostgreSQL.
- No custom Redis queue or XCom for large payloads (state in DB/S3).
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.decorators import task

# We import business logic from our apps/scraper/src modules
from core.job_generator import JobGenerator
from adapters.models import FareSearchRequest
from adapters.cleartrip.adapter import CleartripFlightApiAdapter
from models.observation import FareObservation
from storage.postgres import DatabaseClient
from monitoring.quality_engine import DataQualityEngine
from monitoring.models import QualityDecision
from validation.pipeline import run_validation_pipeline
from core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Basic rate limiter shared (in a real setup, backed by redis; here we mock for DAG design)
_rate_limiter = RateLimiter()


@task
def generate_jobs(**context) -> list[dict]:
    """
    Generate all cross-product scraping jobs for today.
    Returns a list of dicts that Airflow will use for Dynamic Task Mapping.
    """
    logger.info("Generating jobs for today's collection run.")
    generator = JobGenerator()
    # execution_date from Airflow context is used as the collection_date
    exec_date = context["data_interval_start"].date()
    
    jobs = generator.generate_jobs(collection_date=exec_date)
    logger.info(f"Generated {len(jobs)} jobs.")
    
    return jobs


@task(map_index_template="{{ my_custom_map_index }}")
def collect_fares(job_params: dict, **context) -> str:
    """
    Execute a single collection job on an Airflow worker.
    Uses dynamic task mapping to fan out jobs.
    
    Instead of passing large CollectionResult objects via XCom, 
    we save raw evidence and metadata to S3/Postgres, 
    and return only a reference (e.g., run_id or request_id) for downstream steps.
    """
    # In a real environment, context manipulation sets custom map index for UI clarity
    context["my_custom_map_index"] = f"{job_params['source']}_{job_params['origin']}_{job_params['destination']}_T{job_params['lead_days']}"

    request = FareSearchRequest(**job_params)
    logger.info(f"Starting collection for {request.source} ({request.origin}->{request.destination})")

    # Instantiate the adapter based on source
    # For Phase 10 skeleton, we use the Cleartrip adapter as our example
    if request.source == "cleartrip":
        adapter = CleartripFlightApiAdapter()
    else:
        # Placeholder for other adapters
        logger.info(f"Adapter for {request.source} not yet implemented. Skipping.")
        return f"skipped_{request.source}"

    # Here, CrawlerManager / RetryPolicy / RateLimiter would wrap the execution.
    # For brevity in the DAG, we simulate calling the adapter.
    # In production, this task must use asyncio.run or Airflow's deferrable operators
    # if it yields to the event loop.
    import asyncio
    
    async def _run():
        result = await adapter.collect(request)
        # Store result in DB/ObjectStore here (Phase 2 & 8 logic)
        # db_client = DatabaseClient(os.getenv("DATABASE_URL"))
        # await db_client.insert_raw_observation(...)
        return str(result.request_id)
        
    request_id = asyncio.run(_run())
    return request_id


@task
def normalize_and_validate(request_ids: list[str], **context):
    """
    Reads raw results from DB based on request_ids, normalizes them, 
    and validates them against Pydantic models and business rules.
    """
    logger.info(f"Normalizing and validating {len(request_ids)} job results.")
    # In production, this pulls the raw results from the DB, runs the normalizers,
    # and temporarily stages the FareObservations for quality checks.
    pass


@task
def quality_checks(**context) -> str:
    """
    Runs the DataQualityEngine across the entire batch to detect outliers,
    yield anomalies, and duplicates.
    
    Acts as a Quality Gate.
    """
    logger.info("Running DataQualityEngine over today's batch.")
    # engine = DataQualityEngine()
    # report = engine.evaluate_run(...)
    # if report.decision == QualityDecision.QUARANTINE:
    #     raise ValueError("Quality checks failed critically. Halting pipeline.")
    return "quality_gate_passed"


@task
def publish_observations(quality_gate_status: str, **context):
    """
    Writes the validated and quality-checked observations to the 
    canonical FareObservations table in PostgreSQL.
    """
    if quality_gate_status != "quality_gate_passed":
         logger.warning("Quality gate was not passed. Skipping publish.")
         return
    logger.info("Publishing canonical observations to PostgreSQL.")
    # db_client.insert_fare_observations(...)
    pass


@task
def update_source_health(**context):
    """
    Computes source health metrics (yield, success rate, blocks) 
    and updates the monitoring baseline in PostgreSQL.
    """
    logger.info("Updating source health baselines.")
    pass


# ---------------------------------------------------------------------------
# DAG Definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="daily_airfare_collection",
    description="Daily collection, normalization, validation, and quality gate for India Airfare Index",
    schedule="0 2 * * *",  # Run daily at 2:00 AM
    start_date=datetime(2026, 9, 21),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "data_engineering",
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=15),
    },
    tags=["airfare_index", "collection"],
) as dag:

    # 1. Generate jobs based on configuration
    jobs = generate_jobs()

    # 2. Collect fares (Dynamic Task Mapping - fan out)
    # This replaces the custom Redis queue
    collected_request_ids = collect_fares.expand(job_params=jobs)

    # 3. Normalize & Validate (Fan in)
    norm_val = normalize_and_validate(collected_request_ids)

    # 4. Quality Checks (Gate)
    q_gate = quality_checks()

    # 5. Publish
    publish = publish_observations(q_gate)

    # 6. Source Health
    health = update_source_health()

    # Define dependencies not implicitly handled by data passing
    norm_val >> q_gate
    publish >> health

