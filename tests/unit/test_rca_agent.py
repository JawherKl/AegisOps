from datetime import datetime, timezone
from unittest.mock import MagicMock

from aegisops.agents.rca.agent import LLMIncidentDiagnosis, RCAAgent
from aegisops.telemetry.models import Severity, SourceType, TelemetryEvent


def test_agent_maps_diagnosis_to_incident():
    llm = MagicMock()
    llm.generate_structured.return_value = LLMIncidentDiagnosis(
        failure_class="T2.availability.pod-kill",
        target_service="frontend",
        summary="frontend pod restarted",
        root_cause_analysis="pod was forcibly terminated",
        recommended_actions=["verify pod health"],
        confidence_score=0.9,
    )

    ts = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
    events = [
        TelemetryEvent.from_parts(
            source=SourceType.LOKI, timestamp=ts,
            message="frontend restarted", service="frontend",
        )
    ]

    incident = RCAAgent(llm).analyze(events)

    assert incident.severity == Severity.HIGH
    assert incident.title == "T2.availability.pod-kill on frontend"
    assert incident.confidence_score == 0.9
    assert len(incident.correlated_events) == 1


def test_agent_rejects_empty_events():
    llm = MagicMock()
    import pytest
    with pytest.raises(ValueError):
        RCAAgent(llm).analyze([])