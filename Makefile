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
		--values $(HELM_DIR)/prometheus-stack.yaml --wait --timeout 15m
	@helm upgrade --install loki grafana-community/loki \
		--namespace $(OBS_NAMESPACE) \
		--values $(HELM_DIR)/loki-stack.yaml --wait --timeout 5m
	@helm upgrade --install tempo grafana-community/tempo \
		--namespace $(OBS_NAMESPACE) \
		--values $(HELM_DIR)/tempo.yaml --wait --timeout 5m
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