Congratulations on completing the foundational step—your `make up` command now reliably delivers a full observability stack. This is a significant milestone. The next step is to give that stack something meaningful to observe, and simultaneously build the core abstraction layer that will power your Aegis agents.

Per your Phase 1 roadmap, the next milestone (Weeks 5–8) is **Telemetry Normalization and LLM Abstraction**. This decomposes into three concrete deliverables:

1.  **Deploy the Target Application:** A realistic microservice workload (Online Boutique) with an OpenTelemetry Collector to generate traces, metrics, and logs.
2.  **Implement the Telemetry Normalization Layer:** The Pydantic schemas and normalizer that convert raw telemetry from Prometheus, Loki, and Tempo into a unified, agent-ready format.
3.  **Implement the LLM Abstraction Layer:** A provider interface with Ollama as the zero-cost local backend.

---

### 📦 Deliverable 1: Deploy the Target Application & OTel Collector

Your observability stack is currently watching an empty cluster. You need a target to observe and, later, to fail.

**The Application:** Google's **Online Boutique** is the ideal choice. It is a polyglot microservices demo with services written in Go, Python, Node.js, C#, and Java, already instrumented with OpenTelemetry for traces. This heterogeneity is valuable for research—it lets you test whether your future RCA agents generalize across languages and runtimes.

**The Telemetry Pipeline:** You will deploy an **OpenTelemetry Collector**. The collector acts as a central hub: applications send OTLP telemetry to it, and it fans out traces to Tempo, metrics to Prometheus, and logs to Loki. This decouples the application from the backends and gives you a single place to enrich or filter telemetry before storage.

#### Implementation Steps

1.  **Add the manifests to your repository.** Create `infra/apps/online-boutique.yaml` using the official Kubernetes manifests from `GoogleCloudPlatform/microservices-demo`. Ensure the `loadgenerator` service is included—it will generate a steady stream of artificial traffic, which is essential for producing meaningful telemetry.

2.  **Deploy the OpenTelemetry Collector.** Add `infra/helm/otel-collector.yaml` (Helm values) and a Makefile target to install it. The collector configuration should route signals as follows:
    - **Traces:** `otlp` receiver → `otlp` exporter pointing to `tempo.observability.svc.cluster.local:4317`.
    - **Metrics:** `otlp` receiver → `prometheus` exporter (scraped by your existing Prometheus).
    - **Logs:** `otlp` receiver → `loki` exporter. Alternatively, if the application writes logs to stdout only, deploy **Grafana Alloy** as a DaemonSet to tail container logs and push them to Loki.

3.  **Configure the application to send to the collector.** Set the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable in the Online Boutique deployments to point to your collector service (e.g., `http://otel-collector.observability.svc.cluster.local:4317`).

**Success Criterion:** After running `make up`, you can open Grafana, go to **Explore → Tempo**, and see traces from services like `frontend` and `cartservice`. Query `{namespace="online-boutique"}` in Loki to see logs. Prometheus should show application-level RED metrics (request rate, error rate, duration) alongside cluster metrics.

---

### 🧬 Deliverable 2: The Telemetry Normalization Layer

This is where the research begins. Your agents cannot reason over raw PromQL, LogQL, or OTLP spans directly—they need a **unified incident representation**. You will define Pydantic schemas for four core entities: `Event`, `Metric`, `Alert`, and `Incident`.

A helpful reference is the `aegis-os` project, which defines a clean `AIIncidentReport` schema with fields for `incident_id`, `severity`, `title`, `summary`, `root_cause_analysis`, `correlated_sensors`, and `recommended_actions`. You can adapt this structure for AegisOps.

#### File Structure & Schemas

Create the following files in `src/aegisops/telemetry/`:

```python
# src/aegisops/telemetry/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TelemetryEvent(BaseModel):
    """A unified representation of any observable event (log, alert, trace span)."""
    event_id: str
    timestamp: datetime
    source: str  # e.g., "prometheus", "loki", "tempo", "kubernetes"
    service: Optional[str] = None
    namespace: Optional[str] = None
    severity: Severity = Severity.LOW
    message: str
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    # Correlation identifiers
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)

class Incident(BaseModel):
    """A synthesized incident report generated by an Aegis agent."""
    incident_id: str
    timestamp: datetime
    severity: Severity
    title: str
    summary: str
    root_cause_analysis: Optional[str] = None
    correlated_events: List[str] = Field(default_factory=list)  # event_ids
    recommended_actions: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
```

Your `normalizer.py` will query the Prometheus, Loki, and Tempo HTTP APIs and map the responses into `TelemetryEvent` objects. For example, a Prometheus alert becomes an event with `source="prometheus"`; a Loki log line becomes an event with `source="loki"` and the log message; a Tempo span becomes an event with the trace and span IDs populated.

**Success Criterion:** You can run a script that pulls the last 10 events from each backend and prints them as a unified `List[TelemetryEvent]`. This proves the abstraction works.

---

### 🤖 Deliverable 3: The LLM Abstraction Layer

To keep the research reproducible and zero-cost, you need a provider-agnostic interface. Create `src/aegisops/llm/base.py` with an abstract `LLMProvider` class and `src/aegisops/llm/ollama_provider.py` implementing it using the `ollama` Python library.

The interface should enforce **structured output** via Pydantic models. For example, your `remediate` method should accept a Pydantic response model and validate the LLM's output against it. This is a research necessity: it ensures that when you later compare a local 7B model against a frontier API model, you are comparing them under the same output contract.

**Success Criterion:** A unit test that sends a prompt to Ollama (`qwen2.5:7b`) and validates the response against a simple Pydantic schema (e.g., `{"action": "restart_pod", "confidence": 0.9}`).

---

### 🗺️ Your Updated Roadmap

| Step | Focus | Key Deliverable |
| :--- | :--- | :--- |
| **Step 2 (Now)** | **Telemetry & LLM Abstraction** | Online Boutique + OTel Collector + Pydantic schemas + Ollama provider |
| **Step 3 (Next)** | **Failure Injection Library** | Install Chaos Mesh, create 10+ labeled failure scenarios (pod kill, network delay, CPU stress) |
| **Step 4** | **Baseline RCA Agent** | An agent that consumes `TelemetryEvent` objects and produces `Incident` reports using the Ollama provider |
| **Step 5** | **Evaluation Harness** | Automated scoring for detection latency, RCA accuracy, and tool-call efficiency |

### 🚀 Immediate Action

Start with **Deliverable 1**. Add the Online Boutique manifests and the OpenTelemetry Collector to your `Makefile`. Once `make up` brings the application online and you can see a single trace in Tempo, you have closed the loop from application to observability backend. Then move to the schemas—they are the contract that every subsequent agent and experiment in AegisOps will be built upon.