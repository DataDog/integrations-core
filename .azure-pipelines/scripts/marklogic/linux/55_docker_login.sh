#!/bin/bash
set -euo pipefail

set +x

echo "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USERNAME" --password-stdin

set -x
