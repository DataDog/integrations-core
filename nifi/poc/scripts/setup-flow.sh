#!/usr/bin/env bash
# ABOUTME: Creates a test flow in NiFi via the REST API.
# ABOUTME: Builds GenerateFlowFile→LogMessage (happy path) and GenerateFlowFile→PutFile /nonexistent (error bulletins).

set -euo pipefail

NIFI_API_URL="${NIFI_API_URL:-https://localhost:8443/nifi-api}"
NIFI_USERNAME="${NIFI_USERNAME:-admin}"
NIFI_PASSWORD="${NIFI_PASSWORD:-ctsBtRBKHRAx69EqUghvvgEvjnaLjFEB}"

# --- Authenticate ---
echo "Authenticating as ${NIFI_USERNAME}..."
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
echo "Got auth token (${#TOKEN} chars)"

AUTH=(-sk -H "Authorization: Bearer ${TOKEN}")

# --- Helper: validate an ID looks like a UUID ---
require_id() {
    local label="$1" value="$2"
    if [ -z "$value" ] || [ "$value" = "null" ]; then
        echo "ERROR: Failed to get ${label}"
        exit 1
    fi
}

# --- Get root process group ID ---
ROOT_PG_ID=$(curl "${AUTH[@]}" "${NIFI_API_URL}/flow/process-groups/root/status" \
    | jq -r '.processGroupStatus.id')
require_id "root process group ID" "$ROOT_PG_ID"
echo "Root process group: ${ROOT_PG_ID}"

# --- Helper: create a processor ---
NEXT_X=100
NEXT_Y=100

create_processor() {
    local name="$1" type="$2" scheduling="$3" props="$4" auto_term="$5"
    local x=$NEXT_X y=$NEXT_Y

    local config="{\"schedulingPeriod\": \"${scheduling}\", \"properties\": ${props}"
    if [ -n "$auto_term" ]; then
        config="${config}, \"autoTerminatedRelationships\": ${auto_term}"
    fi
    config="${config}}"

    curl "${AUTH[@]}" -X POST \
        "${NIFI_API_URL}/process-groups/${ROOT_PG_ID}/processors" \
        -H "Content-Type: application/json" \
        -d "{
            \"revision\": {\"version\": 0},
            \"component\": {
                \"type\": \"org.apache.nifi.processors.standard.${type}\",
                \"name\": \"${name}\",
                \"position\": {\"x\": ${x}, \"y\": ${y}},
                \"config\": ${config}
            }
        }" | jq -r '.id'

    NEXT_X=$((NEXT_X + 400))
}

# --- Helper: create a connection ---
create_connection() {
    local source_id="$1" dest_id="$2" relationships="$3"

    curl "${AUTH[@]}" -X POST \
        "${NIFI_API_URL}/process-groups/${ROOT_PG_ID}/connections" \
        -H "Content-Type: application/json" \
        -d "{
            \"revision\": {\"version\": 0},
            \"component\": {
                \"source\": {\"id\": \"${source_id}\", \"groupId\": \"${ROOT_PG_ID}\", \"type\": \"PROCESSOR\"},
                \"destination\": {\"id\": \"${dest_id}\", \"groupId\": \"${ROOT_PG_ID}\", \"type\": \"PROCESSOR\"},
                \"selectedRelationships\": ${relationships}
            }
        }" | jq -r '.id'
}

# --- Helper: start a processor ---
start_processor() {
    local proc_id="$1"
    local ver
    ver=$(curl "${AUTH[@]}" "${NIFI_API_URL}/processors/${proc_id}" | jq -r '.revision.version')
    curl "${AUTH[@]}" -X PUT "${NIFI_API_URL}/processors/${proc_id}/run-status" \
        -H "Content-Type: application/json" \
        -d "{\"revision\": {\"version\": ${ver}}, \"state\": \"RUNNING\"}" > /dev/null
}

# --- Happy path: GenerateFlowFile → LogMessage ---
echo ""
echo "Creating happy-path flow: GenerateFlowFile → LogMessage"

GEN_ID=$(create_processor "Generate Test Data" "GenerateFlowFile" "5 sec" '{"File Size": "1 KB"}' '')
require_id "GenerateFlowFile processor" "$GEN_ID"
echo "  GenerateFlowFile: ${GEN_ID}"

LOG_ID=$(create_processor "Log Test Output" "LogMessage" "0 sec" '{}' '["success"]')
require_id "LogMessage processor" "$LOG_ID"
echo "  LogMessage: ${LOG_ID}"

CONN1_ID=$(create_connection "$GEN_ID" "$LOG_ID" '["success"]')
require_id "connection (Generate→Log)" "$CONN1_ID"
echo "  Connection (success): ${CONN1_ID}"

# --- Error path: GenerateFlowFile → PutFile /nonexistent ---
NEXT_X=100
NEXT_Y=300
echo ""
echo "Creating error flow: GenerateFlowFile → PutFile /nonexistent"

GEN2_ID=$(create_processor "Generate Error Data" "GenerateFlowFile" "10 sec" '{"File Size": "512 B"}' '')
require_id "GenerateFlowFile processor (error)" "$GEN2_ID"
echo "  GenerateFlowFile: ${GEN2_ID}"

PUT_ID=$(create_processor "Fail Writer" "PutFile" "0 sec" '{"Directory": "/nonexistent/output"}' '["success", "failure"]')
require_id "PutFile processor" "$PUT_ID"
echo "  PutFile: ${PUT_ID}"

CONN2_ID=$(create_connection "$GEN2_ID" "$PUT_ID" '["success"]')
require_id "connection (Generate→PutFile)" "$CONN2_ID"
echo "  Connection (success): ${CONN2_ID}"

# --- Start all processors ---
echo ""
echo "Starting all processors..."
for pid in "$GEN_ID" "$LOG_ID" "$GEN2_ID" "$PUT_ID"; do
    start_processor "$pid"
    echo "  Started ${pid}"
done

echo ""
echo "Flow setup complete. Wait 15-30 seconds for data to flow and bulletins to appear."
