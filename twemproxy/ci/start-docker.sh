#!/bin/bash

# A script to create the MySQL containers.

function wait_for {
    while netstat -lnt | awk "\$4 ~ /:$1\$/ {exit 1}"; do sleep 1; done
    echo "port $1 active!"
}

set -e

NAME='dd-ci-twemproxy'
PORT=6100
DOCKER_ADDR=$1
CI_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if docker ps | grep dd-ci-twemproxy >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash $CI_PATH/stop-docker.sh
fi

REDIS_A_ID=$(docker run --name=dd-ci-twemproxy-redis-A -d -p 6101:6379 redis)
REDIS_B_ID=$(docker run --name=dd-ci-twemproxy-redis-B -d -p 6102:6379 redis)
wait_for 6101
wait_for 6102

ETCD_ID=$(docker run -d -v /usr/share/ca-certificates/:/etc/ssl/certs -p 4001:4001 -p 2380:2380 -p 2379:2379 --name=dd-ci-twemproxy-etcd quay.io/coreos/etcd:v2.2.0 \
      -name etcd0 \
      -advertise-client-urls http://0.0.0.0:2379,http://0.0.0.0:4001,http://$DOCKER_ADDR:2379,http://$DOCKER_ADDR:4001 \
      -listen-client-urls http://0.0.0.0:2379,http://0.0.0.0:4001 \
      -initial-advertise-peer-urls http://0.0.0.0:2380 \
      -listen-peer-urls http://0.0.0.0:2380 \
      -initial-cluster-token etcd-cluster-1 \
      -initial-cluster etcd0=http://0.0.0.0:2380 \
      -initial-cluster-state new)

wait_for 2379
wait_for 4001

# set etcd config
curl -L -X PUT http://127.0.0.1:2379/v2/keys/services/redis/01 -d value="$DOCKER_ADDR:6101"
curl -L -X PUT http://127.0.0.1:2379/v2/keys/services/redis/02 -d value="$DOCKER_ADDR:6102"
curl -L -X PUT http://127.0.0.1:2379/v2/keys/services/twemproxy/port -d value="$PORT"
curl -L -X PUT http://127.0.0.1:2379/v2/keys/services/twemproxy/host -d value="$DOCKER_ADDR"

# publish the redis host:ip information into etcd
TWEMPROXY_ID=$(docker run --name=dd-ci-twemproxy -d -p 6100:6100 -p 6222:6222 -e ETCD_HOST=$DOCKER_ADDR:4001 jgoodall/twemproxy)

# until [[ `docker logs dd-ci-twemproxy 2>&1` =~ .*"MySQL init process done. Ready for start up" ]];
# do
#   sleep 2
# done

echo 'Docker setup finished'
