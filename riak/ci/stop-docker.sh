#!/bin/bash

# A script to tear down the Riak containers.

NAME='dd-test-riak'

set -e

if docker ps -a | grep $NAME >/dev/null; then
  containers=$(docker ps --format '{{.Names}}' --filter name=$NAME)
  stopped_containers=$(docker ps -a --format '{{.Names}}' --filter name=$NAME)

  docker kill $containers
  docker rm $stopped_containers
fi
