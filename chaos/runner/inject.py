#!/usr/bin/env python3
"""
Inject a named chaos scenario and record its ground-truth window.

Usage:
    python chaos/runner/inject.py --scenario frontend-pod-kill
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_FILE = ROOT / "chaos" / "runner" / "scenarios.yaml"
GROUND_TRUTH_DIR = ROOT / "benchmarks" / "chaos-ground-truth"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, help="Name from scenarios.yaml")
    parser.add_argument("--clean", action="store_true", help="Delete the chaos resource after injection")
    args = parser.parse_args()

    scenarios = yaml.safe_load(SCENARIOS_FILE.read_text())
    if args.scenario not in scenarios:
        print(f"Unknown scenario: {args.scenario}", file=sys.stderr)
        print(f"Available: {', '.join(scenarios)}", file=sys.stderr)
        return 1

    scenario = scenarios[args.scenario]
    manifest = ROOT / scenario["manifest"]

    injection_id = f"inj-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    injected_at = datetime.now(timezone.utc).isoformat()

    print(f"[{injection_id}] Applying {manifest.name} ...")
    try:
        run(["kubectl", "apply", "-f", str(manifest)])
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        print(f"ERROR: failed to apply chaos manifest: {detail}", file=sys.stderr)
        return 1

    duration_seconds = scenario.get("duration_seconds", 300)
    print(f"[{injection_id}] Injection active for {duration_seconds}s. "
          f"Telemetry collection window open.")
    time.sleep(duration_seconds)

    ended_at = datetime.now(timezone.utc).isoformat()

    record = {
        "injection_id": injection_id,
        "failure_class": scenario["failure_class"],
        "target_service": scenario["target_service"],
        "target_namespace": scenario.get("target_namespace", "online-boutique"),
        "chaos_resource": scenario["chaos_resource"],
        "injected_at": injected_at,
        "ended_at": ended_at,
        "parameters": scenario.get("parameters", {}),
        "expected_symptoms": scenario["expected_symptoms"],
    }

    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GROUND_TRUTH_DIR / f"{injection_id}.json"
    out_path.write_text(json.dumps(record, indent=2))
    print(f"[{injection_id}] Ground truth written to {out_path}")

    if args.clean:
        print(f"[{injection_id}] Deleting chaos resource ...")
        run(["kubectl", "delete", "-f", str(manifest), "--ignore-not-found"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())