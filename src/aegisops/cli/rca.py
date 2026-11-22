"""CLI: run the baseline RCA agent against the live telemetry stream."""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

from aegisops.agents.rca.agent import RCAAgent
from aegisops.llm.base import LLMResponseError
from aegisops.llm.ollama_provider import OllamaProvider
from aegisops.telemetry.normalizer import NormalizerConfig, TelemetryNormalizer


def main() -> int:
    p = argparse.ArgumentParser(description="Run the baseline RCA agent.")
    p.add_argument("--namespace", default="online-boutique")
    p.add_argument("--lookback-minutes", type=int, default=10)
    p.add_argument("--model", default="qwen2.5:7b")
    p.add_argument("--prometheus-url", default="http://localhost:30090")
    p.add_argument("--loki-url", default="http://localhost:30310")
    p.add_argument("--output", type=Path, help="Write the Incident JSON to this file")
    args = p.parse_args()

    config = NormalizerConfig(
        prometheus_url=args.prometheus_url,
        loki_url=args.loki_url,
        namespace=args.namespace,
        lookback=timedelta(minutes=args.lookback_minutes),
        metric_queries=(
            "up",
            "kube_pod_container_status_restarts_total",
            "rate(container_cpu_usage_seconds_total[1m])",
        ),
    )

    print(f"[rca] Collecting events (lookback={args.lookback_minutes}m)...", file=sys.stderr)
    events = TelemetryNormalizer(config).collect()
    print(f"[rca] Collected {len(events)} events.", file=sys.stderr)

    if not events:
        print("[rca] No events to analyze. Is the testbed running?", file=sys.stderr)
        return 1

    llm = OllamaProvider(model=args.model)
    print(f"[rca] Analyzing with {llm.model_name}...", file=sys.stderr)

    try:
        incident = RCAAgent(llm).analyze(events)
    except LLMResponseError as e:
        print(f"[rca] LLM error: {e}", file=sys.stderr)
        return 2

    rendered = incident.model_dump_json(indent=2)
    print(rendered)

    if args.output:
        args.output.write_text(rendered)
        print(f"[rca] Wrote incident to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
