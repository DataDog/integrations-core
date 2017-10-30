#!/bin/bash

# A script to tear down the MySQL containers.

set -e

if docker ps -a | grep dd-ci-twemproxy >/dev/null; then
  containers=$(docker ps --format '{{.Names}}' --filter name=dd-ci-twemproxy)
  stopped_containers=$(docker ps -a --format '{{.Names}}' --filter name=dd-ci-twemproxy)

  docker kill $containers
  docker rm $stopped_containers
fi
