#!/bin/bash

if docker ps | grep dd-test-riak >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash riak/ci/stop-docker.sh
fi

set -e

NAME='dd-test-riak'
CI_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker run -d --name $NAME -p 18098:8098 -v $CI_PATH/resources:/etc/riak/ tutum/riak

until [[ `docker logs $NAME 2>&1` =~ .*"INFO success: riak entered RUNNING state"* ]]
do 
  sleep 2
done

echo "Docker setup finished"