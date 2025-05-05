#!/bin/bash

set -ex

# Only required on non-master branches
if [[ "$GITHUB_REF_NAME" != "master" ]]; then
  git fetch origin master:master
fi

set +ex
