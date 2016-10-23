#!/bin/bash

NAME='dd-test-redis'
PORT=6379

# REDIS_VERSION=${FLAVOR_VERSION-2.4.18}
REDIS_VERSION=${FLAVOR_VERSION-2.6.17}
# REDIS_VERSION=${FLAVOR_VERSION-2.8.19}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if docker ps -a | grep dd-test-redis >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash $DIR/stop-docker.sh
fi

if [ "$REDIS_VERSION" == "2.4.18" ];
then
  REDIS_CONTAINER="mtirsel/redis-2.4"
else
  REDIS_CONTAINER="redis:$REDIS_VERSION"
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
  SLAVE=""
  if [ "$REDIS_SERVER" != "noauth" ]; then
    REDIS_MASTER_IP=$(docker inspect dd-test-redis-noauth | grep '"IPAddress"' | cut -d':' -f2 | cut -d'"' -f2)
    REDIS_MASTER_IP=$(echo $REDIS_MASTER_IP | cut -d " " -f2)
    LINK="--link $NAME-noauth:$REDIS_SERVER"
    if [ "$REDIS_SERVER" != "slave_unhealthy" ]; then
      SLAVE="--slaveof $REDIS_MASTER_IP 16379"
    fi
  fi

  docker run -v $DIR/$REDIS_SERVER.conf:/etc/redis.conf $LINK --expose $CONTAINER_PORT_NUM -p $CONTAINER_PORT_NUM:$CONTAINER_PORT_NUM --name $CONTAINER_NAME -d $REDIS_CONTAINER redis-server /etc/redis.conf $SLAVE

  # sleep 5

  CONTAINER_PORT_NUM=$((CONTAINER_PORT_NUM + 10000))

done

# docker run -it -v $DIR/noauth.conf:/etc/redis.conf --expose 16379 -p 16379:16379 --name dd-test-redis-noauth $REDIS_CONTAINER /bin/bash

# docker create --expose 16379 -p 16379:16379 --name $NAME-noauth $REDIS_CONTAINER redis-server /etc/redis.conf
# docker create --expose 26379 -p 26379:26379 --name $NAME-auth $REDIS_CONTAINER redis-server /etc/redis.conf
# docker create --expose 36379 -p 36379:36379 --name $NAME-slave_healthy $REDIS_CONTAINER redis-server /etc/redis.conf
# docker create --expose 46379 -p 46379:46379 --name $NAME-slave_unhealthy $REDIS_CONTAINER redis-server /etc/redis.conf
#
# docker cp ./redisdb/ci/noauth.conf $NAME-noauth:/etc/redis.conf
# docker cp ./redisdb/ci/auth.conf $NAME-auth:/etc/redis.conf
# docker cp ./redisdb/ci/slave_healthy.conf $NAME-slave_healthy:/etc/redis.conf
# docker cp ./redisdb/ci/slave_unhealthy.conf $NAME-slave_unhealthy:/etc/redis.conf
#
# docker start $NAME-noauth
# docker start $NAME-auth
# docker start $NAME-slave_healthy
# docker start $NAME-slave_unhealthy
