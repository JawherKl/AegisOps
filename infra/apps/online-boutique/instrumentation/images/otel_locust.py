import atexit
import os

from locust import events
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode


resource = Resource.create(
    {
        "service.name": os.getenv("OTEL_SERVICE_NAME", "loadgenerator"),
        "service.namespace": "online-boutique",
        "deployment.environment": "testbed",
    }
)
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("aegisops.loadgenerator")
atexit.register(provider.shutdown)


def record_request(**event):
    request_type = event.get("request_type", "HTTP")
    name = event.get("name", "request")
    start_time = event.get("start_time")
    span_start_time = int(start_time * 1_000_000_000) if start_time else None

    with tracer.start_as_current_span(
        f"{request_type} {name}", start_time=span_start_time
    ) as span:
        span.set_attribute("http.request.method", str(request_type))
        span.set_attribute("url.path", str(name))
        response_time = event.get("response_time")
        if response_time is not None:
            span.set_attribute("http.client.request.duration_ms", float(response_time))
        response_length = event.get("response_length")
        if response_length is not None:
            span.set_attribute("http.response.body.size", int(response_length))

        response = event.get("response")
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            span.set_attribute("http.response.status_code", int(status_code))

        exception = event.get("exception")
        if exception is not None:
            span.record_exception(exception)
            span.set_status(Status(StatusCode.ERROR, str(exception)))
        elif status_code is not None and status_code >= 500:
            span.set_status(Status(StatusCode.ERROR))


events.request.add_listener(record_request)
