#!/bin/bash

set -e

if docker ps -a | grep dd-test-tokumx >/dev/null; then
  containers=$(docker ps --format '{{.Names}}' --filter name=dd-test-tokumx)
  stopped_containers=$(docker ps -a --format '{{.Names}}' --filter name=dd-test-tokumx)

  echo 'stopping containers'
  for container in $containers; do
    echo "stopping $container"
    docker kill $container
  done

  echo 'removing stopped containers'
  for stopped_container in $stopped_containers; do
    echo "removing $stopped_container"
    docker rm $stopped_container
  done

fi
