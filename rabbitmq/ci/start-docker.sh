#!/bin/bash

source utils/bash/ci.sh

NAME='dd-test-rabbitmq'

stop-docker $NAME

VERSION=${FLAVOR_VERSION-3.5.0}

docker run -d --name $NAME -p 15672:15672 -p 5672:5672 rabbitmq:$VERSION-management

COUNT=1
until [[ docker logs $NAME 2>&1 ~= "*Server startup complete" || $COUNT -eq 20 ]]; do
  sleep 2
  COUNT=$(($COUNT+1))
done

if [[ docker logs $NAME 2>&1 ~= "*Server startup complete" ]]; then
  mkdir -p tmp
  wget localhost:15672/cli/rabbitmqadmin -O tmp/rabbitmqadmin
else
  exit 1
fi
# chmod +x rabbitmqadmin
