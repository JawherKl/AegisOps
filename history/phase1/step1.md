Phase 1, Step 1 — The make up Testbed


This is the foundational step that everything else in AegisOps will be built upon. Getting this right means you'll have a reproducible, one-command environment for all your experiments—and it directly delivers the "One-command testbed" promise from your README.

Here is a complete, professional implementation guide for Phase 1, Step 1.

---

## Phase 1, Step 1 — The `make up` Testbed

The objective is to go from a fresh clone to a fully instrumented Kubernetes cluster with **metrics, logs, and traces** flowing into Grafana, all triggered by a single `make up` command.

### 1. Prerequisites & Pre-Flight Check

Your `make up` target should **fail fast** with a clear message if a dependency is missing. This is critical for reproducibility. Create a preflight script that checks for:

- **Docker** (running daemon)
- **kind** (v0.20+)
- **kubectl** (v1.27+)
- **helm** (v3.13+)

A simple `scripts/preflight.sh` using `command -v` for each tool is sufficient. The `kube-prometheus-stack` chart itself requires a compatible Kubernetes and Helm version, so checking these early avoids cryptic Helm errors later .

---

### 2. The Kind Cluster Configuration (`infra/kind/cluster.yaml`)

A single-node cluster is tempting for simplicity, but a **multi-node cluster** (1 control-plane + 2 workers) is strongly recommended for AegisOps. Your future failure injection scenarios (pod eviction, node pressure, network partitions) will behave more realistically, and observability components can be spread across nodes.

The standard Kind pattern for a multi-node cluster is a YAML file with a `nodes` list specifying roles :

```yaml
# infra/kind/cluster.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    # Expose NodePorts so Grafana/Prometheus are reachable on localhost
    extraPortMappings:
      - containerPort: 3000   # Grafana
        hostPort: 3000
        protocol: TCP
      - containerPort: 9090   # Prometheus
        hostPort: 9090
        protocol: TCP
      - containerPort: 3100   # Loki
        hostPort: 3100
        protocol: TCP
      - containerPort: 3200   # Tempo
        hostPort: 3200
        protocol: TCP
  - role: worker
  - role: worker
```

**Key design decision:** The `extraPortMappings` on the control-plane node allow you to reach the observability UIs directly at `localhost:3000` (Grafana), `localhost:9090` (Prometheus), etc., **without** needing `kubectl port-forward` in separate terminals. This makes the testbed far more ergonomic and aligns with the "one-command" philosophy. The NodePorts you later assign in Helm values must match these host mappings .

---

### 3. The Observability Stack — Helm Values Files

You will install three separate Helm releases into a dedicated `observability` namespace. Keeping the values files in `infra/helm/` makes the configuration version-controlled and auditable.

#### 3.1 `kube-prometheus-stack` (`infra/helm/prometheus-stack.yaml`)

This chart is the standard way to deploy Prometheus, Alertmanager, and Grafana together with all the Kubernetes scrape configs and dashboards . For a local testbed, you want **ephemeral storage** (no PVCs) and **NodePort services** matching your Kind port mappings.

```yaml
# infra/helm/prometheus-stack.yaml
prometheus:
  service:
    type: NodePort
    nodePort: 9090
  prometheusSpec:
    retention: 3d
    resources:
      requests:
        memory: 512Mi
        cpu: 250m
    # No persistent storage for the local testbed
    storageSpec: {}

alertmanager:
  enabled: true
  config:
    route:
      receiver: "null"
    receivers:
      - name: "null"

grafana:
  service:
    type: NodePort
    nodePort: 3000
  persistence:
    enabled: false
  adminPassword: "aegisops-admin"   # Change in your local copy; never commit real secrets
  # Pre-wire data sources so Grafana is usable immediately
  additionalDataSources:
    - name: Loki
      type: loki
      url: http://loki-gateway.observability.svc.cluster.local:80
      access: proxy
    - name: Tempo
      type: tempo
      url: http://tempo.observability.svc.cluster.local:3200
      access: proxy
```

**Why `storageSpec: {}`?** By default, Prometheus tries to create a PVC. On a Kind cluster without a default StorageClass, this PVC will stay `Pending` forever . Explicitly setting `storageSpec: {}` disables this, which is the correct choice for an ephemeral testbed. You are trading durability for reproducibility—acceptable for research experiments where you re-run from scratch.

#### 3.2 Loki (`infra/helm/loki.yaml`)

As of March 2026, the Loki Helm chart is maintained in the **`grafana-community/helm-charts`** repository, and the monolithic (single-binary) deployment mode is recommended for testing and development .

```yaml
# infra/helm/loki.yaml
deploymentMode: Monolithic
loki:
  commonConfig:
    replication_factor: 1
  auth_enabled: false
  storage:
    type: filesystem
  schemaConfig:
    configs:
      - from: "2024-04-01"
        store: tsdb
        object_store: filesystem
        schema: v13
        index:
          prefix: loki_index_
          period: 24h
  limits_config:
    allow_structured_metadata: true
    volume_enabled: true
  ruler:
    enable_api: true

# Disable the deprecated MinIO subchart; use filesystem storage for local testing
minio:
  enabled: false
ignoreMinioDeprecation: true

# Expose Loki's gateway for Grafana access
gateway:
  service:
    type: NodePort
    nodePort: 3100
```

The critical settings here are `replication_factor: 1` (required for a single replica) and `auth_enabled: false` (appropriate for a local, trusted cluster) . The `filesystem` storage backend is the simplest option for a testbed that does not need durable log retention across cluster rebuilds.

#### 3.3 Tempo (`infra/helm/tempo.yaml`)

Tempo stores distributed traces. The **monolithic chart** (`grafana-community/tempo`) runs everything in a single process, which is ideal for local development . For trace storage, use the **local filesystem backend**—no object storage required for the testbed .

```yaml
# infra/helm/tempo.yaml
tempo:
  retention: 24h
  storage:
    trace:
      backend: local
      local:
        path: /var/tempo/traces
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318
  # Optional: enable metrics generator for trace-derived RED metrics
  metricsGenerator:
    enabled: true
    remoteWriteUrl: "http://prometheus-kube-prometheus-prometheus.observability.svc.cluster.local:9090/api/v1/write"

service:
  type: NodePort
  nodePort: 3200
```

The `metricsGenerator` is a small but powerful addition: it derives **span metrics** (request rate, error rate, duration) from traces and remote-writes them to Prometheus. This means your Prometheus instance will have both cluster metrics *and* application-level RED metrics, giving your future RCA agent a richer signal set from day one.

---

### 4. The Makefile — Orchestrating the Entire Flow

The `Makefile` is the user-facing interface for the entire testbed. It must be **idempotent**, **fail-fast**, and **self-documenting**.

```makefile
# Makefile (relevant excerpt)
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

KIND_CLUSTER_NAME ?= aegisops
KIND_CONFIG       := infra/kind/cluster.yaml
OBS_NAMESPACE     := observability
HELM_DIR          := infra/helm

.PHONY: help preflight up down status

help: ## Show this help
	@echo "AegisOps Testbed"
	@echo "================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

preflight: ## Check required tools are installed
	@bash scripts/preflight.sh

up: preflight ## Spin up Kind cluster + full observability stack
	@echo "==> [1/4] Creating Kind cluster..."
	@if kind get clusters 2>/dev/null | grep -qx "$(KIND_CLUSTER_NAME)"; then \
		echo "  Cluster '$(KIND_CLUSTER_NAME)' already exists — skipping creation."; \
	else \
		kind create cluster --name "$(KIND_CLUSTER_NAME)" --config "$(KIND_CONFIG)"; \
	fi
	@echo "==> [2/4] Adding Helm repositories..."
	@helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
	@helm repo add grafana-community https://grafana-community.github.io/helm-charts
	@helm repo update
	@echo "==> [3/4] Installing observability stack..."
	@helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
		--namespace $(OBS_NAMESPACE) --create-namespace \
		--values $(HELM_DIR)/prometheus-stack.yaml --wait --timeout 10m
	@helm upgrade --install loki grafana-community/loki \
		--namespace $(OBS_NAMESPACE) \
		--values $(HELM_DIR)/loki.yaml --wait --timeout 5m
	@helm upgrade --install tempo grafana-community/tempo \
		--namespace $(OBS_NAMESPACE) \
		--values $(HELM_DIR)/tempo.yaml --wait --timeout 5m
	@echo "==> [4/4] Verifying stack health..."
	@bash scripts/wait-for-observability.sh
	@echo ""
	@echo "✅ AegisOps testbed is ready."
	@echo "   Grafana:    http://localhost:3000  (admin / aegisops-admin)"
	@echo "   Prometheus: http://localhost:9090"
	@echo "   Loki:       http://localhost:3100"
	@echo "   Tempo:      http://localhost:3200"

down: ## Tear down the cluster and all resources
	@echo "==> Deleting Kind cluster '$(KIND_CLUSTER_NAME)'..."
	@kind delete cluster --name "$(KIND_CLUSTER_NAME)"
	@echo "✅ Cluster deleted."

status: ## Show pod status in the observability namespace
	@kubectl get pods -n $(OBS_NAMESPACE) -o wide
```

**Critical detail:** The `up` target checks whether the cluster already exists before creating it. This makes the target idempotent—running `make up` twice does not fail or duplicate resources. The `--wait` flag on each `helm upgrade --install` blocks until the release is ready, so the verification step that follows is meaningful .

---

### 5. The Verification Script (`scripts/wait-for-observability.sh`)

Helm's `--wait` is a good first check, but a research testbed needs a **stricter health assertion**. This script should:

1.  Verify all pods in the `observability` namespace are `Running` or `Completed`.
2.  Query Prometheus's `/-/ready` endpoint.
3.  Query Loki's `/ready` endpoint.
4.  Query Tempo's `/ready` endpoint.

```bash
#!/usr/bin/env bash
# scripts/wait-for-observability.sh
set -euo pipefail

NAMESPACE="${OBS_NAMESPACE:-observability}"
TIMEOUT=300
INTERVAL=5
ELAPSED=0

echo "Waiting for observability pods to become ready..."

while true; do
  NOT_READY=$(kubectl get pods -n "$NAMESPACE" \
    --field-selector=status.phase!=Running,status.phase!=Succeeded \
    --no-headers 2>/dev/null | wc -l)

  if [[ "$NOT_READY" -eq 0 ]]; then
    echo "All pods are ready."
    break
  fi

  if [[ "$ELAPSED" -ge "$TIMEOUT" ]]; then
    echo "ERROR: Timed out waiting for pods after ${TIMEOUT}s."
    kubectl get pods -n "$NAMESPACE"
    exit 1
  fi

  echo "  ${NOT_READY} pod(s) not ready yet... (${ELAPSED}s elapsed)"
  sleep "$INTERVAL"
  ELAPSED=$((ELAPSED + INTERVAL))
done

# Functional readiness checks
echo "Checking Prometheus readiness..."
curl -sf http://localhost:9090/-/ready || { echo "Prometheus not ready"; exit 1; }

echo "Checking Loki readiness..."
curl -sf http://localhost:3100/ready || { echo "Loki not ready"; exit 1; }

echo "Checking Tempo readiness..."
curl -sf http://localhost:3200/ready || { echo "Tempo not ready"; exit 1; }

echo "All observability components are healthy."
```

This script is what transforms `make up` from "the command finished without errors" to "the testbed is actually functional." It is the single most important quality gate for reproducibility.

---

### 6. What Success Looks Like

After running `make up`, you should be able to:

- Open `http://localhost:3000` and log into Grafana with `admin` / `aegisops-admin`.
- See **Prometheus** as a pre-configured data source, with cluster metrics already populating.
- See **Loki** as a data source, and query logs from the `observability` namespace.
- See **Tempo** as a data source, ready to receive traces once your sample application is instrumented.
- Run `make status` and see all pods in `Running` state.

This completes the first deliverable of your Phase 1 roadmap: a reproducible, one-command testbed that any researcher can spin up from a fresh clone. The next step will build on this by deploying the sample application and defining the telemetry normalization schema that your Aegis agents will consume.