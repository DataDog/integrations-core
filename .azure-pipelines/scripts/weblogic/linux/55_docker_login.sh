#!/bin/bash
set -euo pipefail

set +x

echo "[INFO] Docker login"
for i in 2 4 8 16 32; do
  echo "$ORACLE_DOCKER_PASSWORD" | docker login container-registry.oracle.com --username "$ORACLE_DOCKER_USERNAME" --password-stdin && break
  echo "[INFO] Wait $i seconds and retry docker login"
  sleep $i
done

set -x
