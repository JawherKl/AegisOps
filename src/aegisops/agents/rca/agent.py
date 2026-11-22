"""Baseline RCA agent: events -> Incident."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from aegisops.llm.base import LLMProvider
from aegisops.agents.rca.prompts import SYSTEM_PROMPT, build_analysis_prompt
from aegisops.telemetry.models import Incident, Severity, TelemetryEvent


class LLMIncidentDiagnosis(BaseModel):
    failure_class: str
    target_service: str
    summary: str
    root_cause_analysis: str
    recommended_actions: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)


_SEVERITY_BY_CLASS = {
    "T1.resource.stress-cpu": Severity.MEDIUM,
    "T1.resource.stress-memory": Severity.HIGH,
    "T2.availability.pod-kill": Severity.HIGH,
    "T2.availability.pod-failure": Severity.CRITICAL,
    "T3.communication.network-delay": Severity.MEDIUM,
    "T3.communication.network-loss": Severity.HIGH,
    "T3.communication.network-partition": Severity.CRITICAL,
}


class RCAAgent:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    def analyze(self, events: list[TelemetryEvent]) -> Incident:
        if not events:
            raise ValueError("RCAAgent requires at least one event to analyze")

        prompt = build_analysis_prompt(events)
        diagnosis = self.llm.generate_structured(
            prompt=prompt,
            response_model=LLMIncidentDiagnosis,
            system_prompt=SYSTEM_PROMPT,
        )
        severity = _SEVERITY_BY_CLASS.get(diagnosis.failure_class, Severity.MEDIUM)

        return Incident(
            incident_id=f"inc-{uuid.uuid4().hex[:12]}",
            created_at=datetime.now(timezone.utc),
            severity=severity,
            title=f"{diagnosis.failure_class} on {diagnosis.target_service}",
            summary=diagnosis.summary,
            root_cause_analysis=diagnosis.root_cause_analysis,
            correlated_events=[ev.event_id for ev in events],
            recommended_actions=diagnosis.recommended_actions,
            confidence_score=diagnosis.confidence_score,
        )