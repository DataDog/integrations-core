#!/bin/bash
set -euo pipefail

REPO=$(cd "$(dirname "$0")/.." && pwd)

export BOUNDARY_VERSION=0.8
export COCKROACHDB_VERSION=v23.2.2
export COCKROACHDB_START_COMMAND=start-single-node
export KONG_VERSION=3.0.0
export KRAKEND_VERSION=2.10
export N8N_VERSION=1.118.1
export PULSAR_VERSION=2.9.1
export RAY_VERSION=2.8.1
export TEMPORAL_VERSION=1.19.1

export DD_LOG_1=/dev/null
export SERVE_PORT=19001
export HEAD_METRICS_PORT=19090
export HEAD_DASHBOARD_PORT=19265
export WORKER1_METRICS_PORT=19086
export WORKER2_METRICS_PORT=19087
export WORKER3_METRICS_PORT=19088
export RAY_LOG_FOLDER=/tmp
export TEMPORAL_LOG_FOLDER=/tmp

# docker stop dd-agent-foo 2>/dev/null || true
# docker rm dd-agent-foo 2>/dev/null || true

docker compose -f "$REPO/boundary/tests/docker/docker-compose.yaml" -p demo-boundary down --volumes
docker compose -f "$REPO/cockroachdb/tests/docker/docker-compose.yaml" -p demo-cockroachdb down --volumes
docker compose -f "$REPO/kong/tests/compose/docker-compose.yml" -p demo-kong down --volumes
docker compose -f "$REPO/demo/compose/krakend.yaml" -p demo-krakend down --volumes
docker compose -f "$REPO/n8n/tests/docker/docker-compose.yaml" -p demo-n8n down --volumes
docker compose -f "$REPO/demo/compose/pulsar.yaml" -p demo-pulsar down --volumes
docker compose -f "$REPO/demo/compose/ray.yaml" -p demo-ray down --volumes
docker compose -f "$REPO/demo/compose/temporal.yaml" -p demo-temporal down --volumes

rm -rf "$REPO/demo/.runtime"
