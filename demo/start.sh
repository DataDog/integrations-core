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

~/hacks/bin/docker-agent-run.sh \
  --network host \
  -d \
  -e DD_LOG_LEVEL=info \
  -v "$REPO/boundary/datadog_checks/boundary/data/auto_conf_discovery.yaml:$CONF_D/boundary.d/auto_conf_discovery.yaml:ro" \
  -v "$REPO/boundary/datadog_checks/boundary:$SITE_PACKAGES/datadog_checks/boundary:ro" \
  -v "$REPO/cockroachdb/datadog_checks/cockroachdb/data/auto_conf_discovery.yaml:$CONF_D/cockroachdb.d/auto_conf_discovery.yaml:ro" \
  -v "$REPO/cockroachdb/datadog_checks/cockroachdb:$SITE_PACKAGES/datadog_checks/cockroachdb:ro" \
  -v "$REPO/kong/datadog_checks/kong/data/auto_conf_discovery.yaml:$CONF_D/kong.d/auto_conf_discovery.yaml:ro" \
  -v "$REPO/kong/datadog_checks/kong:$SITE_PACKAGES/datadog_checks/kong:ro" \
  -v "$REPO/krakend/datadog_checks/krakend/data/auto_conf_discovery.yaml:$CONF_D/krakend.d/auto_conf_discovery.yaml:ro" \
  -v "$REPO/krakend/datadog_checks/krakend:$SITE_PACKAGES/datadog_checks/krakend:ro" \
  -v "$REPO/n8n/datadog_checks/n8n/data/auto_conf_discovery.yaml:$CONF_D/n8n.d/auto_conf_discovery.yaml:ro" \
  -v "$REPO/n8n/datadog_checks/n8n:$SITE_PACKAGES/datadog_checks/n8n:ro" \
  -v "$REPO/pulsar/datadog_checks/pulsar/data/auto_conf_discovery.yaml:$CONF_D/pulsar.d/auto_conf_discovery.yaml:ro" \
  -v "$REPO/pulsar/datadog_checks/pulsar:$SITE_PACKAGES/datadog_checks/pulsar:ro" \
  -v "$REPO/ray/datadog_checks/ray/data/auto_conf_discovery.yaml:$CONF_D/ray.d/auto_conf_discovery.yaml:ro" \
  -v "$REPO/ray/datadog_checks/ray:$SITE_PACKAGES/datadog_checks/ray:ro" \
  -v "$REPO/temporal/datadog_checks/temporal/data/auto_conf_discovery.yaml:$CONF_D/temporal.d/auto_conf_discovery.yaml:ro" \
  -v "$REPO/temporal/datadog_checks/temporal:$SITE_PACKAGES/datadog_checks/temporal:ro" \
  -v "$REPO/datadog_checks_base/datadog_checks/base/utils/discovery:$SITE_PACKAGES/datadog_checks/base/utils/discovery:ro" \
  -v "$REPO/datadog_checks_base/datadog_checks/base/checks/openmetrics/v2/base.py:$SITE_PACKAGES/datadog_checks/base/checks/openmetrics/v2/base.py:ro" \
  datadog/agent-dev:discovery-local

echo "Agent started. Waiting 30s for discovery..."
sleep 30

docker exec dd-agent-foo agent status 2>&1 | grep -A 3 "Running Checks\|discovery\|boundary\|cockroachdb\|kong\|krakend\|n8n\|pulsar\|ray\|temporal" | head -80
