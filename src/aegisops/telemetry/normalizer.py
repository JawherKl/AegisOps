"""
TelemetryNormalizer: unifies events from Prometheus, Loki, and (optionally) Tempo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from aegisops.telemetry.backends.loki import LokiClient
from aegisops.telemetry.backends.prometheus import PrometheusClient
from aegisops.telemetry.models import SourceType, TelemetryEvent


@dataclass
class NormalizerConfig:
    prometheus_url: str = "http://localhost:30090"
    loki_url: str = "http://localhost:30310"
    tempo_url: str = "http://localhost:30320"
    namespace: str = "online-boutique"
    lookback: timedelta = timedelta(minutes=5)
    metric_queries: tuple[str, ...] = ("up",)


class TelemetryNormalizer:
    """
    Collects and normalizes telemetry from all configured backends into a
    single chronological stream of TelemetryEvent objects.

    The output is deterministic for a given time window and set of backends,
    which is required for reproducible experiments.
    """

    def __init__(self, config: NormalizerConfig) -> None:
        self.config = config

    def collect(self) -> list[TelemetryEvent]:
        events: list[TelemetryEvent] = []
        events.extend(self._collect_prometheus())
        events.extend(self._collect_loki())
        events.sort(key=lambda e: e.timestamp)
        return events

    def _collect_prometheus(self) -> list[TelemetryEvent]:
        events: list[TelemetryEvent] = []
        with PrometheusClient(self.config.prometheus_url) as client:
            events.extend(client.alerts_to_events())
            for query in self.config.metric_queries:
                events.extend(client.metrics_to_events(query))
        return events

    def _collect_loki(self) -> list[TelemetryEvent]:
        # Scope log query to the namespace of interest
        logql = f'{{namespace="{self.config.namespace}"}}'
        with LokiClient(self.config.loki_url) as client:
            return client.query_range(logql, lookback=self.config.lookback)