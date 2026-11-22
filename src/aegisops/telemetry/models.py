"""
Unified telemetry schemas for AegisOps.

Every observable event—regardless of whether it originates from Prometheus,
Loki, or Tempo—is mapped into one of these models. This gives downstream
agents (RCA, remediation, evaluation) a single, typed representation to
reason over.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Which backend produced this event."""
    PROMETHEUS = "prometheus"
    LOKI = "loki"
    TEMPO = "tempo"
    KUBERNETES = "kubernetes"


def parse_iso_datetime(value: str) -> datetime:
    """Parse ISO timestamps, including nanosecond fractional seconds."""
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    normalized = re.sub(r"(\.\d{6})\d+(?=(?:[+-]\d{2}:?\d{2})?$)", r"\1", normalized)

    timestamp = datetime.fromisoformat(normalized)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp


class Severity(str, Enum):
    """Normalized severity scale, aligned with Prometheus alert labels."""
    DEBUG = "debug"
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _make_event_id(source: SourceType, timestamp: datetime, service: Optional[str], message: str) -> str:
    """
    Deterministic event ID: same inputs => same ID.

    Determinism matters for deduplication: if the normalizer is run twice over
    the same time window, downstream agents should see identical event IDs.
    """
    raw = f"{source.value}|{timestamp.isoformat()}|{service or ''}|{message}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class TelemetryEvent(BaseModel):
    """
    A single observable event, normalized from any backend.

    This is the primary unit of input for Aegis agents. Each event captures
    enough context for an LLM (or classical model) to reason over it without
    having to re-query the original backend.
    """
    event_id: str
    timestamp: datetime
    source: SourceType
    severity: Severity = Severity.INFO
    message: str

    service: Optional[str] = None
    namespace: Optional[str] = None

    # Cross-backend correlation IDs
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    # Backend-specific labels (e.g., Prometheus alert labels, Loki stream labels)
    labels: dict[str, str] = Field(default_factory=dict)

    # The unmodified backend payload, preserved for downstream analysis
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_parts(
        cls,
        source: SourceType,
        timestamp: datetime,
        message: str,
        **kwargs: Any,
    ) -> "TelemetryEvent":
        """Build an event, auto-generating the deterministic event_id."""
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return cls(
            event_id=_make_event_id(source, timestamp, kwargs.get("service"), message),
            source=source,
            timestamp=timestamp,
            message=message,
            **kwargs,
        )


class MetricSample(BaseModel):
    """A single point-in-time sample of a Prometheus metric."""
    metric_name: str
    timestamp: datetime
    value: float
    labels: dict[str, str] = Field(default_factory=dict)
    service: Optional[str] = None
    namespace: Optional[str] = None


class Alert(BaseModel):
    """A Prometheus/Alertmanager alert, normalized."""
    alert_id: str
    alertname: str
    severity: Severity
    state: str  # "firing" | "pending" | "resolved"
    starts_at: datetime
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    service: Optional[str] = None
    namespace: Optional[str] = None


class Incident(BaseModel):
    """
    A synthesized incident report, produced by an Aegis agent from a set of
    correlated TelemetryEvents. This is the primary *output* type of the RCA
    and remediation thrusts.
    """
    incident_id: str
    created_at: datetime
    severity: Severity
    title: str
    summary: str
    root_cause_analysis: Optional[str] = None
    correlated_events: list[str] = Field(default_factory=list)  # event_ids
    recommended_actions: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)