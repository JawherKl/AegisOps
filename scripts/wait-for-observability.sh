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

echo "Checking Prometheus readiness..."
curl -sf http://localhost:30090/-/ready || { echo "Prometheus not ready"; exit 1; }

echo "Checking Loki readiness..."
# 1. Wait for the Loki gateway Deployment to be fully available
kubectl wait --for=condition=Available deployment/loki-gateway \
  -n "$NAMESPACE" --timeout=120s

# 2. Run a short-lived Job to confirm the gateway responds (using a supported path)
#    The gateway root "/" returns 200 when healthy.
kubectl delete job loki-ready-check -n "$NAMESPACE" --ignore-not-found
kubectl apply -n "$NAMESPACE" -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: loki-ready-check
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: curl
          image: curlimages/curl:8.6.0
          command: ["sh", "-c", "curl -sS -o /dev/null -w '%{http_code}' http://loki-gateway.${NAMESPACE}.svc.cluster.local/ | grep -q '^200$'"]
EOF

# 3. Wait for the Job to complete successfully
if kubectl wait --for=condition=complete job/loki-ready-check -n "$NAMESPACE" --timeout=60s; then
  echo "Loki gateway is ready."
  kubectl delete job loki-ready-check -n "$NAMESPACE" --ignore-not-found
else
  echo "Loki gateway readiness check failed."
  kubectl logs -n "$NAMESPACE" job/loki-ready-check --tail=20 || true
  kubectl delete job loki-ready-check -n "$NAMESPACE" --ignore-not-found
  exit 1
fi

echo "Checking Tempo readiness..."
# 1. Wait for the Tempo pod to report Ready
kubectl wait --for=condition=Ready pod \
  -l app.kubernetes.io/name=tempo \
  -n "$NAMESPACE" --timeout=180s

# 2. Run a short-lived Job to query Tempo's /ready endpoint from inside the cluster
kubectl delete job tempo-ready-check -n "$NAMESPACE" --ignore-not-found
kubectl apply -n "$NAMESPACE" -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: tempo-ready-check
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: curl
          image: curlimages/curl:8.6.0
          command: ["sh", "-c", "curl -sS -o /dev/null -w '%{http_code}' http://tempo.${NAMESPACE}.svc.cluster.local:3200/ready | grep -q '^200$'"]
EOF

# 3. Wait for the Job to complete successfully
if kubectl wait --for=condition=complete job/tempo-ready-check -n "$NAMESPACE" --timeout=60s; then
  echo "Tempo is ready."
  kubectl delete job tempo-ready-check -n "$NAMESPACE" --ignore-not-found
else
  echo "Tempo readiness check failed."
  kubectl logs -n "$NAMESPACE" job/tempo-ready-check --tail=20 || true
  kubectl delete job tempo-ready-check -n "$NAMESPACE" --ignore-not-found
  exit 1
fi

echo "All observability components are healthy."