#!/bin/bash

set -e

NAME='dd-test-nginx'

PORT1=44441
PORT2=44442

NGINX_VERSION=${FLAVOR_VERSION-1.7.11}
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if docker ps | grep $NAME >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash $DIR/stop-docker.sh
fi

if [[ "$NGINX_VERSION" == "1.6.2" ]]; then
  DOCKER_REPO="simtech/nginx-1.6.2"
else
  DOCKER_REPO="nginx:1.7.11"
fi

docker run -d -p $PORT1:$PORT1 -p $PORT2:$PORT2 --name $NAME -v $DIR/nginx.conf:/etc/nginx/nginx.conf -v $DIR/testing.crt:/etc/nginx/testing.crt -v $DIR/testing.key:/etc/nginx/testing.key $DOCKER_REPO
