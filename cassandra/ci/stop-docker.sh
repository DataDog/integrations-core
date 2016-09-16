#!/bin/bash

# A script to tear down the Cassandra containers.

set -e

if docker ps -a | grep dd-test-cassandra >/dev/null; then
  containers=$(docker ps --format '{{.Names}}' --filter name=dd-test-cassandra)
  stopped_containers=$(docker ps -a --format '{{.Names}}' --filter name=dd-test-cassandra)

  docker kill $containers 2>/dev/null || true
  docker rm $stopped_containers 2>/dev/null || true
fi
