#!/bin/bash
# Run E2E tests for test-target workflow
# This script is called from test-target.yml to reduce YAML size

# Required environment variables:
# INPUT_REPO, INPUT_TARGET, INPUT_PLATFORM, INPUT_PYTEST_ARGS
# INPUT_TARGET_ENV (optional) - environment to run tests against
# INPUT_IS_LATEST (optional) - set to "true" for latest version tests
# INPUT_SESSION_NAME (optional) - custom session name

export DD_TEST_SESSION_NAME="${INPUT_SESSION_NAME:-e2e-tests}"

# Set tracing flag
# TODO: SQL Server on Windows crashes when tracing is enabled with error File Windows fatal exception: access violation
if [ "$INPUT_REPO" = 'core' ] && { [ "$INPUT_TARGET" != 'sqlserver' ] || [ "$INPUT_PLATFORM" != 'windows' ]; }; then
  export DDEV_TEST_ENABLE_TRACING="1"
else
  export DDEV_TEST_ENABLE_TRACING="0"
fi

# Set E2E flags based on repo (latest always uses --base --new-env)
if [ "$INPUT_REPO" = 'core' ] || [ "$INPUT_IS_LATEST" = 'true' ]; then
  E2E_FLAGS="--base --new-env"
else
  E2E_FLAGS="--dev"
fi

# Build target arguments
# For latest: INPUT_TARGET already contains "target:latest", no separate env
# For regular: INPUT_TARGET is just the target, INPUT_TARGET_ENV is the env
if [ -n "$INPUT_TARGET_ENV" ]; then
  TARGET_ARGS="$INPUT_TARGET $INPUT_TARGET_ENV"
else
  TARGET_ARGS="$INPUT_TARGET"
fi

# '-- all' is passed for e2e tests if pytest args are provided
# This is done to avoid ddev from interpreting the arguments as environments
#   instead of pytest-args, because by default if no environment is provided
#   after -- it will run all environments. So when pytests args are provided
#   ddev will interpret '-m' as an environment to run the e2e test on and fails
# This is not required when no pytest args are provided and it will run all environments
#   by default
set +e # Disable immediate exit

if [ -n "$INPUT_PYTEST_ARGS" ]; then
  # Has pytest args: include them with fips filter
  set -x
  ddev env test $E2E_FLAGS --junit $TARGET_ARGS -- $INPUT_PYTEST_ARGS -k "not fips"
  exit_code=$?
  set +x
elif [ "$INPUT_IS_LATEST" = 'true' ]; then
  # Latest version without pytest args: include 'all' explicitly
  set -x
  ddev env test $E2E_FLAGS --junit $TARGET_ARGS -- all -k "not fips"
  exit_code=$?
  set +x
else
  # Default: just fips filter
  set -x
  ddev env test $E2E_FLAGS --junit $TARGET_ARGS -- -k "not fips"
  exit_code=$?
  set +x
fi

if [ "$exit_code" -eq 5 ]; then
  echo "No tests were collected."
  exit 0
else
  exit "$exit_code"
fi
