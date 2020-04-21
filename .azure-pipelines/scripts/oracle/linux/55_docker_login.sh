#!/bin/bash
set -euo pipefail

set +x

for i in 2 4 8 16 32; do
  echo "$ORACLE_DOCKER_PASSWORD" | docker login container-registry.oracle.com --username "$ORACLE_DOCKER_USERNAME" --password-stdin && break
  sleep $i
done

set -x
