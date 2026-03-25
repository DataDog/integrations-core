#!/usr/bin/env bash
# One-shot bootstrap: schema, offline table, batch segments (baseballStats) for distributed E2E.
set -euo pipefail

ADMIN=/opt/pinot/bin/pinot-admin.sh
SCHEMA=/opt/pinot/examples/batch/baseballStats/baseballStats_schema.json
OFFLINE_TABLE=/opt/pinot/examples/batch/baseballStats/baseballStats_offline_table_config.json
JOB_SPEC=/bootstrap/baseball_stats_e2e_ingestion.yaml
CTRL="http://pinot-controller:9000"

until curl -sf "${CTRL}/health" >/dev/null; do
  echo "bootstrap: waiting for pinot-controller..."
  sleep 2
done

# Pinot 1.4.x AddTable CLI can return misleading errors; REST matches QuickStart behavior.
curl -sf -X POST "${CTRL}/schemas" -H "Content-Type: application/json" -d @"${SCHEMA}" || true
curl -sf -X POST "${CTRL}/tables" -H "Content-Type: application/json" -d @"${OFFLINE_TABLE}" || true

for _ in $(seq 1 90); do
  if curl -sf "${CTRL}/tables/baseballStats" | grep -q OFFLINE; then
    break
  fi
  sleep 2
done
if ! curl -sf "${CTRL}/tables/baseballStats" | grep -q OFFLINE; then
  echo "bootstrap: timed out waiting for baseballStats OFFLINE table in controller" >&2
  exit 1
fi

cd /opt/pinot
if ! "$ADMIN" LaunchDataIngestionJob -jobSpec="$JOB_SPEC"; then
  echo "bootstrap: LaunchDataIngestionJob failed" >&2
  exit 1
fi

echo "Bootstrap complete: baseballStats table and segments loaded"
