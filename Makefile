SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

KIND_CLUSTER_NAME ?= aegisops
KIND_CONFIG       := infra/kind/cluster.yaml
OBS_NAMESPACE     := observability
HELM_DIR          := infra/helm

.PHONY: help preflight up down status verify-otel-env build-instrumented-app deploy-app

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
	@helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
	@helm repo update
	@echo "==> [3/4] Installing observability stack..."
	@helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
		--namespace $(OBS_NAMESPACE) --create-namespace \
		--values $(HELM_DIR)/prometheus-stack.yaml --wait --timeout 15m
	@helm upgrade --install loki grafana-community/loki \
		--namespace $(OBS_NAMESPACE) \
		--values $(HELM_DIR)/loki-stack.yaml --wait --timeout 5m
	@helm upgrade --install tempo grafana-community/tempo \
		--namespace $(OBS_NAMESPACE) \
		--values $(HELM_DIR)/tempo.yaml --wait --timeout 5m
	@echo "==> Installing OpenTelemetry Collector..."
	@helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
		--namespace $(OBS_NAMESPACE) \
		--values $(HELM_DIR)/otel-collector.yaml --wait --timeout 10m
	@echo "==> [4/4] Verifying stack health..."
	@bash scripts/wait-for-observability.sh
	@echo ""
	@echo "✅ AegisOps testbed is ready."
	@echo "   Grafana:    http://localhost:30300  (admin / aegisops-admin)"
	@echo "   Prometheus: http://localhost:30090"
	@echo "   Loki:       http://localhost:30310"
	@echo "   Tempo:      http://localhost:30320"

down: ## Tear down the cluster and all resources
	@echo "==> Deleting Kind cluster '$(KIND_CLUSTER_NAME)'..."
	@kind delete cluster --name "$(KIND_CLUSTER_NAME)"
	@echo "✅ Cluster deleted."

status: ## Show pod status in the observability namespace
	@kubectl get pods -n $(OBS_NAMESPACE) -o wide

verify-otel-env: ## Show OTEL env vars on the frontend deployment and running pod
	@echo "=== Deployment spec ==="
	@kubectl get deploy frontend -n online-boutique \
	  -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}' \
	  | grep -E 'OTEL|TRACING|COLLECTOR' || echo "  (none found)"
	@echo
	@echo "=== Running pod spec ==="
	@kubectl get pods -n online-boutique -l app=frontend \
	  -o jsonpath='{range .items[0].spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}' \
	  | grep -E 'OTEL|TRACING|COLLECTOR' || echo "  (none found)"

build-instrumented-app: preflight ## Build and load traced Online Boutique images into Kind
	@KIND_CLUSTER_NAME="$(KIND_CLUSTER_NAME)" bash scripts/build-instrumented-online-boutique.sh

deploy-app: build-instrumented-app ## Build traced images and deploy Online Boutique
	@kubectl create namespace online-boutique --dry-run=client -o yaml | kubectl apply -f -
	@kubectl apply -n online-boutique -f infra/apps/online-boutique/online-boutique.yaml

doctor: ## Verify environment, files, services, and CLI entry points
	@echo "=== Python ==="
	@python --version
	@echo "=== Required modules ==="
	@python -c "import pydantic; print('  pydantic OK')"  || echo "  pydantic MISSING"
	@python -c "import ollama; print('  ollama OK')"      || echo "  ollama MISSING"
	@python -c "import httpx; print('  httpx OK')"        || echo "  httpx MISSING"
	@echo "=== Package files ==="
	@for f in \
	  src/aegisops/llm/base.py \
	  src/aegisops/llm/ollama_provider.py \
	  src/aegisops/agents/rca/agent.py \
	  src/aegisops/agents/rca/prompts.py \
	  src/aegisops/cli/collect.py \
	  src/aegisops/cli/rca.py \
	; do \
	  test -f "$$f" && echo "  OK      $$f" || echo "  MISSING $$f"; \
	done
	@echo "=== CLI entry points ==="
	@which aegisops-collect >/dev/null && echo "  aegisops-collect OK" || echo "  aegisops-collect MISSING"
	@which aegisops-rca     >/dev/null && echo "  aegisops-rca OK"     || echo "  aegisops-rca MISSING"
	@echo "=== Services ==="
	@curl -sf http://localhost:11434/api/tags >/dev/null && echo "  ollama server OK" || echo "  ollama server NOT RESPONDING"
	@curl -sf http://localhost:30090/-/ready  >/dev/null && echo "  prometheus OK"    || echo "  prometheus NOT READY"
	@curl -sf http://localhost:30310/ready    >/dev/null && echo "  loki OK"          || echo "  loki NOT READY"
