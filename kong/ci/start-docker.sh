#!/bin/bash

set -e

NAME='dd-test-kong'
NAME_DB="$NAME-database"

KONG_VERSION=${FLAVOR_VERSION-0.8.1}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if docker ps | grep $NAME >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash $DIR/stop-docker.sh
fi

PORT1=8000
PORT2=8443
PORT3=8001
PORT4=7946

# kong requires a database.
docker run -d --name $NAME_DB -p 9042:9042 cassandra:2.2

# If we add versions, ensure that this log matching works.
WAITED=0
echo 'Waiting for Cassandra to come up'
until [[ `docker logs $NAME_DB 2>&1` =~ .*"Listening for thrift clients" || `docker logs $NAME_DB 2>&1` =~ .*"Created default superuser role 'cassandra'" ]];
do
  echo $WAITED
  if [[ "$WAITED" -eq 20 ]]; then
    echo "The cassandra container has failed to come up"
    docker logs $NAME_DB
    exit 1
  fi
  sleep 2
  WAITED=$(($WAITED+1))
done

docker run -d --name $NAME --link $NAME_DB:kong-database \
  -e "KONG_DATABASE=cassandra" -e "KONG_CASSANDRA_CONTACT_POINTS=$NAME_DB" -e "KONG_PG_HOST=$NAME_DB" \
  -p 8000:8000 -p 8443:8443  -p 8001:8001  -p 7946:7946  -p 7946:7946/udp mashape/kong:0.8.1


WAITED=0
echo 'Waiting for Kong to come up'
until [[ `curl localhost:8001/status 2>/dev/null || echo 'emptycurl'` != 'emptycurl' ]]; do
  echo $WAITED
  # this container takes forever to come up, otherwise this would be set much lower
  if [[ "$WAITED" -eq "50" ]]; then
    echo "The kong container has failed to come up"
    docker logs $NAME
    exit 1
  fi
  RESP=`curl localhost:8001/status 2>/dev/null || echo 'emptycurl'`
  sleep 2
  WAITED=$(($WAITED+1))
done
