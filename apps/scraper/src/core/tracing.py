"""
OpenTelemetry Tracing Configuration for the India Airfare Index.

Spec Phase 11 (§36):
- Uses OpenTelemetry to trace collection, normalization, and validation spans.
- Configured to use a Console/No-Op exporter initially.
- Automatic injection of trace_id and span_id into logs is handled by 
  opentelemetry-instrumentation-logging (set up in main execution).
"""

import os
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.resources import Resource, SERVICE_NAME


def setup_tracing(service_name: str = "airfare-index-scraper") -> None:
    """
    Initializes the OpenTelemetry tracer provider with a Console Exporter.
    This should be called once at application/worker startup.
    """
    # Create a resource identifying this service
    resource = Resource.create({
        SERVICE_NAME: service_name
    })

    # Create the tracer provider
    provider = TracerProvider(resource=resource)

    # Use a Console Span Exporter for now (approved in Phase 11 plan)
    # A real exporter (OTLP/Jaeger/Datadog) can be swapped in via environment variables later.
    exporter = ConsoleSpanExporter()
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # Set the global default tracer provider
    trace.set_tracer_provider(provider)


def get_tracer(module_name: str):
    """
    Returns a tracer for the specified module.
    """
    return trace.get_tracer(module_name)


# Central tracer for the core pipeline
pipeline_tracer = trace.get_tracer("airfare.pipeline")


@contextmanager
def trace_span(name: str, attributes: dict[str, str | int | float | bool] | None = None):
    """
    Helper context manager to easily trace a block of code.
    
    Usage:
        with trace_span("collect_fares", {"source": "indigo"}):
            do_work()
    """
    with pipeline_tracer.start_as_current_span(name) as span:
        if attributes:
            span.set_attributes(attributes)
        yield span
