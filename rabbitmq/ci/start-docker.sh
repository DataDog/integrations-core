#!/bin/bash

source utils/bash/ci.sh

NAME='dd-test-rabbitmq'

stop-docker $NAME

VERSION=${FLAVOR_VERSION-3.5.0}

docker run -d --name $NAME -p 15672:15672 -p 5672:5672 rabbitmq:$VERSION-management

mkdir -p tmp
wget localhost:15672/cli/rabbitmqadmin -O tmp/rabbitmqadmin
# chmod +x rabbitmqadmin
