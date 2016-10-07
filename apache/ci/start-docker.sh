#!/bin/bash

# A script to create the Apache containers.

set -e

NAME='dd-test-apache'
PORT=8180

APACHE_VERSION=${APACHE_VERSION-2.4.23}

if docker ps -a | grep dd-test-apache >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash apache/ci/stop-docker.sh
fi

docker create --expose $PORT -p $PORT:$PORT --name $NAME httpd:$APACHE_VERSION
docker cp ./apache/ci/httpd.conf $NAME:/usr/local/apache2/conf/httpd.conf
docker start $NAME

IP_ADDR=$(docker inspect ${NAME} | grep '"IPAddress"' | cut -d':' -f2 | cut -d'"' -f2)
IP_ADDR=$(echo $NAME | cut -d " " -f2)

sleep 10
