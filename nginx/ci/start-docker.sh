#!/bin/bash

set -e

NAME='dd-test-nginx'

PORT1=44441
PORT2=44442

NGINX_VERSION=${FLAVOR_VERSION-1.7.11}
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if docker ps -a | grep $NAME >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash $DIR/stop-docker.sh
fi

if [[ "$NGINX_VERSION" == "1.6.2" ]]; then
  # DOCKER_REPO="simtech/nginx-1.6.2"
  DOCKER_REPO="centos/nginx-16-centos7"
  VOLUMES="-v $DIR/nginx.conf:/opt/rh/nginx16/root/etc/nginx/nginx.conf -v $DIR/testing.crt:/opt/rh/nginx16/root/etc/nginx/testing.crt -v $DIR/testing.key:/opt/rh/nginx16/root/etc/nginx/testing.key"
  # docker run -d -p $PORT1:$PORT1 -p $PORT2:$PORT2 --name $NAME -v $DIR/nginx.conf:/opt/rh/nginx16/root/etc/nginx/nginx.conf -v $DIR/testing.crt:/opt/rh/nginx16/root/etc/nginx/testing.crt -v $DIR/testing.key:/opt/rh/nginx16/root/etc/nginx/testing.key $DOCKER_REPO
  docker create -p $PORT1:$PORT1 -p $PORT2:$PORT2 --name $NAME $DOCKER_REPO
  docker cp $DIR/nginx.conf $NAME:/opt/rh/nginx16/root/etc/nginx/nginx.conf
  docker cp $DIR/testing.key $NAME:/opt/rh/nginx16/root/etc/nginx/testing.key
  docker cp $DIR/testing.crt $NAME:/opt/rh/nginx16/root/etc/nginx/testing.crt

  docker start $NAME
else
  DOCKER_REPO="nginx:1.7.11"
  VOLUMES="-v $DIR/nginx.conf:/etc/nginx/nginx.conf -v $DIR/testing.crt:/etc/nginx/testing.crt -v $DIR/testing.key:/etc/nginx/testing.key"
  docker run -d -p $PORT1:$PORT1 -p $PORT2:$PORT2 --name $NAME -v $DIR/nginx.conf:/etc/nginx/nginx.conf -v $DIR/testing.crt:/etc/nginx/testing.crt -v $DIR/testing.key:/etc/nginx/testing.key $DOCKER_REPO
fi


docker logs $NAME
# docker run -d -p $PORT1:$PORT1 -p $PORT2:$PORT2 --name $NAME $DOCKER_REPO
