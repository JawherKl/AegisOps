#!/usr/bin/env bash
# Verifies that all tools required to bootstrap the AegisOps testbed are present.
set -euo pipefail

# --- Configuration -----------------------------------------------------------
MIN_DOCKER_MAJOR=20
MIN_KIND_VERSION="0.20.0"
MIN_KUBECTL_VERSION="1.27.0"
MIN_HELM_MAJOR=3

# --- Colors ------------------------------------------------------------------
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
BLUE=$'\033[0;34m'
RESET=$'\033[0m'

# --- Helpers -----------------------------------------------------------------
failures=0

ok()   { printf "  ${GREEN}✔${RESET} %s\n" "$1"; }
warn() { printf "  ${YELLOW}!${RESET} %s\n" "$1"; }
fail() { printf "  ${RED}✘${RESET} %s\n" "$1"; failures=$((failures + 1)); }
info() { printf "${BLUE}%s${RESET}\n" "$1"; }

# Compare two semver-ish strings: returns 0 if $1 >= $2
version_ge() {
  # shellcheck disable=SC2206
  local IFS=.
  local i ver1=($1) ver2=($2)
  # Pad with zeros to equal length
  for ((i=${#ver1[@]}; i<${#ver2[@]}; i++)); do ver1[i]=0; done
  for ((i=0; i<${#ver1[@]}; i++)); do
    if ((10#${ver1[i]:-0} > 10#${ver2[i]:-0})); then return 0; fi
    if ((10#${ver1[i]:-0} < 10#${ver2[i]:-0})); then return 1; fi
  done
  return 0
}

has() { command -v "$1" >/dev/null 2>&1; }

# --- 1. Docker ---------------------------------------------------------------
info "Checking Docker..."
if has docker; then
  if docker info >/dev/null 2>&1; then
    docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0.0.0")
    docker_major=${docker_version%%.*}
    if [[ "$docker_major" -ge "$MIN_DOCKER_MAJOR" ]]; then
      ok "docker ${docker_version}"
    else
      fail "docker ${docker_version} is too old (need >= ${MIN_DOCKER_MAJOR}.0)"
    fi
  else
    fail "docker is installed but the daemon is not running (start Docker Desktop)"
  fi
else
  fail "docker not found — install Docker Desktop or Docker Engine"
fi

# --- 2. kind -----------------------------------------------------------------
info "Checking kind..."
if has kind; then
  kind_version=$(kind version 2>/dev/null | awk '{print $2}' | sed 's/^v//')
  if version_ge "${kind_version:-0.0.0}" "$MIN_KIND_VERSION"; then
    ok "kind v${kind_version}"
  else
    fail "kind v${kind_version} is too old (need >= v${MIN_KIND_VERSION})"
  fi
else
  fail "kind not found — install from https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
fi

# --- 3. kubectl --------------------------------------------------------------
info "Checking kubectl..."
if has kubectl; then
  # client version only — we don't have a cluster yet
  kubectl_version=$(kubectl version --client=true -o json 2>/dev/null \
    | grep -o '"gitVersion": *"v[^"]*"' | head -1 \
    | sed -E 's/.*"v([^"]+)".*/\1/')
  if [[ -z "${kubectl_version:-}" ]]; then
    # Fallback for older kubectl
    kubectl_version=$(kubectl version --client=true 2>/dev/null \
      | grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1 | sed 's/^v//')
  fi
  if version_ge "${kubectl_version:-0.0.0}" "$MIN_KUBECTL_VERSION"; then
    ok "kubectl v${kubectl_version}"
  else
    fail "kubectl v${kubectl_version:-unknown} is too old (need >= v${MIN_KUBECTL_VERSION})"
  fi
else
  fail "kubectl not found — install from https://kubernetes.io/docs/tasks/tools/"
fi

# --- 4. helm -----------------------------------------------------------------
info "Checking helm..."
if has helm; then
  helm_version=$(helm version --short 2>/dev/null | sed -E 's/^v//; s/\+.*$//')
  helm_major=${helm_version%%.*}
  if [[ "${helm_major:-0}" -ge "$MIN_HELM_MAJOR" ]]; then
    ok "helm v${helm_version}"
  else
    fail "helm v${helm_version} is too old (need >= v${MIN_HELM_MAJOR}.0)"
  fi
else
  fail "helm not found — install from https://helm.sh/docs/intro/install/"
fi

# --- 5. curl (used by wait-for-observability.sh) -----------------------------
info "Checking curl..."
if has curl; then
  ok "curl $(curl --version | head -1 | awk '{print $2}')"
else
  fail "curl not found — required for readiness checks"
fi

# --- Summary -----------------------------------------------------------------
echo
if [[ "$failures" -gt 0 ]]; then
  printf "${RED}Preflight failed: %d problem(s) detected.${RESET}\n" "$failures"
  echo "Fix the items above and re-run 'make up'."
  exit 1
fi

printf "${GREEN}Preflight passed — all required tools are installed.${RESET}\n"
exit 0