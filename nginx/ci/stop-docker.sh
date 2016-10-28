#!/bin/bash

# A script to tear down the MySQL containers.

set -e

NAME=dd-test-nginx

if docker ps -a | grep $NAME >/dev/null; then
  containers=$(docker ps --format '{{.Names}}' --filter name=$NAME)
  stopped_containers=$(docker ps -a --format '{{.Names}}' --filter name=$NAME)

  docker kill $containers>/dev/null
  docker rm $stopped_containers>/dev/null
fi
