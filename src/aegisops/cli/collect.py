"""CLI: print a chronological stream of normalized telemetry events."""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta

from aegisops.telemetry.normalizer import NormalizerConfig, TelemetryNormalizer


def main() -> int:
    p = argparse.ArgumentParser(description="Collect and print normalized telemetry.")
    p.add_argument("--namespace", default="online-boutique")
    p.add_argument("--lookback-minutes", type=int, default=5)
    p.add_argument("--prometheus-url", default="http://localhost:30090")
    p.add_argument("--loki-url", default="http://localhost:30310")
    p.add_argument("--limit", type=int, default=50)
    args = p.parse_args()

    config = NormalizerConfig(
        prometheus_url=args.prometheus_url,
        loki_url=args.loki_url,
        namespace=args.namespace,
        lookback=timedelta(minutes=args.lookback_minutes),
    )

    normalizer = TelemetryNormalizer(config)
    try:
        events = normalizer.collect()
    except Exception as e:
        print(f"ERROR: failed to collect telemetry: {e}", file=sys.stderr)
        return 1

    if not events:
        print("No events collected. Is the testbed running? Try 'make up'.")
        return 0

    events = events[-args.limit :]
    print(f"Collected {len(events)} events (showing last {args.limit}):\n")
    for ev in events:
        ts = ev.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        svc = ev.service or "—"
        print(f"[{ts}] [{ev.source.value:10s}] [{ev.severity.value:8s}] [{svc:20s}] {ev.message[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())