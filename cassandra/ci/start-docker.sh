#!/bin/bash

# A script to create the Cassandra containers.

set -e

NAME='dd-test-cassandra'
PORT=7199

CASSANDRA_VERSION=${CASSANDRA_VERSION-2.1.14}
# CASSANDRA_VERSION=${CASSANDRA_VERSION-2.0.17}

if docker ps -a | grep dd-test-cassandra >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash cassandra/ci/stop-docker.sh
fi

docker create --expose $PORT --expose 9042 --expose 7000 --expose 7001 --expose 9160 -p $PORT:$PORT -p 9042:9042 -p 7000:7000 -p 7001:7001 -p 9160:9160 -e JMX_PORT=7199 -e LOCAL_JMX='no' -e JVM_OPTS=-Djava.rmi.server.hostname=localhost --name $NAME cassandra:$CASSANDRA_VERSION
 # -e JVM_OPTS=-Djava.rmi.server.hostname=0.0.0.0
# docker ps
# docker ps -a
# docker logs $NAME

# docker cp ./cassandra/ci/cassandra_${CASSANDRA_VERSION}.yaml $NAME:/etc/cassandra/cassandra.yaml
# docker cp $NAME:/etc/cassandra/cassandra.yaml ./cassandra/ci/cassandra_${CASSANDRA_VERSION}.new.yaml
# docker ps
# docker ps -a
# docker logs $NAME

# docker cp ./cassandra/ci/cassandra-env_${CASSANDRA_VERSION}.sh $NAME:/etc/cassandra/cassandra-env.sh
# docker cp $NAME:/etc/cassandra/cassandra-env.sh ./cassandra/ci/cassandra-env_${CASSANDRA_VERSION}.new.sh

# docker ps
# docker ps -a
# docker logs $NAME

cp ./cassandra/ci/jmxremote.password ./cassandra/ci/jmxremote.password.tmp
chmod 400 ./cassandra/ci/jmxremote.password.tmp
docker cp ./cassandra/ci/jmxremote.password.tmp $NAME:/etc/cassandra/jmxremote.password
rm -f ./cassandra/ci/jmxremote.password.tmp

docker start $NAME
# docker exec -it $NAME /bin/bash
docker ps
docker ps -a
docker logs $NAME


IP_ADDR=$(docker inspect ${NAME} | grep '"IPAddress"' | cut -d':' -f2 | cut -d'"' -f2)
IP_ADDR=$(echo $IP_ADDR | cut -d " " -f2)


echo "Your cassandra container is running at $IP_ADDR"

echo 'running'
