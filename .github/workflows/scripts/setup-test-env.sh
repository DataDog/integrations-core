#!/bin/bash
# Setup environment variables for test-target workflow
# This script is called from test-target.yml to reduce YAML size

set -euo pipefail

# Required environment variables (passed from workflow):
# INPUT_PYTHON_VERSION, INPUT_TEST_PY2, INPUT_TEST_PY3, INPUT_PLATFORM
# INPUT_AGENT_IMAGE, INPUT_AGENT_IMAGE_PY2, INPUT_AGENT_IMAGE_WINDOWS, INPUT_AGENT_IMAGE_WINDOWS_PY2
# INPUT_TARGET, INPUT_REPO, INPUT_CONTEXT, INPUT_MINIMUM_BASE_PACKAGE, INPUT_JOB_NAME
# DD_API_KEY_SECRET, SETUP_ENV_VARS
# DOCKER_USERNAME, DOCKER_ACCESS_TOKEN, ORACLE_DOCKER_USERNAME, ORACLE_DOCKER_PASSWORD
# DD_GITHUB_USER, DD_GITHUB_TOKEN

# =============================================================================
# Define all variables as bash variables first for readability
# =============================================================================

DEFAULT_PYTHON_VERSION="3.13"

# Static variables
FORCE_COLOR="1"
TEST_RESULTS_BASE_DIR="test-results"
PYTHON_VERSION="${INPUT_PYTHON_VERSION:-$DEFAULT_PYTHON_VERSION}"
PYTHONUNBUFFERED="1"

# SKIP_ENV_NAME logic
if [ "${INPUT_TEST_PY2:-}" = 'true' ] && [ "${INPUT_TEST_PY3:-}" != 'true' ]; then
  SKIP_ENV_NAME="py3.*"
elif [ "${INPUT_TEST_PY2:-}" != 'true' ] && [ "${INPUT_TEST_PY3:-}" = 'true' ]; then
  SKIP_ENV_NAME="py2.*"
else
  SKIP_ENV_NAME=""
fi

# Windows E2E requires Windows containers
if [ "${INPUT_PLATFORM:-}" = 'windows' ]; then
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
if [ "${INPUT_MINIMUM_BASE_PACKAGE:-}" = 'true' ]; then
  MINIMUM_BASE_PACKAGE_PREFIX="minimum-base-package-"
else
  MINIMUM_BASE_PACKAGE_PREFIX=""
fi

# We want to replace leading dots as they will make directories hidden,
# which will cause them to be ignored by upload-artifact and EnricoMi/publish-unit-test-result-action
JOB_NAME=$(echo "$INPUT_JOB_NAME" | sed 's/^\./Dot/')
TEST_RESULTS_DIR="${TEST_RESULTS_BASE_DIR}/${JOB_NAME}"

# DD_TAGS
DD_TAGS="team:agent-integrations,platform:${INPUT_PLATFORM},target:${INPUT_TARGET},agent_image:${DDEV_E2E_AGENT},context:${INPUT_CONTEXT}"

# =============================================================================
# Export all variables to GITHUB_ENV
# =============================================================================
{
  echo "FORCE_COLOR=${FORCE_COLOR}"
  echo "TEST_RESULTS_BASE_DIR=${TEST_RESULTS_BASE_DIR}"
  echo "PYTHON_VERSION=${PYTHON_VERSION}"
  echo "PYTHONUNBUFFERED=${PYTHONUNBUFFERED}"
  echo "SKIP_ENV_NAME=${SKIP_ENV_NAME}"
  echo "DDEV_E2E_AGENT=${DDEV_E2E_AGENT}"
  echo "DDEV_E2E_AGENT_PY2=${DDEV_E2E_AGENT_PY2}"
  echo "DD_ENV=${DD_ENV}"
  echo "DD_SERVICE=${DD_SERVICE}"
  echo "DD_TRACE_ANALYTICS_ENABLED=${DD_TRACE_ANALYTICS_ENABLED}"
  echo "DD_CIVISIBILITY_ENABLED=${DD_CIVISIBILITY_ENABLED}"
  echo "DD_CIVISIBILITY_AGENTLESS_ENABLED=${DD_CIVISIBILITY_AGENTLESS_ENABLED}"
  echo "DD_CIVISIBILITY_AUTO_INSTRUMENTATION_PROVIDER=${DD_CIVISIBILITY_AUTO_INSTRUMENTATION_PROVIDER}"
  echo "DD_PROFILING_ENABLED=${DD_PROFILING_ENABLED}"
  echo "DD_SITE=${DD_SITE}"
  echo "DD_API_KEY=${DD_API_KEY}"
  echo "MINIMUM_BASE_PACKAGE_PREFIX=${MINIMUM_BASE_PACKAGE_PREFIX}"
  echo "TEST_RESULTS_DIR=${TEST_RESULTS_DIR}"
  echo "DD_TAGS=${DD_TAGS}"
  echo "DOCKER_USERNAME=${DOCKER_USERNAME}"
  echo "DOCKER_ACCESS_TOKEN=${DOCKER_ACCESS_TOKEN}"
  echo "ORACLE_DOCKER_USERNAME=${ORACLE_DOCKER_USERNAME}"
  echo "ORACLE_DOCKER_PASSWORD=${ORACLE_DOCKER_PASSWORD}"
  echo "DD_GITHUB_USER=${DD_GITHUB_USER}"
  echo "DD_GITHUB_TOKEN=${DD_GITHUB_TOKEN}"
} >> "$GITHUB_ENV"

# Override with custom vars if provided
if [ -n "${SETUP_ENV_VARS:-}" ]; then
  echo "$SETUP_ENV_VARS" | jq -r 'to_entries[] | "\(.key)=\(.value)"' >> "$GITHUB_ENV"
fi
