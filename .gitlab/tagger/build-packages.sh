#!/bin/bash
# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euxo pipefail
IFS=$'\n\t'

echo "Start build-packages.sh"

if [[ -n "$DD_TEST_CMD" ]]; then
    echo "Triggering build pipeline..."
    echo "$DD_TEST_CMD"
else
    echo "Skipping, DD_TEST_CMD is not set"
fi

echo "End build-packages.sh"
