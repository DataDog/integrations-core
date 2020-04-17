#!/bin/bash
set -euo pipefail

set +x

n=0
until [ $n -ge 3 ]
do
   echo "$ORACLE_DOCKER_PASSWORD" | docker login container-registry.oracle.com --username "$ORACLE_DOCKER_USERNAME" --password-stdin && break
   n=$((n+1))
   sleep 5
done

set -x
