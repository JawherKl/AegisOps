#!/usr/bin/env python3
"""
Patch the upstream Online Boutique manifest to inject OpenTelemetry
environment variables, so all microservices export traces to the
AegisOps OTEL Collector.

Reproducible: re-run this script any time you re-download the upstream
manifest. It is idempotent — services that already have the OTEL env
vars will not be duplicated.
"""
from pathlib import Path
from ruamel.yaml import YAML

MANIFEST = Path("infra/apps/online-boutique/online-boutique.yaml")

OTEL_COLLECTOR_ENDPOINT = (
    "http://otel-collector.observability.svc.cluster.local:4317"
)

# Services that ship OTEL-instrumented binaries. redis-cart is intentionally
# excluded: it is a stock Redis image with no tracing support.
INSTRUMENTED_SERVICES = {
    "adservice", "shippingservice", "checkoutservice", "currencyservice",
    "emailservice", "productcatalogservice", "frontend",
    "recommendationservice", "loadgenerator", "cartservice", "paymentservice",
}

def build_env_for(service_name: str) -> list[dict]:
    return [
        # Online Boutique-specific tracing activation
        {"name": "ENABLE_TRACING", "value": "1"},
        {
            "name": "COLLECTOR_SERVICE_ADDR",
            "value": "otel-collector.observability.svc.cluster.local:4317",
        },
        # Standard OTEL configuration
        {
            "name": "OTEL_EXPORTER_OTLP_ENDPOINT",
            "value": "http://otel-collector.observability.svc.cluster.local:4317",
        },
        {"name": "OTEL_EXPORTER_OTLP_PROTOCOL", "value": "grpc"},
        {"name": "OTEL_SERVICE_NAME", "value": service_name},
        {
            "name": "OTEL_RESOURCE_ATTRIBUTES",
            "value": "service.namespace=online-boutique,deployment.environment=testbed",
        },
    ]


def main() -> None:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    with MANIFEST.open("r") as f:
        docs = list(yaml.load_all(f))

    patched = 0
    for doc in docs:
        if not doc or doc.get("kind") != "Deployment":
            continue
        name = doc.get("metadata", {}).get("name")
        if name not in INSTRUMENTED_SERVICES:
            continue

        # Only patch the main containers, NOT initContainers
        for container in doc["spec"]["template"]["spec"]["containers"]:
            env = container.setdefault("env", [])
            existing_names = {e["name"] for e in env}
            for entry in build_env_for(name):
                if entry["name"] not in existing_names:
                    env.append(entry)
        patched += 1
        print(f"  ✓ patched deployment/{name}")

    with MANIFEST.open("w") as f:
        yaml.dump_all(docs, f)

    print(f"\nDone. Patched {patched} deployments in {MANIFEST}.")


if __name__ == "__main__":
    main()