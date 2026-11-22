"""Loki client: recent log lines within a time window."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aegisops.telemetry.backends.base import BackendClient
from aegisops.telemetry.models import Severity, SourceType, TelemetryEvent


_SEVERITY_KEYWORDS = {
    "critical": Severity.CRITICAL,
    "fatal": Severity.CRITICAL,
    "error": Severity.HIGH,
    "err": Severity.HIGH,
    "warn": Severity.MEDIUM,
    "warning": Severity.MEDIUM,
    "info": Severity.INFO,
    "debug": Severity.DEBUG,
}


def _infer_severity(line: str, labels: dict[str, str]) -> Severity:
    explicit = labels.get("level", labels.get("severity", "")).lower()
    if explicit in _SEVERITY_KEYWORDS:
        return _SEVERITY_KEYWORDS[explicit]
    lower = line.lower()
    for keyword, sev in _SEVERITY_KEYWORDS.items():
        if keyword in lower:
            return sev
    return Severity.INFO


class LokiClient(BackendClient):
    def health(self) -> bool:
        try:
            r = self._client.get("/ready", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def query_range(
        self,
        query: str,
        lookback: timedelta = timedelta(minutes=5),
        limit: int = 100,
    ) -> list[TelemetryEvent]:
        end = datetime.now(tz=timezone.utc)
        start = end - lookback
        r = self._client.get(
            "/loki/api/v1/query_range",
            params={
                "query": query,
                "start": str(int(start.timestamp() * 1e9)),
                "end": str(int(end.timestamp() * 1e9)),
                "limit": str(limit),
            },
        )
        r.raise_for_status()
        body = r.json()
        if body.get("status") != "success":
            return []

        events: list[TelemetryEvent] = []
        for stream in body.get("data", {}).get("result", []):
            labels = stream.get("stream", {})
            for ts_ns, line in stream.get("values", []):
                ts = datetime.fromtimestamp(int(ts_ns) / 1e9, tz=timezone.utc)
                events.append(
                    TelemetryEvent.from_parts(
                        source=SourceType.LOKI,
                        timestamp=ts,
                        message=line,
                        severity=_infer_severity(line, labels),
                        service=labels.get("app") or labels.get("service_name"),
                        namespace=labels.get("namespace"),
                        labels=labels,
                        raw_payload={"stream": labels, "line": line},
                    )
                )
        return events