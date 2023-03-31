#!/bin/bash

set -ex

# Only required on pull requests
if [[ $GITHUB_BASE_REF ]]; then
  git fetch origin master:master
fi

set +ex
