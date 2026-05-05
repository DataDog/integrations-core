#!/bin/bash
set -euo pipefail

REPO=$(cd "$(dirname "$0")/.." && pwd)

SITE_PACKAGES=/opt/datadog-agent/embedded/lib/python3.13/site-packages
CONF_D=/etc/datadog-agent/conf.d

~/hacks/bin/docker-agent-run.sh \
  --network host \
  -d \
  -e DD_LOG_LEVEL=info \
  -e DD_HOSTNAME=demo-new \
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
