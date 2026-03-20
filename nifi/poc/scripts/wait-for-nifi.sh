#!/usr/bin/env bash
# ABOUTME: Polls the NiFi REST API until it becomes available.
# ABOUTME: Exits 0 on success, 1 on timeout.

set -euo pipefail

NIFI_API_URL="${NIFI_API_URL:-https://localhost:8443/nifi-api}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-60}"
SLEEP_INTERVAL="${SLEEP_INTERVAL:-5}"

echo "Waiting for NiFi at ${NIFI_API_URL}/flow/about ..."

for i in $(seq 1 "$MAX_ATTEMPTS"); do
    http_code=$(curl -sk -o /dev/null -w '%{http_code}' "${NIFI_API_URL}/flow/about" 2>/dev/null || echo "000")
    if [ "$http_code" != "000" ] && [ "$http_code" != "" ]; then
        echo "NiFi is ready (attempt ${i}/${MAX_ATTEMPTS})"
        exit 0
    fi
    echo "  Attempt ${i}/${MAX_ATTEMPTS} — not ready yet, waiting ${SLEEP_INTERVAL}s..."
    sleep "$SLEEP_INTERVAL"
done

echo "ERROR: NiFi did not become ready after $((MAX_ATTEMPTS * SLEEP_INTERVAL))s"
exit 1
