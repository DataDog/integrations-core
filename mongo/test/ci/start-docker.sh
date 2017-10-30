#!/bin/bash

set -e

PORT=47017
PORT1=$(( $PORT + 1 ))
PORT2=$(( $PORT + 2 ))

NAME='dd-test-mongo'
NAME1='dd-test-mongo-1'
NAME2='dd-test-mongo-2'

MONGO_VERSION=${FLAVOR_VERSION-3.0.1}

if docker ps | grep dd-test-mongo >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash mongo/ci/stop-docker.sh
fi

SHARD00_ID=$(docker run -p $PORT:$PORT --expose $PORT --name $NAME -d mongo:$MONGO_VERSION mongod --replSet rs0 --bind_ip 0.0.0.0 --port $PORT)
SHARD00_IP=$(docker inspect ${SHARD00_ID} | grep '"IPAddress"' | cut -d':' -f2 | cut -d'"' -f2)
SHARD00_IP=$(echo $SHARD00_IP | cut -d " " -f2)

SHARD01_ID=$(docker run --link=$NAME --expose $PORT1 -p $PORT1:$PORT1 --name $NAME1 -d mongo:$MONGO_VERSION mongod --replSet rs0 --bind_ip 0.0.0.0 --port $PORT1)
SHARD01_IP=$(docker inspect ${SHARD01_ID} | grep '"IPAddress"' | cut -d':' -f2 | cut -d'"' -f2)
SHARD01_IP=$(echo $SHARD01_IP | cut -d " " -f2)

SHARD02_ID=$(docker run --link=$NAME --expose $PORT2 -p $PORT2:$PORT2 --name $NAME2 -d mongo:$MONGO_VERSION mongod --replSet rs0 --bind_ip 0.0.0.0 --port $PORT2)
SHARD02_IP=$(docker inspect ${SHARD02_ID} | grep '"IPAddress"' | cut -d':' -f2 | cut -d'"' -f2)
SHARD02_IP=$(echo $SHARD02_IP | cut -d " " -f2)

echo "Your shard container ${SHARD00_ID} listen on ip: ${SHARD00_IP}:$PORT (waiting that becomes ready)"
until docker logs ${SHARD00_ID} | grep "waiting for connections" >/dev/null;
do
    sleep 2
done
echo "Your shard container ${SHARD01_ID} listen on ip: ${SHARD01_IP}:$PORT1 (waiting that becomes ready)"
until docker logs ${SHARD01_ID} | grep "waiting for connections" >/dev/null;
do
    sleep 2
done
echo "Your shard container ${SHARD02_ID} listen on ip: ${SHARD02_IP}:$PORT2 (waiting that becomes ready)"
until docker logs ${SHARD02_ID} | grep "waiting for connections" >/dev/null;
do
    sleep 2
done

echo 'docker exec -it $NAME mongo --eval "rs.initiate();" localhost:$PORT'
docker exec -it $NAME mongo --eval "rs.initiate();" localhost:$PORT

echo 'docker exec -it $NAME mongo --eval cfg = rs.conf(); cfg.members[0].host = "localhost:$PORT"; rs.reconfig(cfg); printjson(rs.conf()); localhost:$PORT'
echo "cfg = rs.conf(); cfg.members[0].host = '$SHARD00_IP:$PORT'; rs.reconfig(cfg); printjson(rs.conf());"
docker exec -it $NAME mongo --eval "cfg = rs.conf(); cfg.members[0].host = '$SHARD00_IP:$PORT'; rs.reconfig(cfg); printjson(rs.conf());" localhost:$PORT

sleep 2

echo 'docker exec -it $NAME mongo --eval "printjson(rs.add(\'$SHARD01_IP:$PORT1\\')); printjson(rs.status());" localhost:$PORT'
docker exec -it $NAME mongo --eval "printjson(rs.add('$SHARD01_IP:$PORT1')); printjson(rs.status());" localhost:$PORT

echo 'docker exec -it $NAME mongo --eval "printjson(rs.add(\'$SHARD02_IP:$PORT2\\')); printjson(rs.status());" localhost:$PORT'
docker exec -it $NAME mongo --eval "printjson(rs.add('$SHARD02_IP:$PORT2')); printjson(rs.status());" localhost:$PORT

docker exec -it $NAME mongo --eval "db.getMongo().getDBNames()" localhost:$PORT/test
docker exec -it $NAME mongo --eval "db.getCollectionNames()" localhost:$PORT/test

sleep 2

echo "Checking if shards are initialized and then waiting until they are initialized"
until docker exec -it $NAME mongo --eval "printjson(rs.status());" localhost:$PORT | grep '"stateStr" : "SECONDARY"' >/dev/null;
do
    sleep 2
done

echo "The shards have been initialized"

echo 'docker exec -it $NAME mongo --eval cfg = rs.conf(); cfg.members[0].host = "localhost:$PORT"; rs.reconfig(cfg); printjson(rs.conf()); localhost:$PORT'
echo "cfg = rs.conf(); cfg.members[0].host = '$SHARD00_IP:$PORT'; rs.reconfig(cfg); printjson(rs.conf());"
docker exec -it $NAME mongo --eval "cfg = rs.conf(); cfg.members[0].host = '$SHARD00_IP:$PORT'; rs.reconfig(cfg); printjson(rs.conf());" localhost:$PORT

echo "Setting test user"
docker exec -it $NAME mongo --eval 'db.createUser({ user: "testUser", pwd: "testPass", roles: [ { role: "read", db: "test" } ] })' localhost:$PORT/authDB

echo "Setting test user"
docker exec -it $NAME mongo --eval 'db.createUser({ user: "testUser2", pwd: "testPass2", roles: [ { role: "read", db: "test" } ] })' localhost:$PORT/test
