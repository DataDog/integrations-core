#!/bin/bash

# A script to tear down the MySQL containers.

set -e

if docker ps -a | grep dd-test-fluentd >/dev/null; then
  containers=$(docker ps --format '{{.Names}}' --filter name=dd-test-fluentd)
  stopped_containers=$(docker ps -a --format '{{.Names}}' --filter name=dd-test-fluentd)

  docker kill $containers
  docker rm $stopped_containers
fi
