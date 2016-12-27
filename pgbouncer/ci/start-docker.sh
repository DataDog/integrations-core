#!/bin/bash

# A script to create the postgres containers.

function wait_for {
    while netstat -lnt | awk "\$4 ~ /:$1\$/ {exit 1}"; do sleep 1; done
    echo "port $1 active!"
}

set -e

PGNAME='dd-test-postgres'
PGBNAME='dd-test-pgbouncer'
PORT=15432
CI_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if docker ps | grep dd-test-postgres >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash postgres/ci/stop-docker.sh
fi

echo 'Installing Postgres'
docker run --name $PGNAME -v $CI_PATH/resources/pg:/docker-entrypoint-initdb.d -e POSTGRES_PASSWORD=datadog -d postgres:latest

until [[ `docker logs $PGNAME 2>&1` =~ .*"PostgreSQL init process complete" ]];
do
  sleep 2
done

echo 'Postgres is running, installing PgBouncer'

docker run -d --name $PGBNAME --link $PGNAME:postgres -v $CI_PATH/resources/pgb:/etc/pgbouncer:ro -p 16432:6432 kotaimen/pgbouncer

echo 'Docker setup finished'
