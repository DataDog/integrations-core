#!/bin/bash
# Run E2E tests for test-target workflow
# This script is called from test-target.yml to reduce YAML size

# Environment variables (set via GITHUB_ENV by setup-test-env.sh):
# INPUT_REPO, INPUT_TARGET, INPUT_PLATFORM, INPUT_PYTEST_ARGS, INPUT_TARGET_ENV, INPUT_IS_FORK
# INPUT_EXCLUDE_FIPS
#
# Step-specific environment variables (passed directly from workflow step):
# INPUT_SESSION_NAME (optional) - custom session name, defaults to "e2e-tests"
# INPUT_IS_LATEST (optional) - set to "true" for latest version tests
# INPUT_TARGET_ENV (override) - for latest tests, set to "latest"

export DD_TEST_SESSION_NAME="${INPUT_SESSION_NAME:-e2e-tests}"

# Set tracing flag
# TODO: SQL Server on Windows crashes when tracing is enabled with error File Windows fatal exception: access violation
# Disable tracing on forks since they don't have access to DD_API_KEY
if [[ "$INPUT_REPO" == 'core' && ( "$INPUT_TARGET" != 'sqlserver' || "$INPUT_PLATFORM" != 'windows' ) && "$INPUT_IS_FORK" != 'true' ]]; then
  export DDEV_TEST_ENABLE_TRACING="1"
else
  export DDEV_TEST_ENABLE_TRACING="0"
fi

# Set E2E flags based on context and repo
if [[ "$INPUT_CONTEXT" == test-agent* ]]; then
  E2E_FLAGS=(--new-env)
elif [[ "$INPUT_REPO" == 'core' || "$INPUT_IS_LATEST" == 'true' ]]; then
  E2E_FLAGS=(--base --new-env)
else
  E2E_FLAGS=(--dev)
fi

# Only core is guaranteed to run a ddev with --ignore-teardown-errors, since it installs ddev from
# the checkout. Other repos install from PyPI and may pin an older ddev to support older Pythons.
if [[ "$INPUT_REPO" == 'core' ]]; then
  E2E_FLAGS+=(--ignore-teardown-errors)
fi

PYTEST_ARGS="${INPUT_PYTEST_ARGS:-}"
if [[ "${INPUT_EXCLUDE_FIPS:-true}" == 'true' ]]; then
  PYTEST_ARGS+=' -k "not fips"'
fi

set +e
set -x
ddev env test "${E2E_FLAGS[@]}" --junit "$INPUT_TARGET" --envs "${INPUT_TARGET_ENV:-all}" --pytest-args "$PYTEST_ARGS"
exit_code=$?
set +x

if [[ $exit_code -eq 5 ]]; then
  echo "No tests were collected."
  exit 0
else
  exit $exit_code
fi
