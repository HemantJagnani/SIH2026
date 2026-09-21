"""
Tests for Phase 11: Observability
"""

import io
import json
import logging
import os
import sys
from unittest.mock import patch

import pytest
from prometheus_client import REGISTRY

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from core.logging import setup_logging, set_job_context, clear_job_context, log_context_run_id
from monitoring.metrics import (
    collection_success_total,
    collection_failure_total,
    observations_extracted_total,
    registry
)
from core.tracing import setup_tracing, trace_span


def test_structured_logging_context_injection():
    """Verify that JSON logger injects context variables correctly."""
    
    # Create an in-memory stream to capture logs
    log_stream = io.StringIO()
    
    # Setup our logger
    root_logger = logging.getLogger()
    # Reset existing handlers for clean test
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    setup_logging(level=logging.INFO)
    
    # Swap standard output handler to our stream
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.stream = log_stream
            
    # Set context
    set_job_context(
        run_id="run-123",
        job_id="job-456",
        source="indigo",
        route="DEL-BOM",
        travel_date="2026-10-01",
        lead_days=7
    )
    
    # Log a message
    logger = logging.getLogger("test_logger")
    logger.info("Test extraction complete")
    
    # Read the log output
    log_output = log_stream.getvalue()
    log_dict = json.loads(log_output)
    
    assert log_dict["message"] == "Test extraction complete"
    assert log_dict["run_id"] == "run-123"
    assert log_dict["job_id"] == "job-456"
    assert log_dict["source"] == "indigo"
    assert log_dict["route"] == "DEL-BOM"
    assert log_dict["lead_days"] == 7
    
    # Clear context
    clear_job_context()
    assert log_context_run_id.get() == ""


def test_prometheus_metrics_counters():
    """Verify that Prometheus metrics counters increment correctly."""
    
    # Clear previous metrics for clean test state
    collection_success_total._metrics.clear()
    observations_extracted_total._metrics.clear()
    
    # Increment counters
    collection_success_total.labels(source="cleartrip", route="DEL-BOM", lead_days="7").inc()
    observations_extracted_total.labels(source="cleartrip").inc(15)
    
    # Verify values
    success_val = registry.get_sample_value(
        "collection_success_total", 
        labels={"source": "cleartrip", "route": "DEL-BOM", "lead_days": "7"}
    )
    assert success_val == 1.0
    
    obs_val = registry.get_sample_value(
        "observations_extracted_total", 
        labels={"source": "cleartrip"}
    )
    assert obs_val == 15.0


def test_opentelemetry_tracing():
    """Verify OpenTelemetry tracer creates spans without crashing."""
    # Setup tracing with console exporter
    setup_tracing("test-service")
    
    # Use context manager
    with trace_span("test_span", {"source": "yatra"}) as span:
        assert span.is_recording()
        
    # No assertion needed, just verifying it runs without error and correctly creates a span
