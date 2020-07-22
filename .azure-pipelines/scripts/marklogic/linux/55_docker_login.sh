#!/bin/bash
set -euo pipefail

set +x

echo "$DEV_DOCKER_PASSWORD" | docker login --username "$DEV_DOCKER_USERNAME" --password-stdin

set -x
