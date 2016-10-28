#!/bin/bash

NAME=dd-test-fluentd
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if docker ps | grep $NAME >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash fluentd/ci/stop-docker.sh
fi

docker run -d -p 24220:24220 --name $NAME -v $DIR/td-agent.conf:/fluentd/etc/td-agent.conf -e FLUENTD_CONF=td-agent.conf fluent/fluentd:v0.12.23

WAITED=0
until [[ `docker logs $NAME 2>&1` =~ .*"type monitor_agent" || "$WAITED" -eq "10" ]]; do
  echo $WAITED
  docker logs $NAME
  sleep 2
  WAITED=$(($WAITED+1))
done
