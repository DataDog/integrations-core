#!/bin/bash

set -ex

# Only required on pull requests or release branches where master is not available
if [[ -n "$GITHUB_BASE_REF" || "$GITHUB_REF_NAME" =~ ^[[:digit:]]\.[[:digit:]]+\.[[:digit:]]+.* ]]; then
  git fetch origin master:master
fi

set +ex
