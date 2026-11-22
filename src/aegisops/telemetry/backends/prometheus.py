"""Prometheus client: alerts and metric samples."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aegisops.telemetry.backends.base import BackendClient
from aegisops.telemetry.models import (
    Alert, MetricSample, Severity, SourceType, TelemetryEvent,
)


_SEVERITY_MAP = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "warning": Severity.MEDIUM,
    "info": Severity.INFO,
}


class PrometheusClient(BackendClient):
    def health(self) -> bool:
        try:
            r = self._client.get("/-/ready", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def fetch_alerts(self) -> list[Alert]:
        r = self._client.get("/api/v1/alerts")
        r.raise_for_status()
        body = r.json()
        if body.get("status") != "success":
            return []

        alerts: list[Alert] = []
        for raw in body.get("data", {}).get("alerts", []):
            labels = raw.get("labels", {})
            severity = _SEVERITY_MAP.get(labels.get("severity", "").lower(), Severity.MEDIUM)
            alerts.append(
                Alert(
                    alert_id=raw.get("fingerprint") or labels.get("alertname", "unknown"),
                    alertname=labels.get("alertname", "unknown"),
                    severity=severity,
                    state=raw.get("state", "unknown"),
                    starts_at=datetime.fromisoformat(raw["activeAt"].replace("Z", "+00:00")),
                    labels=labels,
                    annotations=raw.get("annotations", {}),
                    service=labels.get("service") or labels.get("app"),
                    namespace=labels.get("namespace"),
                )
            )
        return alerts

    def fetch_metric(self, query: str) -> list[MetricSample]:
        r = self._client.get("/api/v1/query", params={"query": query})
        r.raise_for_status()
        body = r.json()
        if body.get("status") != "success":
            return []

        result = body.get("data", {}).get("result", [])
        samples: list[MetricSample] = []
        for series in result:
            metric = series.get("metric", {})
            value_pair = series.get("value", [0, "0"])
            ts, val = value_pair[0], value_pair[1]
            samples.append(
                MetricSample(
                    metric_name=metric.get("__name__", "unknown"),
                    timestamp=datetime.fromtimestamp(float(ts), tz=timezone.utc),
                    value=float(val),
                    labels=metric,
                    service=metric.get("service") or metric.get("app"),
                    namespace=metric.get("namespace"),
                )
            )
        return samples

    def alerts_to_events(self) -> list[TelemetryEvent]:
        return [
            TelemetryEvent.from_parts(
                source=SourceType.PROMETHEUS,
                timestamp=a.starts_at,
                message=f"[{a.state}] {a.alertname}: {a.annotations.get('summary', '')}",
                severity=a.severity,
                service=a.service,
                namespace=a.namespace,
                labels=a.labels,
                raw_payload=a.model_dump(mode="json"),
            )
            for a in self.fetch_alerts()
        ]

    def metrics_to_events(self, query: str) -> list[TelemetryEvent]:
        return [
            TelemetryEvent.from_parts(
                source=SourceType.PROMETHEUS,
                timestamp=s.timestamp,
                message=f"{s.metric_name} = {s.value}",
                severity=Severity.INFO,
                service=s.service,
                namespace=s.namespace,
                labels=s.labels,
                raw_payload=s.model_dump(mode="json"),
            )
            for s in self.fetch_metric(query)
        ]