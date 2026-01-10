#!/bin/bash
# Record paginated Task fixtures from a real Nutanix Prism Central API.
#
# Defaults match `AWS_INSTANCE` in `tests/conftest.py`, but you should override secrets via env vars.
#
# Usage:
#   ./record_tasks_fixtures.sh [PAGE_LIMIT] [MAX_PAGES]
#
# Env overrides:
#   NUTANIX_PC_IP         (default: https://prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com)
#   NUTANIX_PC_PORT       (default: 9440)
#   NUTANIX_PC_USERNAME   (default: dd_agent_viewer)
#   NUTANIX_PC_PASSWORD   (default: DummyP4ssw0rd!)
#   NUTANIX_TLS_VERIFY    (default: false)  # when false, uses curl -k
#
# Output:
#   tests/fixtures/tasks_limit{PAGE_LIMIT}_page{N}.json
#
# Requires: curl, jq
set -euo pipefail

PAGE_LIMIT=${1:-50}
MAX_PAGES=${2:-20}

PC_IP=${NUTANIX_PC_IP:-"https://prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com"}
PC_PORT=${NUTANIX_PC_PORT:-"9440"}
PC_USERNAME=${NUTANIX_PC_USERNAME:-"dd_agent"}
PC_PASSWORD=${NUTANIX_PC_PASSWORD:-"DummyPassw0rd!"}
TLS_VERIFY=${NUTANIX_TLS_VERIFY:-"false"}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="${SCRIPT_DIR}/../fixtures"

mkdir -p "${FIXTURES_DIR}"

# Normalize base URL
BASE_URL="${PC_IP%/}:${PC_PORT}"
if [[ "${BASE_URL}" != http* ]]; then
    BASE_URL="https://${BASE_URL}"
fi

curl_tls_args=()
if [[ "${TLS_VERIFY}" == "false" ]]; then
    curl_tls_args+=("-k")
fi

echo "Base URL: ${BASE_URL}"
echo "Fixtures dir: ${FIXTURES_DIR}"
echo "Endpoint: api/prism/v4.0/config/tasks"
echo "Page limit: ${PAGE_LIMIT}"
echo "Max pages: ${MAX_PAGES}"
echo ""

page=0
while [[ "${page}" -lt "${MAX_PAGES}" ]]; do
    endpoint="api/prism/v4.0/config/tasks?\$limit=${PAGE_LIMIT}&\$page=${page}"
    out="${FIXTURES_DIR}/tasks_limit${PAGE_LIMIT}_page${page}.json"

    echo "Fetching page ${page} -> ${out}"
    response="$(curl -sS "${curl_tls_args[@]}" \
        -u "${PC_USERNAME}:${PC_PASSWORD}" \
        -H "Accept: application/json" \
        -H "Content-Type: application/json" \
        "${BASE_URL}/${endpoint}")"

    # pretty-print + save
    echo "${response}" | jq '.' >"${out}"

    # stop if there's no next link
    next_href="$(echo "${response}" | jq -r '.metadata.links[]? | select(.rel=="next") | .href // empty')"
    if [[ -z "${next_href}" ]]; then
        echo "No next page link; stopping."
        break
    fi

    page=$((page + 1))
done

echo ""
echo "Done. Wrote task fixtures:"
ls -1 "${FIXTURES_DIR}/tasks_limit${PAGE_LIMIT}_page"*.json
