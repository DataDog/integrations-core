#!/bin/bash

shopt -s expand_aliases

stop-docker() {
  if docker ps -a | grep $1 >/dev/null; then
    containers=$(docker ps -q --filter name=$1)
    stopped_containers=$(docker ps -a -q --filter name=$1)

    docker kill $containers 2>&1 > /dev/null || true
    docker rm $stopped_containers 2>&1 > /dev/null || true
  fi
}


# This has to be an alias, a bash function will give you the directory the utils script lives in,
# while an alias will give you the directory it's called in.
alias currentdir='
  "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
'
