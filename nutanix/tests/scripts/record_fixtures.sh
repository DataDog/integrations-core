#!/bin/bash
# Script to record all API fixtures from the Nutanix API
# Uses AWS_INSTANCE credentials and matches endpoints used in check.py
#
# Usage: ./record_fixtures.sh [PAGE_LIMIT] [MAX_PAGES]
#   PAGE_LIMIT: Number of items per page (default: 2)
#   MAX_PAGES: Maximum number of pages to fetch (default: 20)
#
# Examples:
#   ./record_fixtures.sh          # Use defaults (limit=2, max=20 pages)
#   ./record_fixtures.sh 10       # Use limit=10, max=20 pages
#   ./record_fixtures.sh 2 5      # Use limit=2, max=5 pages
#
# Retry Configuration:
#   MAX_RETRIES: 3 attempts with exponential backoff (2s, 4s, 8s)
#   Automatically retries failed requests with detailed error messages
#
# Events Collection:
#   Events are fetched ordered by creationTime ascending (oldest first)

set -e

# Parse arguments
PAGE_LIMIT=${1:-2}
MAX_PAGES=${2:-20}

# Retry Configuration
MAX_RETRIES=3
INITIAL_RETRY_DELAY=2  # seconds, will double with each retry (exponential backoff)

# AWS Instance Configuration
PC_HOST="prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com"
PC_PORT="9440"
PC_USERNAME="dd_agent_viewer"
PC_PASSWORD="DummyP4ssw0rd!"

# API Configuration
BASE_URL="https://${PC_HOST}:${PC_PORT}"

# Output directory (relative to this script's location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="${SCRIPT_DIR}/../fixtures"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Recording Nutanix API Fixtures${NC}"
echo -e "${BLUE}============================================${NC}"
echo "Base URL: ${BASE_URL}"
echo "Fixtures directory: ${FIXTURES_DIR}"
echo "Page limit: ${PAGE_LIMIT}"
echo "Max pages: ${MAX_PAGES}"
echo ""

# Create fixtures directory if it doesn't exist
mkdir -p "${FIXTURES_DIR}"

# Function to make API request and save response (with retry logic)
fetch_and_save() {
    local endpoint=$1
    local output_file=$2

    echo -e "${YELLOW}Fetching: ${endpoint}${NC}"

    local url="${BASE_URL}/${endpoint}"
    local retry_count=0
    local retry_delay="${INITIAL_RETRY_DELAY}"

    while [ "$retry_count" -le "${MAX_RETRIES}" ]; do
        # Make the API request
        local response
        local http_code

        response=$(curl -s -k -w "\n%{http_code}" \
            -u "${PC_USERNAME}:${PC_PASSWORD}" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json" \
            "${url}")

        # Extract HTTP status code (last line)
        http_code=$(echo "$response" | tail -n 1)
        # Extract response body (all but last line)
        response_body=$(echo "$response" | sed '$d')

        if [ "$http_code" -eq 200 ]; then
            # Success - pretty print and save the response
            echo "$response_body" | jq '.' > "${output_file}"
            echo -e "${GREEN}✓ Saved: ${output_file}${NC}"
            echo ""
            return 0
        fi

        # Request failed - display detailed error
        echo -e "${RED}✗ HTTP Error ${http_code}${NC}"
        echo -e "${RED}Endpoint: ${endpoint}${NC}"

        # Try to pretty-print JSON error, fallback to raw output
        if echo "$response_body" | jq '.' > /dev/null 2>&1; then
            echo -e "${RED}Error response:${NC}"
            echo "$response_body" | jq '.' | sed 's/^/  /'
        else
            echo -e "${RED}Error response: ${response_body}${NC}"
        fi

        # Check if we should retry
        if [ "$retry_count" -lt "${MAX_RETRIES}" ]; then
            retry_count=$((retry_count + 1))
            echo -e "${YELLOW}Retrying in ${retry_delay}s... (attempt ${retry_count}/${MAX_RETRIES})${NC}"
            sleep "$retry_delay"
            # Exponential backoff
            retry_delay=$((retry_delay * 2))
        else
            echo -e "${RED}Failed after ${MAX_RETRIES} retries${NC}"
            echo ""
            return 1
        fi
    done
}

# Function to fetch paginated data (with retry logic)
fetch_paginated() {
    local endpoint=$1
    local base_name=$2
    local limit=$3
    local max_pages=$4

    echo -e "${BLUE}Fetching paginated: ${endpoint} (limit=${limit}, max_pages=${max_pages})${NC}"

    local page=0
    while [ "$page" -lt "$max_pages" ]; do
        # Use & if endpoint already has query params, otherwise use ?
        local separator="?"
        if [[ "$endpoint" == *"?"* ]]; then
            separator="&"
        fi
        local url="${endpoint}${separator}\$limit=${limit}&\$page=${page}"
        local output_file="${FIXTURES_DIR}/${base_name}_limit${limit}_page${page}.json"

        echo -e "${YELLOW}Page ${page}...${NC}"

        local retry_count=0
        local retry_delay="${INITIAL_RETRY_DELAY}"
        local page_success=false

        while [ "$retry_count" -le "${MAX_RETRIES}" ]; do
            local response
            local http_code

            response=$(curl -s -k -w "\n%{http_code}" \
                -u "${PC_USERNAME}:${PC_PASSWORD}" \
                -H "Content-Type: application/json" \
                -H "Accept: application/json" \
                "${BASE_URL}/${url}")

            # Extract HTTP status code (last line)
            http_code=$(echo "$response" | tail -n 1)
            # Extract response body (all but last line)
            response_body=$(echo "$response" | sed '$d')

            if [ "$http_code" -eq 200 ]; then
                # Success - pretty print and save the response
                echo "$response_body" | jq '.' > "${output_file}"
                echo -e "${GREEN}✓ Saved${NC}"
                page_success=true
                break
            fi

            # Request failed - display detailed error
            echo -e "${RED}✗ HTTP Error ${http_code}${NC}"
            echo -e "${RED}Endpoint: ${endpoint}?limit=${limit}&page=${page}${NC}"

            # Try to pretty-print JSON error, fallback to raw output
            if echo "$response_body" | jq '.' > /dev/null 2>&1; then
                echo -e "${RED}Error response:${NC}"
                echo "$response_body" | jq '.' | sed 's/^/  /'
            else
                echo -e "${RED}Error response: ${response_body}${NC}"
            fi

            # Check if we should retry
            if [ "$retry_count" -lt "${MAX_RETRIES}" ]; then
                retry_count=$((retry_count + 1))
                echo -e "${YELLOW}Retrying in ${retry_delay}s... (attempt ${retry_count}/${MAX_RETRIES})${NC}"
                sleep "$retry_delay"
                # Exponential backoff
                retry_delay=$((retry_delay * 2))
            else
                echo -e "${RED}Failed after ${MAX_RETRIES} retries${NC}"
                echo ""
                return 1
            fi
        done

        # If page failed after all retries, exit
        if [ "$page_success" = false ]; then
            return 1
        fi

        # Check if there's a next page
        local has_next
        has_next=$(echo "$response_body" | jq -r '.metadata.links[]? | select(.rel == "next") | .href // empty')

        if [ -z "$has_next" ]; then
            echo -e "${GREEN}No more pages (reached end)${NC}"
            break
        fi

        ((page++))
    done

    if [ "$page" -eq "$max_pages" ]; then
        echo -e "${YELLOW}Reached maximum page limit${NC}"
    fi

    echo -e "${GREEN}✓ Fetched $((page + 1)) page(s)${NC}"
    echo ""
}

# Calculate time window for stats (matching check.py logic)
# Use 120s window ending 120s ago
end_time=$(date -u -v-120S +"%Y-%m-%dT%H:%M:%S.000000Z" 2>/dev/null || date -u -d "120 seconds ago" +"%Y-%m-%dT%H:%M:%S.000000Z")
start_time=$(date -u -v-240S +"%Y-%m-%dT%H:%M:%S.000000Z" 2>/dev/null || date -u -d "240 seconds ago" +"%Y-%m-%dT%H:%M:%S.000000Z")

echo -e "${BLUE}Stats time window: ${start_time} to ${end_time}${NC}"
echo ""

# 1. Clusters (api/clustermgmt/v4.0/config/clusters)
echo -e "${BLUE}=== 1. Clusters ===${NC}"
fetch_paginated "api/clustermgmt/v4.0/config/clusters" "clusters" "${PAGE_LIMIT}" "${MAX_PAGES}"

# Get cluster ID for later use
CLUSTER_ID=""
if [ -f "${FIXTURES_DIR}/clusters_limit${PAGE_LIMIT}_page0.json" ]; then
    CLUSTER_ID=$(jq -r '.data[0].extId // empty' "${FIXTURES_DIR}/clusters_limit${PAGE_LIMIT}_page0.json")
    echo "Found cluster ID: ${CLUSTER_ID}"
    echo ""
fi

# 2. Hosts (api/clustermgmt/v4.0/config/clusters/{cluster_id}/hosts)
echo -e "${BLUE}=== 2. Hosts ===${NC}"
if [ -n "$CLUSTER_ID" ]; then
    fetch_paginated "api/clustermgmt/v4.0/config/clusters/${CLUSTER_ID}/hosts" "hosts" "${PAGE_LIMIT}" "${MAX_PAGES}"
else
    echo -e "${YELLOW}No cluster ID found, skipping hosts${NC}"
    echo ""
fi

# 3. VMs (api/vmm/v4.0/ahv/config/vms)
echo -e "${BLUE}=== 3. VMs ===${NC}"
fetch_paginated "api/vmm/v4.0/ahv/config/vms" "vms" "${PAGE_LIMIT}" "${MAX_PAGES}"

# 4. Cluster Stats (api/clustermgmt/v4.0/stats/clusters/{cluster_id})
echo -e "${BLUE}=== 4. Cluster Stats ===${NC}"
if [ -n "$CLUSTER_ID" ]; then
    # URL encode the time parameters
    start_time_encoded=$(printf '%s' "$start_time" | jq -sRr @uri)
    end_time_encoded=$(printf '%s' "$end_time" | jq -sRr @uri)
    params="\$startTime=${start_time_encoded}&\$endTime=${end_time_encoded}&\$statType=AVG&\$samplingInterval=120"
    fetch_and_save "api/clustermgmt/v4.0/stats/clusters/${CLUSTER_ID}?${params}" \
        "${FIXTURES_DIR}/cluster_stats.json"
else
    echo -e "${YELLOW}No cluster ID found, skipping${NC}"
    echo ""
fi

# 5. Host Stats (api/clustermgmt/v4.0/stats/clusters/{cluster_id}/hosts/{host_id})
echo -e "${BLUE}=== 5. Host Stats ===${NC}"
if [ -n "$CLUSTER_ID" ] && [ -f "${FIXTURES_DIR}/hosts_limit${PAGE_LIMIT}_page0.json" ]; then
    HOST_ID=$(jq -r '.data[0].extId // empty' "${FIXTURES_DIR}/hosts_limit${PAGE_LIMIT}_page0.json")
    if [ -n "$HOST_ID" ]; then
        echo "Using host ID: ${HOST_ID}"
        # URL encode the time parameters
        start_time_encoded=$(printf '%s' "$start_time" | jq -sRr @uri)
        end_time_encoded=$(printf '%s' "$end_time" | jq -sRr @uri)
        params="\$startTime=${start_time_encoded}&\$endTime=${end_time_encoded}&\$statType=AVG&\$samplingInterval=120"
        fetch_and_save "api/clustermgmt/v4.0/stats/clusters/${CLUSTER_ID}/hosts/${HOST_ID}?${params}" \
            "${FIXTURES_DIR}/host_stats.json"
    else
        echo -e "${YELLOW}No host ID found, skipping${NC}"
        echo ""
    fi
else
    echo -e "${YELLOW}No cluster or hosts fixture found, skipping${NC}"
    echo ""
fi

# 6. VM Stats (api/vmm/v4.0/ahv/stats/vms/)
echo -e "${BLUE}=== 6. VM Stats ===${NC}"
# URL encode the time parameters and $select=*
start_time_encoded=$(printf '%s' "$start_time" | jq -sRr @uri)
end_time_encoded=$(printf '%s' "$end_time" | jq -sRr @uri)
params="\$startTime=${start_time_encoded}&\$endTime=${end_time_encoded}&\$statType=AVG&\$samplingInterval=120&\$select=%2A"
fetch_paginated "api/vmm/v4.0/ahv/stats/vms/?${params}" "vms_stats" "${PAGE_LIMIT}" "${MAX_PAGES}"

# 7. Events (api/monitoring/v4.0/serviceability/events)
# Fetch events ordered by creationTime ascending (oldest first)
echo -e "${BLUE}=== 7. Events ===${NC}"
echo -e "${YELLOW}Ordering by creationTime asc${NC}"
events_params="\$orderby=creationTime%20asc"
fetch_paginated "api/monitoring/v4.0/serviceability/events?${events_params}" "events" "${PAGE_LIMIT}" "${MAX_PAGES}"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✓ All fixtures recorded successfully!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Summary:"
echo "  Page limit: ${PAGE_LIMIT}"
echo "  Cluster ID: ${CLUSTER_ID:-N/A}"
echo "  Fixtures directory: ${FIXTURES_DIR}"
echo ""
echo "Recorded fixtures:"
ls -lh "${FIXTURES_DIR}"/*.json 2>/dev/null | awk '{print "  " $9, "(" $5 ")"}' | tail -20
echo ""
echo "Total fixtures: $(ls -1 "${FIXTURES_DIR}"/*.json 2>/dev/null | wc -l | tr -d ' ')"
