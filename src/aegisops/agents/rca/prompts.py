"""Prompt templates for the baseline RCA agent."""
from __future__ import annotations

from aegisops.telemetry.models import TelemetryEvent

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer analyzing telemetry
from a Kubernetes-based microservices application called Online Boutique.

Your task: given a chronological stream of events, identify the most likely
root cause of the incident and produce a structured diagnosis.

The failure taxonomy is:
- T1.resource.stress-cpu: sustained CPU saturation on a service
- T1.resource.stress-memory: sustained memory pressure on a service
- T2.availability.pod-kill: a pod was forcibly terminated
- T2.availability.pod-failure: a pod is repeatedly failing or unavailable
- T3.communication.network-delay: added latency between two services
- T3.communication.network-loss: packet loss between two services
- T3.communication.network-partition: complete network isolation

Respond with a single JSON object matching exactly this schema:
{
  "failure_class": "<one of the taxonomy values above>",
  "target_service": "<the service name that is the root cause>",
  "summary": "<one-sentence description of what is happening>",
  "root_cause_analysis": "<2-3 sentences explaining the causal chain>",
  "recommended_actions": ["<action 1>", "<action 2>"],
  "confidence_score": <float between 0.0 and 1.0>
}

Do not include any text outside the JSON object.
"""


def build_analysis_prompt(events: list[TelemetryEvent], max_events: int = 40) -> str:
    """
    Format a window of TelemetryEvents into a prompt for the RCA agent.
    """
    trimmed = events[-max_events:]
    lines = [f"You are analyzing {len(trimmed)} telemetry events.\n"]

    for ev in trimmed:
        ts = ev.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        svc = ev.service or "unknown"
        lines.append(
            f"[{ts}] source={ev.source.value} severity={ev.severity.value} "
            f"service={svc} :: {ev.message[:200]}"
        )

    lines.append("\nProvide your diagnosis as a single JSON object.")
    return "\n".join(lines)