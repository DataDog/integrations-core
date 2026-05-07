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

mkdir -p "$REPO/demo/.runtime"
touch "$REPO/demo/.runtime/boundary-events.ndjson"
touch "$REPO/demo/.runtime/pulsar.log"
mkdir -p "$REPO/demo/.runtime/ray-logs"
mkdir -p "$REPO/demo/.runtime/temporal-logs"
chmod 777 "$REPO/demo/.runtime/temporal-logs"

export RAY_LOG_FOLDER="$REPO/demo/.runtime/ray-logs"
export TEMPORAL_LOG_FOLDER="$REPO/demo/.runtime/temporal-logs"

export SERVE_PORT=19001
export HEAD_METRICS_PORT=19090
export HEAD_DASHBOARD_PORT=19265
export WORKER1_METRICS_PORT=19086
export WORKER2_METRICS_PORT=19087
export WORKER3_METRICS_PORT=19088

DD_LOG_1="$REPO/demo/.runtime/boundary-events.ndjson" \
  docker compose -f "$REPO/boundary/tests/docker/docker-compose.yaml" -p demo-boundary up -d --build --remove-orphans

docker compose -f "$REPO/cockroachdb/tests/docker/docker-compose.yaml" -p demo-cockroachdb up -d --build --remove-orphans

docker compose -f "$REPO/kong/tests/compose/docker-compose.yml" -p demo-kong up -d --build --remove-orphans

docker compose -f "$REPO/demo/compose/krakend.yaml" -p demo-krakend up -d --build --remove-orphans

docker compose -f "$REPO/n8n/tests/docker/docker-compose.yaml" -p demo-n8n up -d --build --remove-orphans

DD_LOG_1="$REPO/demo/.runtime/pulsar.log" \
  docker compose -f "$REPO/demo/compose/pulsar.yaml" -p demo-pulsar up -d --build --remove-orphans

docker compose -f "$REPO/demo/compose/ray.yaml" -p demo-ray up -d --remove-orphans

docker compose -f "$REPO/demo/compose/temporal.yaml" -p demo-temporal up -d --build --remove-orphans

echo "Services starting... waiting 60s for core services to be healthy"
sleep 60

SITE_PACKAGES=/opt/datadog-agent/embedded/lib/python3.13/site-packages
CONF_D=/etc/datadog-agent/conf.d

# ./agent.sh
# 
# echo "Agent started. Waiting 30s for discovery..."
# sleep 30
# 
# docker exec dd-agent-foo agent status 2>&1 | grep -A 3 "Running Checks\|discovery\|boundary\|cockroachdb\|kong\|krakend\|n8n\|pulsar\|ray\|temporal" | head -80
