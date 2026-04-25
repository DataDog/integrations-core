#!/usr/bin/env bash
# ABOUTME: Creates test flows in NiFi via the REST API for integration testing.
# ABOUTME: Builds a happy-path flow and an error-path flow that generates bulletins.

set -euo pipefail

NIFI_API_URL="${NIFI_API_URL:-https://localhost:8443/nifi-api}"
NIFI_USERNAME="${NIFI_USERNAME:-admin}"
NIFI_PASSWORD="${NIFI_PASSWORD:-ctsBtRBKHRAx69EqUghvvgEvjnaLjFEB}"

# --- Authenticate ---
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

# --- Helper: require a non-empty, non-null value ---
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

# --- Helper: create a processor ---
NEXT_X=100
NEXT_Y=100

create_processor() {
    local name="$1" type="$2" scheduling="$3" props="$4" auto_term="$5"
    local x=$NEXT_X y=$NEXT_Y
    NEXT_Y=$((NEXT_Y + 200))

    local body
    body=$(jq -n \
        --arg name "$name" \
        --arg type "$type" \
        --arg scheduling "$scheduling" \
        --argjson props "$props" \
        --argjson autoTerm "$auto_term" \
        --argjson x "$x" \
        --argjson y "$y" \
        '{
            revision: {version: 0},
            component: {
                name: $name,
                type: ("org.apache.nifi.processors." + $type),
                position: {x: $x, y: $y},
                config: {
                    schedulingPeriod: $scheduling,
                    properties: $props,
                    autoTerminatedRelationships: $autoTerm
                }
            }
        }')

    local resp
    resp=$(curl "${AUTH[@]}" -X POST \
        "${NIFI_API_URL}/process-groups/${ROOT_PG_ID}/processors" \
        -H "Content-Type: application/json" \
        -d "$body")

    echo "$resp" | jq -r '.id'
}

# --- Helper: create a connection between two processors ---
create_connection() {
    local source_id="$1" dest_id="$2" relationship="$3" name="$4"

    local body
    body=$(jq -n \
        --arg srcId "$source_id" \
        --arg dstId "$dest_id" \
        --arg rel "$relationship" \
        --arg name "$name" \
        --arg pgId "$ROOT_PG_ID" \
        '{
            revision: {version: 0},
            component: {
                name: $name,
                source: {id: $srcId, groupId: $pgId, type: "PROCESSOR"},
                destination: {id: $dstId, groupId: $pgId, type: "PROCESSOR"},
                selectedRelationships: [$rel]
            }
        }')

    curl "${AUTH[@]}" -X POST \
        "${NIFI_API_URL}/process-groups/${ROOT_PG_ID}/connections" \
        -H "Content-Type: application/json" \
        -d "$body" > /dev/null
}

# --- Helper: start a processor ---
start_processor() {
    local proc_id="$1"
    local version
    version=$(curl "${AUTH[@]}" "${NIFI_API_URL}/processors/${proc_id}" | jq '.revision.version')

    curl "${AUTH[@]}" -X PUT \
        "${NIFI_API_URL}/processors/${proc_id}/run-status" \
        -H "Content-Type: application/json" \
        -d "{\"revision\":{\"version\":${version}},\"state\":\"RUNNING\"}" > /dev/null
}

# === Flow 1: Happy path (GenerateFlowFile -> LogMessage) ===
GEN1_ID=$(create_processor "Generate Test Data" "standard.GenerateFlowFile" "5 sec" \
    '{"File Size": "1 KB"}' '[]')
require_id "GenerateFlowFile processor" "$GEN1_ID"

LOG_ID=$(create_processor "Log Test Output" "standard.LogMessage" "0 sec" \
    '{"Log Level": "info", "Log Prefix": "NiFi-Test"}' '["failure"]')
require_id "LogMessage processor" "$LOG_ID"

create_connection "$GEN1_ID" "$LOG_ID" "success" "happy-path"

# Auto-terminate LogMessage success relationship
LOG_VERSION=$(curl "${AUTH[@]}" "${NIFI_API_URL}/processors/${LOG_ID}" | jq '.revision.version')
curl "${AUTH[@]}" -X PUT "${NIFI_API_URL}/processors/${LOG_ID}" \
    -H "Content-Type: application/json" \
    -d "{\"revision\":{\"version\":${LOG_VERSION}},\"component\":{\"id\":\"${LOG_ID}\",\"config\":{\"autoTerminatedRelationships\":[\"success\"]}}}" > /dev/null

# === Flow 2: Error path (GenerateFlowFile -> PutFile /nonexistent -> generates bulletins) ===
GEN2_ID=$(create_processor "Generate Error Data" "standard.GenerateFlowFile" "10 sec" \
    '{"File Size": "1 KB"}' '[]')
require_id "Error GenerateFlowFile processor" "$GEN2_ID"

PUT_ID=$(create_processor "Write To Bad Path" "standard.PutFile" "0 sec" \
    '{"Directory": "/nonexistent/path"}' '["success"]')
require_id "PutFile processor" "$PUT_ID"

create_connection "$GEN2_ID" "$PUT_ID" "success" "error-path"

# Auto-terminate PutFile failure to avoid backpressure blocking
PUT_VERSION=$(curl "${AUTH[@]}" "${NIFI_API_URL}/processors/${PUT_ID}" | jq '.revision.version')
curl "${AUTH[@]}" -X PUT "${NIFI_API_URL}/processors/${PUT_ID}" \
    -H "Content-Type: application/json" \
    -d "{\"revision\":{\"version\":${PUT_VERSION}},\"component\":{\"id\":\"${PUT_ID}\",\"config\":{\"autoTerminatedRelationships\":[\"failure\"]}}}" > /dev/null

# --- Start all processors ---
start_processor "$GEN1_ID"
start_processor "$LOG_ID"
start_processor "$GEN2_ID"
start_processor "$PUT_ID"

echo "Test flows created and started."
