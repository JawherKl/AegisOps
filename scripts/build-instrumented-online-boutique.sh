#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTRUMENTATION_DIR="$ROOT_DIR/infra/apps/online-boutique/instrumentation"
IMAGE_DIR="$INSTRUMENTATION_DIR/images"
KIND_CLUSTER_NAME="${KIND_CLUSTER_NAME:-aegisops}"
UPSTREAM_REF="v0.10.7"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/aegisops-online-boutique.XXXXXX")"
UPSTREAM_DIR="$WORK_DIR/microservices-demo"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

if ! kind get clusters | grep -Fxq "$KIND_CLUSTER_NAME"; then
  echo "Kind cluster '$KIND_CLUSTER_NAME' does not exist. Run 'make up' first." >&2
  exit 1
fi

echo "==> Cloning Online Boutique $UPSTREAM_REF for instrumented source builds..."
git clone --depth 1 --branch "$UPSTREAM_REF" --single-branch \
  https://github.com/GoogleCloudPlatform/microservices-demo.git "$UPSTREAM_DIR"

echo "==> Applying cartservice and shippingservice tracing patches..."
git -C "$UPSTREAM_DIR" apply "$INSTRUMENTATION_DIR/cartservice.patch"
git -C "$UPSTREAM_DIR" apply "$INSTRUMENTATION_DIR/shippingservice.patch"
cp "$INSTRUMENTATION_DIR/shippingservice-otel.go" \
  "$UPSTREAM_DIR/src/shippingservice/otel.go"

echo "==> Building instrumented images..."
docker build \
  -f "$IMAGE_DIR/Dockerfile.adservice" \
  -t aegisops/adservice:v0.10.7-otel \
  "$IMAGE_DIR"
docker build \
  -f "$IMAGE_DIR/Dockerfile.loadgenerator" \
  -t aegisops/loadgenerator:v0.10.7-otel \
  "$IMAGE_DIR"
docker build \
  -t aegisops/cartservice:v0.10.7-otel \
  "$UPSTREAM_DIR/src/cartservice/src"
docker build \
  -t aegisops/shippingservice:v0.10.7-otel \
  -f "$IMAGE_DIR/Dockerfile.shippingservice" \
  "$UPSTREAM_DIR/src/shippingservice"

echo "==> Loading instrumented images into Kind cluster '$KIND_CLUSTER_NAME'..."
kind load docker-image \
  aegisops/adservice:v0.10.7-otel \
  aegisops/cartservice:v0.10.7-otel \
  aegisops/loadgenerator:v0.10.7-otel \
  aegisops/shippingservice:v0.10.7-otel \
  --name "$KIND_CLUSTER_NAME"
