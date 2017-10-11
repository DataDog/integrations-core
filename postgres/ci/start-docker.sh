#!/bin/bash

# A script to create the postgres containers.

function wait_for {
    while netstat -lnt | awk "\$4 ~ /:$1\$/ {exit 1}"; do sleep 1; done
    echo "port $1 active!"
}

set -e

NAME='dd-test-postgres'
PORT=15432
CI_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if docker ps | grep dd-test-postgres >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash postgres/ci/stop-docker.sh
fi

POSTGRES00_ID=$(docker run -p $PORT:5432 --name $NAME -v $CI_PATH/resources:/docker-entrypoint-initdb.d -e POSTGRES_PASSWORD=datadog -d postgres:${FLAVOR_VERSION})
POSTGRES00_IP=$(docker inspect ${POSTGRES00_ID} | grep '"IPAddress"' | cut -d':' -f2 | cut -d'"' -f2)
POSTGRES00_IP=$(echo $POSTGRES00_IP | cut -d " " -f2)

until [[ `docker logs $NAME 2>&1` =~ .*"PostgreSQL init process complete" ]];
do
  sleep 2
done
echo 'running'

echo 'Docker setup finished'
