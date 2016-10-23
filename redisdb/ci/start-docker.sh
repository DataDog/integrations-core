#!/bin/bash

NAME='dd-test-redis'
PORT=6379

REDIS_VERSION=${FLAVOR_VERSION-2.4.18}
# REDIS_VERSION=${FLAVOR_VERSION-2.6.17}
# REDIS_VERSION=${FLAVOR_VERSION-2.8.19}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if docker ps -a | grep dd-test-redis >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash $DIR/stop-docker.sh
fi

REDIS_STDIN_CONFIG=false

if [ "$REDIS_VERSION" == "2.4.18" ];
then
  REDIS_CONTAINER="mtirsel/redis-2.4"
else
  REDIS_CONTAINER="redis:$REDIS_VERSION"
  REDIS_STDIN_CONFIG=true
fi

REDIS_SERVERS=(
  noauth
  auth
  slave_healthy
  slave_unhealthy
)

CONTAINER_PORT_NUM=16379

for REDIS_SERVER in ${REDIS_SERVERS[*]}; do
  CONTAINER_NAME=$NAME-$REDIS_SERVER

  LINK=""

  cp -f $DIR/$REDIS_SERVER.conf $DIR/$REDIS_SERVER.tmp.conf

  if [ "$REDIS_SERVER" != "noauth" ]; then
    REDIS_MASTER_IP=$(docker inspect dd-test-redis-noauth | grep '"IPAddress"' | cut -d':' -f2 | cut -d'"' -f2)
    REDIS_MASTER_IP=$(echo $REDIS_MASTER_IP | cut -d " " -f2)
    LINK="--link $NAME-noauth:$REDIS_SERVER"
    if [ "$REDIS_SERVER" != "slave_unhealthy" ]; then
      echo "slaveof $REDIS_MASTER_IP 16379" >> $DIR/$REDIS_SERVER.tmp.conf
    fi
  fi

  docker run -v $DIR/$REDIS_SERVER.tmp.conf:/etc/redis.conf $LINK --expose $CONTAINER_PORT_NUM -p $CONTAINER_PORT_NUM:$CONTAINER_PORT_NUM --name $CONTAINER_NAME -d $REDIS_CONTAINER redis-server /etc/redis.conf

  CONTAINER_PORT_NUM=$((CONTAINER_PORT_NUM + 10000))

done
