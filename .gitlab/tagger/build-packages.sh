#!/bin/bash
# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euxo pipefail
IFS=$'\n\t'

if [[ -n "$DD_TEST_CMD" ]]; then
    echo "Triggering build pipeline..."
    eval "$DD_TEST_CMD"
else
    echo "Skipping, DD_TEST_CMD is not set"
fi
