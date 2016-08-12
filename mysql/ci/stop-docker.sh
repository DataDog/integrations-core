#!/bin/bash

# A script to tear down the MySQL containers.

set -e

if docker ps -a | grep dd-test-mysql >/dev/null; then
  containers=$(docker ps --format '{{.Names}}' --filter name=dd-test-mysql)
  stopped_containers=$(docker ps -a --format '{{.Names}}' --filter name=dd-test-mysql)

  docker kill $containers
  docker rm $stopped_containers
fi
