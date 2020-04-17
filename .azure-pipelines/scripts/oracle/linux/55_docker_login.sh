#!/bin/bash
set -euo pipefail

set +x

echo "$ORACLE_DOCKER_PASSWORD" | docker login container-registry.oracle.com --username "$ORACLE_DOCKER_USERNAME" --password-stdin

set -x
