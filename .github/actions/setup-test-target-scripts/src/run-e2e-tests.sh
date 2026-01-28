#!/bin/bash
# Run E2E tests for test-target workflow
# This script is called from test-target.yml to reduce YAML size

# Environment variables (set via GITHUB_ENV by setup-test-env.sh):
# INPUT_REPO, INPUT_TARGET, INPUT_PLATFORM, INPUT_PYTEST_ARGS, INPUT_TARGET_ENV, INPUT_IS_FORK
#
# Step-specific environment variables (passed directly from workflow step):
# INPUT_SESSION_NAME (optional) - custom session name, defaults to "e2e-tests"
# INPUT_IS_LATEST (optional) - set to "true" for latest version tests
# INPUT_TARGET (override) - for latest tests, set to "target:latest"

export DD_TEST_SESSION_NAME="${INPUT_SESSION_NAME:-e2e-tests}"

# Set tracing flag
# TODO: SQL Server on Windows crashes when tracing is enabled with error File Windows fatal exception: access violation
# Disable tracing on forks since they don't have access to DD_API_KEY
if [[ "$INPUT_REPO" == 'core' && ( "$INPUT_TARGET" != 'sqlserver' || "$INPUT_PLATFORM" != 'windows' ) && "$INPUT_IS_FORK" != 'true' ]]; then
  export DDEV_TEST_ENABLE_TRACING="1"
else
  export DDEV_TEST_ENABLE_TRACING="0"
fi

# Set E2E flags based on repo (latest always uses --base --new-env)
if [[ "$INPUT_REPO" == 'core' || "$INPUT_IS_LATEST" == 'true' ]]; then
  E2E_FLAGS="--base --new-env"
else
  E2E_FLAGS="--dev"
fi

# Build target arguments
# For latest: INPUT_TARGET already contains "target:latest", no separate env
# For regular: INPUT_TARGET is just the target, INPUT_TARGET_ENV is the env
if [[ -n "$INPUT_TARGET_ENV" ]]; then
  TARGET_ARGS="$INPUT_TARGET $INPUT_TARGET_ENV"
else
  TARGET_ARGS="$INPUT_TARGET"
fi

# Set positional arguments ($@) based on inputs
# This is done to ensure we handle pytest args correctly.
if [[ -n "$INPUT_PYTEST_ARGS" ]]; then
  # Use eval to correctly parse quoted arguments (e.g. -m "not flaky")
  eval "set -- $INPUT_PYTEST_ARGS"
elif [[ "$INPUT_IS_LATEST" == 'true' ]]; then
  # Latest version without pytest args: include 'all' explicitly
  set -- "all"
else
  # Clear positional arguments
  set --
fi

set +e
set -x
ddev env test $E2E_FLAGS --junit $TARGET_ARGS -- "$@" -k "not fips"
exit_code=$?
set +x

if [[ $exit_code -eq 5 ]]; then
  echo "No tests were collected."
  exit 0
else
  exit $exit_code
fi
