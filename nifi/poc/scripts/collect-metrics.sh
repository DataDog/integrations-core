#!/usr/bin/env bash
# ABOUTME: Queries all NiFi monitoring endpoints and saves JSON responses.
# ABOUTME: Authenticates, then hits each endpoint the Agent integration will use.

set -euo pipefail

NIFI_API_URL="${NIFI_API_URL:-https://localhost:8443/nifi-api}"
NIFI_USERNAME="${NIFI_USERNAME:-admin}"
NIFI_PASSWORD="${NIFI_PASSWORD:-ctsBtRBKHRAx69EqUghvvgEvjnaLjFEB}"
OUTPUT_DIR="${1:-$(dirname "$0")/../responses}"

mkdir -p "$OUTPUT_DIR"

# --- Authenticate ---
echo "Authenticating..."
TOKEN_RESPONSE=$(mktemp)
HTTP_CODE=$(curl -sk -X POST "${NIFI_API_URL}/access/token" \
    -d "username=${NIFI_USERNAME}&password=${NIFI_PASSWORD}" \
    -o "$TOKEN_RESPONSE" -w '%{http_code}' 2>/dev/null || echo "000")
TOKEN=$(cat "$TOKEN_RESPONSE")
rm -f "$TOKEN_RESPONSE"

if [ "$HTTP_CODE" != "201" ] || [ -z "$TOKEN" ]; then
    echo "ERROR: Failed to obtain auth token (HTTP ${HTTP_CODE})"
    exit 1
fi

AUTH=(-sk -H "Authorization: Bearer ${TOKEN}")

# --- Collect each endpoint ---
FAILURES=0

collect() {
    local name="$1" path="$2"
    echo "  Collecting ${name}..."
    local http_code tmpfile
    tmpfile=$(mktemp)
    http_code=$(curl "${AUTH[@]}" -o "$tmpfile" -w '%{http_code}' "${NIFI_API_URL}${path}" 2>/dev/null || echo "000")
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        jq . "$tmpfile" > "${OUTPUT_DIR}/${name}.json" 2>/dev/null || mv "$tmpfile" "${OUTPUT_DIR}/${name}.json"
        rm -f "$tmpfile"
        local size
        size=$(wc -c < "${OUTPUT_DIR}/${name}.json" | tr -d ' ')
        echo "    ✓ ${name}.json (${size} bytes, HTTP ${http_code})"
    else
        rm -f "$tmpfile"
        echo "    ✗ ${name} failed (HTTP ${http_code})"
        FAILURES=$((FAILURES + 1))
    fi
}

echo ""
echo "Collecting API responses into ${OUTPUT_DIR}/"
echo ""

# 1. Version info (cached in real check)
collect "about" "/flow/about"

# 2. System diagnostics (JVM, GC, repos)
collect "system-diagnostics" "/system-diagnostics"

# 3. Flow status (controller summary)
collect "flow-status" "/flow/status"

# 4. Process group status (recursive — the key endpoint)
collect "process-group-recursive" "/flow/process-groups/root/status?recursive=true"

# 5. Cluster summary
collect "cluster-summary" "/flow/cluster/summary"

# 6. Bulletin board (errors/warnings)
collect "bulletin-board" "/flow/bulletin-board"

# 7. JMX metrics via REST (expected empty without config)
collect "jmx-metrics" "/system-diagnostics/jmx-metrics"

echo ""
echo "=== Summary ==="
echo ""

# Print key findings
echo "NiFi version:"
jq -r '.about.title + " " + .about.version' "${OUTPUT_DIR}/about.json" 2>/dev/null || echo "  (parse error)"

echo ""
echo "JVM heap:"
jq -r '"  Used: " + .systemDiagnostics.aggregateSnapshot.usedHeap + " / " + .systemDiagnostics.aggregateSnapshot.maxHeap + " (" + .systemDiagnostics.aggregateSnapshot.heapUtilization + ")"' "${OUTPUT_DIR}/system-diagnostics.json" 2>/dev/null || echo "  (parse error)"

echo ""
echo "Threads: "
jq -r '"  Total: " + (.systemDiagnostics.aggregateSnapshot.totalThreads | tostring) + ", Daemon: " + (.systemDiagnostics.aggregateSnapshot.daemonThreads | tostring)' "${OUTPUT_DIR}/system-diagnostics.json" 2>/dev/null || echo "  (parse error)"

echo ""
echo "Flow status:"
jq -r '"  Running: " + (.controllerStatus.runningCount | tostring) + ", Stopped: " + (.controllerStatus.stoppedCount | tostring) + ", Invalid: " + (.controllerStatus.invalidCount | tostring)' "${OUTPUT_DIR}/flow-status.json" 2>/dev/null || echo "  (parse error)"

echo ""
echo "Queued FlowFiles:"
jq -r '"  " + (.controllerStatus.flowFilesQueued | tostring) + " FlowFiles, " + (.controllerStatus.bytesQueued | tostring) + " bytes"' "${OUTPUT_DIR}/flow-status.json" 2>/dev/null || echo "  (parse error)"

echo ""
echo "Processors (from recursive status):"
jq -r '.processGroupStatus.aggregateSnapshot.processorStatusSnapshots[]? | .processorStatusSnapshot | "  " + .name + " (" + .type + "): " + .runStatus + ", tasks=" + (.taskCount | tostring)' "${OUTPUT_DIR}/process-group-recursive.json" 2>/dev/null || echo "  (none or parse error)"

echo ""
echo "Connections (from recursive status):"
jq -r '.processGroupStatus.aggregateSnapshot.connectionStatusSnapshots[]? | .connectionStatusSnapshot | "  " + .sourceName + " → " + .destinationName + ": queued=" + (.flowFilesQueued | tostring) + ", backpressure=" + (.percentUseCount | tostring) + "%"' "${OUTPUT_DIR}/process-group-recursive.json" 2>/dev/null || echo "  (none or parse error)"

echo ""
echo "Cluster:"
jq -r 'if .clusterSummary.clustered then "  Clustered: " + (.clusterSummary.connectedNodeCount | tostring) + "/" + (.clusterSummary.totalNodeCount | tostring) + " nodes connected" else "  Standalone mode" end' "${OUTPUT_DIR}/cluster-summary.json" 2>/dev/null || echo "  (parse error)"

echo ""
echo "Bulletins:"
BULLETIN_COUNT=$(jq '.bulletinBoard.bulletins | length' "${OUTPUT_DIR}/bulletin-board.json" 2>/dev/null || echo "0")
echo "  ${BULLETIN_COUNT} bulletin(s)"
if [ "$BULLETIN_COUNT" -gt 0 ]; then
    jq -r '.bulletinBoard.bulletins[:5][] | "  [" + .bulletin.level + "] " + .bulletin.sourceName + ": " + (.bulletin.message | .[0:120])' "${OUTPUT_DIR}/bulletin-board.json" 2>/dev/null
fi

echo ""
if [ "$FAILURES" -gt 0 ]; then
    echo "ERROR: ${FAILURES} endpoint(s) failed"
    exit 1
fi
echo "All responses saved to ${OUTPUT_DIR}/"
