#!/bin/bash

PORT=37017

NAME='dd-test-tokumx'

set -e

if docker ps | grep dd-test-tokumx >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash tokumx/ci/stop-docker.sh
fi

SHARD00_ID=$(docker run --privileged -p $PORT:$PORT --name $NAME -d datadog/tokumx mongod --bind_ip 0.0.0.0 --port $PORT)
SHARD00_IP=$(docker inspect ${SHARD00_ID} | grep '"IPAddress"' | cut -d':' -f2 | cut -d'"' -f2)
SHARD00_IP=$(echo $SHARD00_IP | cut -d " " -f2)

# msg="replSet info you may need to run replSetInitiate"
msg="waiting for connections"
echo "Your shard container ${SHARD00_ID} listen on ip: ${SHARD00_IP}:$PORT (waiting that becomes ready)"
until docker logs ${SHARD00_ID} | grep "$msg" >/dev/null;
do
    sleep 2
done

echo 'docker exec -it $NAME mongo --eval "printjson(db.serverStatus());" localhost:$PORT'
docker exec -it $NAME mongo localhost:37017 --eval "printjson(db.serverStatus());"

sleep 2
