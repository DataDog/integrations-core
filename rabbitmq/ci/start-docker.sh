#!/bin/bash

source utils/bash/ci.sh

NAME='dd-test-rabbitmq'

stop-docker $NAME

VERSION=${FLAVOR_VERSION-3.5.0}

docker run -d --name $NAME rabbitmq:$VERSION-management
