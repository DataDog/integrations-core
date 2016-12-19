#!/bin/bash

NAME='dd-test-rabbitmq'

stop-docker $NAME

VERSION=${FLAVOR_VERSION-3.5.0}

docker run -d --name $NAME -p 15672:15672 -p 5672:5672 rabbitmq:$VERSION-management

COUNT=1
until [[ `docker logs $NAME 2>&1` =~ .*"Server startup complete" || $COUNT -eq 20 ]]; do
  sleep 2
  COUNT=$(($COUNT+1))
  echo `docker logs $NAME`
  echo $COUNT
  if [[ $COUNT -eq 20 ]]; then
    exit 1
  fi
done
