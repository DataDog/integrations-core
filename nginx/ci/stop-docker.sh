#!/bin/bash

# A script to tear down the MySQL containers.

set -e

NAME=dd-test-nginx

if docker ps -a | grep $NAME >/dev/null; then
  containers=$(docker ps -q --filter name=$NAME)
  stopped_containers=$(docker ps -a -q --filter name=$NAME)

  docker kill $containers>/dev/null || true
  docker rm $stopped_containers>/dev/null || true
fi
