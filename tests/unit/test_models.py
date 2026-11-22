from datetime import datetime, timezone
from aegisops.telemetry.models import Severity, SourceType, TelemetryEvent


def test_event_id_is_deterministic():
    ts = datetime(2026, 11, 22, 12, 0, 0, tzinfo=timezone.utc)
    a = TelemetryEvent.from_parts(source=SourceType.LOKI, timestamp=ts, message="hello", service="frontend")
    b = TelemetryEvent.from_parts(source=SourceType.LOKI, timestamp=ts, message="hello", service="frontend")
    assert a.event_id == b.event_id


def test_event_id_changes_with_message():
    ts = datetime(2026, 11, 22, 12, 0, 0, tzinfo=timezone.utc)
    a = TelemetryEvent.from_parts(source=SourceType.LOKI, timestamp=ts, message="hello")
    b = TelemetryEvent.from_parts(source=SourceType.LOKI, timestamp=ts, message="world")
    assert a.event_id != b.event_id


def test_severity_defaults_to_info():
    ts = datetime(2026, 11, 22, 12, 0, 0, tzinfo=timezone.utc)
    ev = TelemetryEvent.from_parts(source=SourceType.LOKI, timestamp=ts, message="hi")
    assert ev.severity == Severity.INFO