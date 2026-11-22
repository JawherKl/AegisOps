from datetime import datetime, timezone
from aegisops.telemetry.models import (
    Severity,
    SourceType,
    TelemetryEvent,
    parse_iso_datetime,
)


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


def test_parse_iso_datetime_accepts_nanosecond_fraction():
    timestamp = parse_iso_datetime("2026-11-21T16:29:51.789438134+00:00")

    assert timestamp.isoformat() == "2026-11-21T16:29:51.789438+00:00"


def test_parse_iso_datetime_accepts_z_suffix():
    timestamp = parse_iso_datetime("2026-11-21T16:29:51Z")

    assert timestamp.tzinfo == timezone.utc