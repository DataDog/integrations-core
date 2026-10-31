#!/bin/bash
# Setup environment variables for test-target workflow
# This script is called from test-target.yml to reduce YAML size

set -euo pipefail

# Required environment variables (passed from workflow):
# INPUT_PYTHON_VERSION, INPUT_TEST_PY2, INPUT_TEST_PY3, INPUT_PLATFORM
# INPUT_AGENT_IMAGE, INPUT_AGENT_IMAGE_PY2, INPUT_AGENT_IMAGE_WINDOWS, INPUT_AGENT_IMAGE_WINDOWS_PY2
# INPUT_TARGET, INPUT_TARGET_ENV, INPUT_REPO, INPUT_CONTEXT, INPUT_MINIMUM_BASE_PACKAGE, INPUT_JOB_NAME
# INPUT_PYTEST_ARGS, INPUT_IS_FORK. INPUT_ADDITIONAL_TAGS and INPUT_REPLACE_TAGS are optional.
# DD_API_KEY_SECRET, SETUP_ENV_VARS
# DOCKER_USERNAME, DOCKER_ACCESS_TOKEN, ORACLE_DOCKER_USERNAME, ORACLE_DOCKER_PASSWORD
# DD_GITHUB_USER, DD_GITHUB_TOKEN

validate_single_line() {
  if [[ "$1" == *$'\r'* || "$1" == *$'\n'* ]]; then
    echo "Environment values must not contain CR or LF." >&2
    exit 1
  fi
}

# Validate before command substitution can strip trailing newlines (notably JOB_NAME).
for name in \
  INPUT_PYTHON_VERSION INPUT_TEST_PY2 INPUT_TEST_PY3 INPUT_PLATFORM \
  INPUT_AGENT_IMAGE INPUT_AGENT_IMAGE_PY2 INPUT_AGENT_IMAGE_WINDOWS INPUT_AGENT_IMAGE_WINDOWS_PY2 \
  INPUT_TARGET INPUT_TARGET_ENV INPUT_REPO INPUT_CONTEXT INPUT_MINIMUM_BASE_PACKAGE INPUT_JOB_NAME \
  INPUT_PYTEST_ARGS INPUT_IS_FORK INPUT_ADDITIONAL_TAGS INPUT_REPLACE_TAGS \
  DD_API_KEY_SECRET DOCKER_USERNAME DOCKER_ACCESS_TOKEN ORACLE_DOCKER_USERNAME ORACLE_DOCKER_PASSWORD \
  DD_GITHUB_USER DD_GITHUB_TOKEN; do
  validate_single_line "${!name-}"
done

DEFAULT_PYTHON_VERSION="3.13"

# Static variables
FORCE_COLOR="1"
TEST_RESULTS_BASE_DIR="test-results"
PYTHON_VERSION="${INPUT_PYTHON_VERSION:-$DEFAULT_PYTHON_VERSION}"
PYTHONUNBUFFERED="1"

# SKIP_ENV_NAME logic
if [[ "${INPUT_TEST_PY2:-}" == 'true' && "${INPUT_TEST_PY3:-}" != 'true' ]]; then
  SKIP_ENV_NAME="py3.*"
elif [[ "${INPUT_TEST_PY2:-}" != 'true' && "${INPUT_TEST_PY3:-}" == 'true' ]]; then
  SKIP_ENV_NAME="py2.*"
else
  SKIP_ENV_NAME=""
fi

# Windows E2E requires Windows containers
if [[ "${INPUT_PLATFORM:-}" == 'windows' ]]; then
  DDEV_E2E_AGENT="$INPUT_AGENT_IMAGE_WINDOWS"
  DDEV_E2E_AGENT_PY2="$INPUT_AGENT_IMAGE_WINDOWS_PY2"
else
  DDEV_E2E_AGENT="$INPUT_AGENT_IMAGE"
  DDEV_E2E_AGENT_PY2="$INPUT_AGENT_IMAGE_PY2"
fi

# CI Visibility configuration
DD_ENV="ci"
DD_SERVICE="${INPUT_TARGET}-integrations-${INPUT_REPO}"
DD_TRACE_ANALYTICS_ENABLED="true"
DD_CIVISIBILITY_ENABLED="true"
DD_CIVISIBILITY_AGENTLESS_ENABLED="true"
DD_CIVISIBILITY_AUTO_INSTRUMENTATION_PROVIDER="github"
DD_PROFILING_ENABLED="true"
DD_SITE="datadoghq.com"
DD_API_KEY="$DD_API_KEY_SECRET"

# Prefix for artifact names when using minimum base package
if [[ "${INPUT_MINIMUM_BASE_PACKAGE:-}" == 'true' ]]; then
  MINIMUM_BASE_PACKAGE_PREFIX="minimum-base-package-"
else
  MINIMUM_BASE_PACKAGE_PREFIX=""
fi

# We want to replace leading dots as they will make directories hidden,
# which will cause them to be ignored by upload-artifact and EnricoMi/publish-unit-test-result-action
JOB_NAME=$(echo "$INPUT_JOB_NAME" | sed 's/^\./Dot/')
TEST_RESULTS_DIR="${TEST_RESULTS_BASE_DIR}/${JOB_NAME}"

# DD_TAGS
if [[ "${INPUT_REPLACE_TAGS:-false}" == 'true' ]]; then
  if [[ -z "${INPUT_ADDITIONAL_TAGS:-}" ]]; then
    echo "INPUT_ADDITIONAL_TAGS must not be empty when INPUT_REPLACE_TAGS is true." >&2
    exit 1
  fi
  DD_TAGS="${INPUT_ADDITIONAL_TAGS}"
else
  DD_TAGS="team:agent-integrations,platform:${INPUT_PLATFORM},target:${INPUT_TARGET},target_env:${INPUT_TARGET_ENV:-all},agent_image:${DDEV_E2E_AGENT},context:${INPUT_CONTEXT}"
  if [[ -n "${INPUT_ADDITIONAL_TAGS:-}" ]]; then
    DD_TAGS="${DD_TAGS},${INPUT_ADDITIONAL_TAGS}"
  fi
fi

# Compute INPUT_TARGET_STR from INPUT_TARGET and INPUT_TARGET_ENV
if [[ -n "${INPUT_TARGET_ENV:-}" ]]; then
  INPUT_TARGET_STR="${INPUT_TARGET}:${INPUT_TARGET_ENV}"
else
  INPUT_TARGET_STR="${INPUT_TARGET}"
fi

records=(
  "FORCE_COLOR=${FORCE_COLOR}"
  "TEST_RESULTS_BASE_DIR=${TEST_RESULTS_BASE_DIR}"
  "PYTHON_VERSION=${PYTHON_VERSION}"
  "PYTHONUNBUFFERED=${PYTHONUNBUFFERED}"
  "SKIP_ENV_NAME=${SKIP_ENV_NAME}"
  "DDEV_E2E_AGENT=${DDEV_E2E_AGENT}"
  "DDEV_E2E_AGENT_PY2=${DDEV_E2E_AGENT_PY2}"
  "DD_ENV=${DD_ENV}"
  "DD_SERVICE=${DD_SERVICE}"
  "DD_TRACE_ANALYTICS_ENABLED=${DD_TRACE_ANALYTICS_ENABLED}"
  "DD_CIVISIBILITY_ENABLED=${DD_CIVISIBILITY_ENABLED}"
  "DD_CIVISIBILITY_AGENTLESS_ENABLED=${DD_CIVISIBILITY_AGENTLESS_ENABLED}"
  "DD_CIVISIBILITY_AUTO_INSTRUMENTATION_PROVIDER=${DD_CIVISIBILITY_AUTO_INSTRUMENTATION_PROVIDER}"
  "DD_PROFILING_ENABLED=${DD_PROFILING_ENABLED}"
  "DD_SITE=${DD_SITE}"
  "DD_API_KEY=${DD_API_KEY}"
  "MINIMUM_BASE_PACKAGE_PREFIX=${MINIMUM_BASE_PACKAGE_PREFIX}"
  "TEST_RESULTS_DIR=${TEST_RESULTS_DIR}"
  "DD_TAGS=${DD_TAGS}"
  "DOCKER_USERNAME=${DOCKER_USERNAME}"
  "DOCKER_ACCESS_TOKEN=${DOCKER_ACCESS_TOKEN}"
  "ORACLE_DOCKER_USERNAME=${ORACLE_DOCKER_USERNAME}"
  "ORACLE_DOCKER_PASSWORD=${ORACLE_DOCKER_PASSWORD}"
  "DD_GITHUB_USER=${DD_GITHUB_USER}"
  "DD_GITHUB_TOKEN=${DD_GITHUB_TOKEN}"
  # Variables used by test scripts (run-unit-integration-tests.sh, run-e2e-tests.sh)
  # Define once here to avoid overloading the action object map
  "INPUT_REPO=${INPUT_REPO}"
  "INPUT_TARGET=${INPUT_TARGET}"
  "INPUT_TARGET_ENV=${INPUT_TARGET_ENV:-}"
  "INPUT_TARGET_STR=${INPUT_TARGET_STR}"
  "INPUT_PLATFORM=${INPUT_PLATFORM}"
  "INPUT_MINIMUM_BASE_PACKAGE=${INPUT_MINIMUM_BASE_PACKAGE:-false}"
  "INPUT_PYTEST_ARGS=${INPUT_PYTEST_ARGS:-}"
  "INPUT_IS_FORK=${INPUT_IS_FORK:-false}"
  "INPUT_CONTEXT=${INPUT_CONTEXT:-standard}"
)

for record in "${records[@]}"; do
  if [[ ! "${record%%=*}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "Invalid environment variable name." >&2
    exit 1
  fi
  validate_single_line "$record"
done

# Stage everything privately, preserving native jq line endings on Windows.
staged_env=$(mktemp "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/test-env.XXXXXX")
trap 'rm -f "$staged_env"' EXIT
printf '%s\n' "${records[@]}" > "$staged_env"

# Validate decoded values before rendering, preserving jq's string conversions.
if [[ -n "${SETUP_ENV_VARS:-}" ]]; then
  if ! printf '%s' "$SETUP_ENV_VARS" | jq -sr '
    if length == 0 then
      empty
    elif length != 1 or (.[0] | type) != "object" then
      error("Expected one environment variable map")
    else
      .[0] | to_entries | map(.value |= tostring) |
      if all(.[];
        (.key | test("\\A[A-Za-z_][A-Za-z0-9_]*\\z")) and
        (.value | test("[\r\n\u0000]") | not)
      ) then
        .[] | "\(.key)=\(.value)"
      else
        error("Invalid environment record")
      end
    end
  ' >> "$staged_env" 2>/dev/null; then
    echo "Invalid SETUP_ENV_VARS: expected a JSON map with valid names and single-line values." >&2
    exit 1
  fi
fi

cat "$staged_env" >> "$GITHUB_ENV"
