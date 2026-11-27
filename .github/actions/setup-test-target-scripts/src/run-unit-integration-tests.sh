#!/bin/bash
# Run Unit & Integration tests for test-target workflow
# This script is called from test-target.yml to reduce YAML size

# Environment variables (set via GITHUB_ENV by setup-test-env.sh):
# INPUT_REPO, INPUT_TARGET, INPUT_PLATFORM, INPUT_MINIMUM_BASE_PACKAGE
# INPUT_TARGET_ENV, INPUT_PYTEST_ARGS, INPUT_EXCLUDE_FIPS, INPUT_IS_FORK

# Set tracing flag
# TODO: SQL Server on Windows crashes when tracing is enabled with error File Windows fatal exception: access violation
# Disable tracing on forks since they don't have access to DD_API_KEY
if [[ "$INPUT_REPO" == 'core' && ( "$INPUT_TARGET" != 'sqlserver' || "$INPUT_PLATFORM" != 'windows' ) && "$INPUT_IS_FORK" != 'true' ]]; then
  export DDEV_TEST_ENABLE_TRACING="1"
else
  export DDEV_TEST_ENABLE_TRACING="0"
fi

# Set test session name and extra flags based on minimum-base-package
if [[ "$INPUT_MINIMUM_BASE_PACKAGE" == 'true' ]]; then
  export DD_TEST_SESSION_NAME="minimum-base-package-tests"
  TEST_FLAGS=(--compat --recreate)
  GLOBAL_FLAGS=()
else
  export DD_TEST_SESSION_NAME="unit-tests"
  TEST_FLAGS=(--cov)
  GLOBAL_FLAGS=(-v)
  # ddev -v sets HATCH_VERBOSE=2, which makes Hatch pass -v to its native uv commands;
  # HATCH_QUIET=1 offsets that to net verbosity 1, so uv stays quiet but ddev/pytest verbosity is kept.
  export HATCH_QUIET=1
fi

if [[ -n "$INPUT_TARGET_ENV" ]]; then
  TEST_FLAGS+=(--envs "$INPUT_TARGET_ENV")
fi
PYTEST_ARGS="${INPUT_PYTEST_ARGS:-}"
if [[ "${INPUT_EXCLUDE_FIPS:-true}" == 'true' ]]; then
  PYTEST_ARGS+=' -k "not fips"'
fi

set +e
set -x
ddev "${GLOBAL_FLAGS[@]}" test "${TEST_FLAGS[@]}" --junit "$INPUT_TARGET" --pytest-args "$PYTEST_ARGS"
exit_code=$?
set +x

if [[ "$INPUT_PYTEST_ARGS" == '-m flaky' && $exit_code -eq 5 ]]; then
  # Flaky test count can be zero, this is done to avoid pipeline failure
  echo "No tests were collected."
  exit 0
else
  exit $exit_code
fi
