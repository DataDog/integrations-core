#!/bin/bash
set -euo pipefail

set +x

echo "$DOCKER_ACCESS_TOKEN" | docker login --username "$DOCKER_USERNAME" --password-stdin

set -x
