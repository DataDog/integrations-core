#!/bin/bash
# Run Unit & Integration tests for test-target workflow
# This script is called from test-target.yml to reduce YAML size

# Required environment variables:
# INPUT_REPO, INPUT_TARGET, INPUT_PLATFORM, INPUT_MINIMUM_BASE_PACKAGE
# INPUT_TARGET_STR, INPUT_PYTEST_ARGS

# Set tracing flag
# TODO: SQL Server on Windows crashes when tracing is enabled with error File Windows fatal exception: access violation
if [ "$INPUT_REPO" = 'core' ] && { [ "$INPUT_TARGET" != 'sqlserver' ] || [ "$INPUT_PLATFORM" != 'windows' ]; }; then
  export DDEV_TEST_ENABLE_TRACING="1"
else
  export DDEV_TEST_ENABLE_TRACING="0"
fi

# Set test session name and extra flags based on minimum-base-package
if [ "$INPUT_MINIMUM_BASE_PACKAGE" = 'true' ]; then
  export DD_TEST_SESSION_NAME="minimum-base-package-tests"
  EXTRA_FLAGS="--compat --recreate"
  COV_FLAG=""
  VERBOSE_FLAG=""
else
  export DD_TEST_SESSION_NAME="unit-tests"
  EXTRA_FLAGS=""
  COV_FLAG="--cov"
  VERBOSE_FLAG="-v"
fi

if [ "$INPUT_PYTEST_ARGS" = '-m flaky' ]; then
  set +e # Disable immediate exit
  set -x # Print command
  ddev $VERBOSE_FLAG test $EXTRA_FLAGS $COV_FLAG --junit "$INPUT_TARGET_STR" -- $INPUT_PYTEST_ARGS -k "not fips"
  exit_code=$?
  set +x
  if [ $exit_code -eq 5 ]; then
    # Flaky test count can be zero, this is done to avoid pipeline failure
    echo "No tests were collected."
    exit 0
  else
    exit $exit_code
  fi
elif [ -n "$INPUT_PYTEST_ARGS" ]; then
  # Has pytest args: include them with fips filter
  set -x
  ddev $VERBOSE_FLAG test $EXTRA_FLAGS $COV_FLAG --junit "$INPUT_TARGET_STR" -- $INPUT_PYTEST_ARGS -k "not fips"
  set +x
else
  # Default: just fips filter
  set -x
  ddev $VERBOSE_FLAG test $EXTRA_FLAGS $COV_FLAG --junit "$INPUT_TARGET_STR" -- -k "not fips"
  set +x
fi
