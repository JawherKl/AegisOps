## 1. Project Name: **AegisOps**

**Tagline:** *AegisOps — A Reproducible Research Testbed for Safe, LLM-Augmented DevOps Automation*

**Why this name works:**
- **"Aegis"** evokes protection, shielding, and safety—central to the PhD's core contribution of **safety-constrained self-healing** (not just automation, but *safe* automation).
- **"Ops"** grounds it in the DevOps/AIOps domain.
- It is short, memorable, and unclaimed in the OSS ecosystem (unlike `AURA`, `GopherGuard`, or `ai-devops-platform`).
- It scales: the repo can later host sub-modules like `aegis-ci` (Thrust A), `aegis-observe` (Thrust B), and `aegis-heal` (Thrust C).

---

## 2. README.md (Copy-Paste Ready)

```markdown
See [README](Readme.md)
```

## 3. Why This README Structure Works for a PhD Repository

A research repository must answer **five questions** in the first 30 seconds[reference:2]:

1. **What is this?** → The tagline and "What is AegisOps?" section.
2. **Why does it matter?** → The research context note and the three-thrust table.
3. **How do I run it?** → The Quick Start with a one-command bootstrap.
4. **What makes it credible?** → Badges, architecture diagram, roadmap, and citation block.
5. **How do I engage?** → Contributing section and GitHub Discussions pointer.

The architecture diagram is deliberately placed early: it signals that this is an **engineered system**, not a loose collection of scripts—critical for reviewers and potential collaborators who evaluate research artifacts[reference:3].

---

## 4. Six-Month Phase 1 Roadmap (Detailed)

The first six months are about **building the instrument**, not running the full experiment. Your deliverable is a testbed and a workshop paper. Here is the week-by-week breakdown.

### Month 1: Foundation and Cluster Bootstrap

**Goal:** A working Kind cluster with the full observability stack, deployed via a single command.

| Week | Task | Success Criterion |
|---|---|---|
| 1 | Initialize repo, CI skeleton (GitHub Actions: lint + test), write `Makefile` targets | `make test` passes on empty repo |
| 2 | Write `infra/kind/cluster.yaml`; bootstrap Kind cluster | `kubectl get nodes` shows 3 nodes |
| 3 | Deploy Prometheus + Alertmanager + Grafana via Helm | Grafana reachable at `localhost:30300`; Prometheus scraping the cluster |
| 4 | Deploy Loki + Tempo + sample app (Online Boutique) | Logs and traces visible in Grafana; app serves traffic |

**Deliverable:** `make up` spins up the entire stack from zero.

---

### Month 2: Telemetry Normalization and LLM Abstraction

**Goal:** A unified data layer and a swappable LLM backend.

| Week | Task | Success Criterion |
|---|---|---|
| 5 | Define Pydantic schemas for `Event`, `Metric`, `Alert`, `Incident` in `src/aegisops/telemetry/models.py` | Schema documented; unit tests pass |
| 6 | Implement `normalizer.py`: pull from Prometheus/Loki APIs and map to the shared schema | Normalizer outputs validated Pydantic objects for 3 sample incidents |
| 7 | Build `LLMProvider` abstraction (`base.py`) + `OllamaProvider` | `make llm-test` sends a prompt to Ollama and returns a structured response |
| 8 | Add `OpenAIProvider` (optional) for baseline comparison; write integration test | Both providers pass the same contract test suite |

**Deliverable:** A documented telemetry schema and a working LLM abstraction—the foundation for all three thrusts.

---

### Month 3: Failure Injection Library

**Goal:** A reproducible, labeled failure library with at least 10 CI failures and 5 Kubernetes failures.

| Week | Task | Success Criterion |
|---|---|---|
| 9 | Install Chaos Mesh; write `chaos/pod-kill.yaml`, `chaos/network-delay.yaml` | Chaos experiments run via `kubectl apply` |
| 10 | Build `scripts/inject_failures.py` wrapper (Python client for Chaos Mesh + GitHub Actions API) | Can trigger pod kill, OOM, and CI build failure programmatically |
| 11 | Curate 10 CI failure logs from public GitHub repos (anonymized); label with a draft taxonomy | `benchmarks/ci-failures/labeled/` contains 10 JSON files with labels |
| 12 | Write `docs/benchmark-spec.md`: define the failure taxonomy, labeling guide, and ground-truth format | Spec reviewed and frozen for Phase 1 |

**Deliverable:** A failure library that any researcher can replay with one command.

---

### Month 4: Baseline RCA Agent and Evaluation Harness

**Goal:** A working baseline agent and an automated scoring pipeline.

| Week | Task | Success Criterion |
|---|---|---|
| 13 | Implement `Aegis-Observe` agent loop (`agents/observe/agent.py`) with tool-calling over PromQL, LogQL, and `kubectl describe` | Agent diagnoses 3 out of 5 injected failures correctly |
| 14 | Implement `eval/metrics.py`: detection latency, RCA accuracy (top-1 and top-3), tool-call count | Metrics computed automatically from experiment runs |
| 15 | Build `eval/runner.py`: orchestrates injection → agent → scoring | `make experiment-rca` runs end-to-end and produces a JSON report |
| 16 | Integrate HolmesGPT as a baseline: wrap its API and run the same experiment | Comparison table (Aegis baseline vs. HolmesGPT) generated |

**Deliverable:** The first quantitative results table—even if small (n=5)—that proves the harness works.

---

### Month 5: Dataset Expansion and Reproducibility Hardening

**Goal:** Scale the failure library and ensure the entire testbed is reproducible from scratch.

| Week | Task | Success Criterion |
|---|---|---|
| 17 | Expand CI failure dataset to 30+ labeled examples; add K8s failure scenarios to 10 | `benchmarks/` contains 40+ labeled scenarios |
| 18 | Write `docs/phase1-roadmap.md` (this document); add reproducibility tests (`tests/integration/test_reproducibility.py`) | `make reproduce` passes on a fresh machine |
| 19 | Add GitHub Actions workflow that runs the full testbed on every push (Kind-in-Docker) | CI green; integration tests complete in < 15 minutes |
| 20 | Write the **workshop paper draft**: "AegisOps: A Reproducible Testbed for AI-Augmented DevOps Research" | Draft complete (4–6 pages), submitted to internal review |

**Deliverable:** A citable artifact and a workshop paper draft.

---

### Month 6: Release, Documentation, and Phase 2 Planning

**Goal:** Public v0.1.0 release and a concrete plan for Thrust A.

| Week | Task | Success Criterion |
|---|---|---|
| 21 | Finalize README, CONTRIBUTING, CODE_OF_CONDUCT, and issue templates | Repo passes a "fresh-eyes" usability test (a colleague runs Quick Start without help) |
| 22 | Tag `v0.1.0`; publish to GitHub with a Zenodo DOI (for citability) | DOI minted; release notes written |
| 23 | Submit workshop paper; post on relevant forums (CNCF Slack, r/devops, Hacker News) | Paper submitted; community feedback collected |
| 24 | Write the **Phase 2 research design**: gatekeeper architecture, dataset collection plan, evaluation protocol for Aegis-CI | `docs/phase2-design.md` completed and reviewed with advisor |

**Phase 1 Exit Criteria:**
- ✅ Reproducible testbed with one-command bootstrap
- ✅ 40+ labeled failure scenarios (30 CI + 10 K8s)
- ✅ Working baseline RCA agent with quantitative results
- ✅ Public v0.1.0 release with DOI
- ✅ Workshop paper submitted
- ✅ Phase 2 research design approved

---

## 5. Strategic Advice for the Repository Launch

**Do not wait for perfection.** A common failure mode in PhD engineering is spending 12 months building infrastructure before a single result exists. The Month 4 milestone (a tiny n=5 experiment) is deliberately early: it forces you to confront evaluation challenges before the dataset grows, and it gives you something concrete to show your advisor and potential collaborators.

**Treat the failure library as a first-class research contribution.** DevOps-Gym demonstrated that a well-curated benchmark can itself be a publishable artifact, independent of the agents evaluated on it[reference:4]. Your `benchmarks/ci-failures/` directory should be designed with the same rigor: documented schema, labeling guide, and versioned releases. This is how you ensure the repository is cited even if your agent architecture evolves.

**Use the "Research Context" note in the README strategically.** It signals to academic reviewers that this is not a hobby project, and to industry practitioners that the tooling is grounded in real problems. The citation block and Zenodo DOI make the artifact citable from day one—a small detail that significantly increases the likelihood of adoption in the research community[reference:5].

**Keep the LLM abstraction layer thin but strict.** The `LLMProvider` interface should enforce structured output schemas (Pydantic models) rather than free-text responses. This is not just engineering hygiene—it is a research necessity. When you later compare Ollama 7B vs. a frontier model, the comparison is only meaningful if both are constrained to the same output contract.
