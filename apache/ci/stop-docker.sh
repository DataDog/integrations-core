#!/bin/bash

# A script to tear down the MySQL containers.

set -e

if docker ps -a | grep dd-test-apache >/dev/null; then
  containers=$(docker ps --format '{{.Names}}' --filter name=dd-test-apache)
  stopped_containers=$(docker ps -a --format '{{.Names}}' --filter name=dd-test-apache)

  docker kill $containers 2>/dev/null || true
  docker rm $stopped_containers 2>/dev/null || true
fi
