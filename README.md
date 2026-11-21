# AegisOps

> **A Reproducible Research Testbed for Safe, LLM-Augmented DevOps Automation**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Kind%20%7C%20k3s-blue?logo=kubernetes)](https://kind.sigs.k8s.io/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20%7C%20Local%20%26%20Free-green)](https://ollama.com/)
[![Prometheus](https://img.shields.io/badge/Monitoring-Prometheus-orange?logo=prometheus)](https://prometheus.io/)
[![Status](https://img.shields.io/badge/Status-Phase%201%3A%20Instrumentation-brightgreen)]()

---

## What is AegisOps?

AegisOps is an **open, reproducible research testbed** for investigating how Large Language Models (LLMs) and classical ML can make DevOps pipelines and cloud infrastructure *self-observing, self-diagnosing, and self-healing*—safely.

Unlike existing tools that demonstrate AI-powered DevOps in isolation, AegisOps provides a **controlled experimental environment** with:

- **Standardized failure injection** (Chaos Mesh + custom CI failure library)
- **Full-stack observability** (Prometheus, Loki, Tempo, Grafana)
- **Pluggable LLM backends** (Ollama for zero-cost local inference, plus optional frontier-model baselines)
- **Reproducible benchmarks** for root-cause analysis and remediation correctness

The project is structured around three research thrusts:

| Thrust | Focus | Key Question |
|---|---|---|
| **Aegis-CI** | Intelligent CI/CD remediation | Can hybrid ML–LLM pipelines fix build failures with high precision and low cost? |
| **Aegis-Observe** | LLM-driven root-cause analysis | How far can agentic LLMs go in correlating logs, metrics, and traces—and where do they fail? |
| **Aegis-Heal** | Safe self-healing Kubernetes | What architectural patterns make autonomous remediation *provably safe*? |

> **Research context:** This repository is the artifact companion to a PhD thesis on AI-augmented DevOps automation. All code, datasets, benchmarks, and experiment scripts are released open-source to maximize reproducibility and community adoption.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        AegisOps Testbed                              │
│                                                                      │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────┐  │
│  │  Kind / k3s │    │  Prometheus     │    │  Loki (logs)        │  │
│  │  Cluster    │───▶│  (metrics)      │    │  Tempo (traces)     │  │
│  │             │    │  Alertmanager   │    │  Grafana            │  │
│  └──────┬──────┘    └────────┬────────┘    └──────────┬──────────┘  │
│         │                    │                        │             │
│         ▼                    ▼                        ▼             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Telemetry Normalization Layer                   │   │
│  │         (unified schema for logs, metrics, events)           │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                       │
│                             ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              AegisOps Agent Runtime                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │ Aegis-CI    │  │ Aegis-      │  │ Aegis-Heal          │  │   │
│  │  │ (gatekeeper │  │ Observe     │  │ (safety-constrained │  │   │
│  │  │  + LLM)     │  │ (agentic    │  │  remediation        │  │   │
│  │  │             │  │  RCA)       │  │  executor)          │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │   │
│  │         │                │                     │             │   │
│  │         ▼                ▼                     ▼             │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │         LLM Abstraction Layer (Ollama / APIs)          │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │         Failure Injection & Evaluation Harness               │   │
│  │     (Chaos Mesh + CI failure library + scoring engine)       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Features (Phase 1)

- ✅ **One-command testbed:** Spin up a complete Kind cluster with observability stack via `make up`
- ✅ **Zero-cost LLM:** Ollama integration with Llama 3.1 / Qwen 2.5 (local, private, free)
- ✅ **Failure library:** 15+ injectable failure scenarios with ground-truth labels (CI build failures, pod crashes, OOMKilled, network partitions)
- ✅ **Baseline agents:** Wrappers around HolmesGPT and a custom lightweight RCA agent for comparison studies
- ✅ **Evaluation harness:** Automated scoring for detection latency, RCA accuracy, and remediation success rate
- 🔜 **Phase 2:** Safety-gated remediation executor, benchmark dataset release, paper artifacts

---

## Quick Start

### Prerequisites
- Docker Desktop (with ≥ 8 GB RAM allocated)
- [Kind](https://kind.sigs.k8s.io/) (`brew install kind` or equivalent)
- [Ollama](https://ollama.com/download) (for local LLM inference)
- `kubectl`, `helm`, `make`

### 1. Clone and bootstrap
```bash
git clone https://github.com/<your-username>/aegisops.git
cd aegisops
make bootstrap   # installs kind, helm charts, and pulls Ollama model
```

### 2. Start the cluster and observability stack
```bash
make up
```

### 3. Pull an LLM and run a sample experiment
```bash
ollama pull qwen2.5:7b
make experiment-ci   # runs the CI failure injection + RCA baseline
```

### 4. View results
```bash
make report   # opens the evaluation dashboard at localhost:30300
```

---

## Project Structure

```
aegisops/
├── README.md
├── LICENSE
├── Makefile                         # Top-level orchestration (make up/down/experiment/report)
├── pyproject.toml                   # Python project config (lint, test, packaging)
├── .gitignore
├── .pre-commit-config.yaml
│
├── infra/                           # Testbed infrastructure (all IaC)
│   ├── kind/
│   │   └── cluster.yaml             # Kind cluster definition (1 control-plane, 2 workers)
│   ├── helm/
│   │   ├── prometheus-stack.yaml    # kube-prometheus-stack values
│   │   ├── loki-stack.yaml
│   │   └── tempo.yaml
│   ├── chaos/
│   │   └── chaos-mesh-install.sh
│   └── apps/
│       └── online-boutique.yaml     # Sample microservice target
│
├── src/
│   ├── aegisops/
│   │   ├── __init__.py
│   │   ├── telemetry/               # Unified telemetry normalization
│   │   │   ├── normalizer.py        # Converts Prometheus/Loki/Tempo to shared schema
│   │   │   └── models.py            # Pydantic schemas for events, metrics, alerts
│   │   ├── llm/                     # LLM abstraction layer
│   │   │   ├── base.py              # Abstract LLM interface
│   │   │   ├── ollama_provider.py
│   │   │   └── openai_provider.py   # Optional, for baseline comparison
│   │   ├── agents/
│   │   │   ├── ci/                  # Aegis-CI
│   │   │   │   ├── gatekeeper.py    # ML classifier (SVM/GBM) for failure triage
│   │   │   │   └── remediator.py    # LLM patch synthesis
│   │   │   ├── observe/             # Aegis-Observe
│   │   │   │   ├── agent.py         # Agentic RCA loop (tool-calling)
│   │   │   │   └── tools.py         # PromQL, LogQL, kubectl tool definitions
│   │   │   └── heal/                # Aegis-Heal
│   │   │       ├── planner.py       # Remediation plan generation
│   │   │       └── executor.py      # Safety-gated action executor (Phase 2)
│   │   └── eval/                    # Evaluation harness
│   │       ├── metrics.py           # Detection latency, RCA accuracy, MTTR
│   │       ├── runner.py            # Experiment orchestrator
│   │       └── scorers.py           # Custom scoring functions
│   │
│   └── cli/
│       └── main.py                  # `aegisops` CLI entry point
│
├── experiments/                     # Reproducible experiment configs
│   ├── ci-failure-baseline/
│   │   ├── config.yaml
│   │   └── failures.json            # Ground-truth labeled failure scenarios
│   ├── rca-holmes-comparison/
│   │   └── config.yaml
│   └── heal-safety-gate/
│       └── config.yaml
│
├── benchmarks/                      # Datasets and evaluation suites
│   ├── ci-failures/
│   │   ├── raw/                     # Collected CI logs (anonymized)
│   │   └── labeled/                 # Ground-truth failure taxonomy labels
│   └── k8s-incidents/
│       └── scenarios/               # Chaos experiment definitions
│
├── notebooks/                       # Analysis notebooks (exploratory, not production)
│   ├── 01_failure_taxonomy.ipynb
│   └── 02_gatekeeper_eval.ipynb
│
├── docs/
│   ├── architecture.md
│   ├── research-agenda.md           # Detailed PhD thrust descriptions
│   ├── benchmark-spec.md            # Dataset schema and labeling guide
│   └── phase1-roadmap.md            # 6-month plan with milestones
│
├── tests/                           # Unit and integration tests
│   ├── unit/
│   └── integration/
│
└── scripts/
    ├── collect_ci_logs.py           # Scrape public CI logs from GitHub
    └── inject_failures.py           # Chaos Mesh wrapper
```

---

## Roadmap

| Phase | Timeline | Deliverable |
|---|---|---|
| **Phase 1: Instrumentation** | Months 1–6 | Testbed, failure library, evaluation harness, workshop paper draft |
| Phase 2: Aegis-CI | Months 7–12 | Hybrid ML–LLM pipeline, CI failure benchmark, full paper submission |
| Phase 3: Aegis-Observe | Months 13–20 | Agentic RCA benchmark, hallucination study, full paper |
| Phase 4: Aegis-Heal | Months 21–30 | Safety-gated executor, chaos evaluation, systems paper |
| Phase 5: Synthesis | Months 31–36 | Thesis, unified framework, open-source release v1.0 |

See [docs/phase1-roadmap.md](docs/phase1-roadmap.md) for the detailed 6-month plan.

---

## Contributing

This is a research-first repository. Contributions are welcome in the form of:
- New failure scenarios for the injection library
- Bug reports and testbed improvements
- Benchmark dataset extensions

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a PR. For research collaboration inquiries, open a GitHub Discussion.

---

## Citation

If you use AegisOps in your research, please cite:

```bibtex
@software{aegisops2026,
  title   = {AegisOps: A Reproducible Research Testbed for Safe, LLM-Augmented DevOps Automation},
  author  = {<Your Name>},
  year    = {2026},
  url     = {https://github.com/<your-username>/aegisops},
  note    = {PhD research artifact}
}
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

**Built with:** Kubernetes · Kind · Prometheus · Loki · Grafana · Chaos Mesh · Ollama · Python · Go (for operators) · GitHub Actions
