#!/bin/bash

# A script to tear down the MySQL containers.

set -e

if docker ps -a | grep dd-test-redis >/dev/null; then
  containers=$(docker ps --format '{{.Names}}' --filter name=dd-test-redis)
  stopped_containers=$(docker ps -a --format '{{.Names}}' --filter name=dd-test-redis)

  docker kill $containers || true
  docker rm $stopped_containers || true
fi
