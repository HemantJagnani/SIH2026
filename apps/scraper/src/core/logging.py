"""
Structured JSON Logging Configuration for the India Airfare Index Pipeline.

Spec Phase 11 (§36):
- Uses python-json-logger for structured logs.
- Uses contextvars to inject contextual fields (run_id, job_id, etc.).
- Relies on OpenTelemetry's instrumentation to inject trace_id and span_id.
"""

import logging
from contextvars import ContextVar
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

# Context variables for job execution tracing
# These can be set by the Airflow task / wrapper before invoking the scraper
log_context_run_id: ContextVar[str] = ContextVar("log_context_run_id", default="")
log_context_job_id: ContextVar[str] = ContextVar("log_context_job_id", default="")
log_context_source: ContextVar[str] = ContextVar("log_context_source", default="")
log_context_route: ContextVar[str] = ContextVar("log_context_route", default="")
log_context_travel_date: ContextVar[str] = ContextVar("log_context_travel_date", default="")
log_context_lead_days: ContextVar[int | str] = ContextVar("log_context_lead_days", default="")
log_context_adapter_version: ContextVar[str] = ContextVar("log_context_adapter_version", default="")


class PipelineContextFilter(logging.Filter):
    """
    Injects pipeline context variables into every log record.
    OpenTelemetry instrumentation handles `trace_id` and `span_id`.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = log_context_run_id.get()
        record.job_id = log_context_job_id.get()
        record.source = log_context_source.get()
        record.route = log_context_route.get()
        record.travel_date = log_context_travel_date.get()
        record.lead_days = log_context_lead_days.get()
        record.adapter_version = log_context_adapter_version.get()
        return True


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configures the root logger to output JSON format to standard output.
    Adds context filtering for pipeline variables.
    Should be called once at application / task startup.
    """
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.setLevel(level)
    
    log_handler = logging.StreamHandler()
    
    # Format string specifies standard fields + OpenTelemetry fields
    # (otelTraceID and otelSpanID will be populated by OTel instrumentation)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(otelTraceID)s %(otelSpanID)s %(run_id)s %(job_id)s %(source)s %(route)s %(travel_date)s %(lead_days)s %(adapter_version)s",
        rename_fields={
            "levelname": "level",
            "asctime": "timestamp"
        }
    )
    
    log_handler.setFormatter(formatter)
    
    # Add filter to inject ContextVar fields
    log_handler.addFilter(PipelineContextFilter())
    
    root_logger.addHandler(log_handler)


def set_job_context(
    run_id: str,
    job_id: str,
    source: str,
    route: str,
    travel_date: str,
    lead_days: int,
    adapter_version: str = "1.0.0"
) -> None:
    """
    Helper function to set all job context variables for the current context.
    """
    log_context_run_id.set(run_id)
    log_context_job_id.set(job_id)
    log_context_source.set(source)
    log_context_route.set(route)
    log_context_travel_date.set(travel_date)
    log_context_lead_days.set(lead_days)
    log_context_adapter_version.set(adapter_version)


def clear_job_context() -> None:
    """
    Clears current job context variables.
    """
    log_context_run_id.set("")
    log_context_job_id.set("")
    log_context_source.set("")
    log_context_route.set("")
    log_context_travel_date.set("")
    log_context_lead_days.set("")
    log_context_adapter_version.set("")
