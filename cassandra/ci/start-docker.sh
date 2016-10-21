#!/bin/bash

# A script to create the Cassandra containers.

set -e

NAME='dd-test-cassandra'
PORT=7199

CASSANDRA_VERSION=${FLAVOR_VERSION-2.1.14}
# CASSANDRA_VERSION=${FLAVOR_VERSION-2.0.17}
# CASSANDRA_VERSION=${FLAVOR_VERSION-2.2.8}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if docker ps -a | grep dd-test-cassandra >/dev/null; then
  echo 'the containers already exist, we have to remove them'
  bash $DIR/stop-docker.sh
fi

# Cassandra 2.0.17 overrides the LOCAL_JMX environmental variable.
# So, I'm just enabling it manually instead.
JMX_JVM_OPTS="-Dcom.sun.management.jmxremote.port=$PORT"
JMX_JVM_OPTS="$JMX_JVM_OPTS -Dcom.sun.management.jmxremote.rmi.port=$PORT"
JMX_JVM_OPTS="$JMX_JVM_OPTS -Dcom.sun.management.jmxremote.ssl=false"
JMX_JVM_OPTS="$JMX_JVM_OPTS -Dcom.sun.management.jmxremote.authenticate=true"
JMX_JVM_OPTS="$JMX_JVM_OPTS -Dcom.sun.management.jmxremote.password.file=/etc/cassandra/jmxremote.password"
JMX_JVM_OPTS="$JMX_JVM_OPTS -Djava.rmi.server.hostname=localhost"

docker create --expose $PORT --expose 9042 --expose 7000 --expose 7001 --expose 9160 -p $PORT:$PORT -p 9042:9042 -p 7000:7000 -p 7001:7001 -p 9160:9160 -e JMX_PORT=$PORT -e LOCAL_JMX='no' -e JVM_EXTRA_OPTS="$JMX_JVM_OPTS" --name $NAME cassandra:$CASSANDRA_VERSION

cp ./cassandra/ci/jmxremote.password ./cassandra/ci/jmxremote.password.tmp
chmod 400 ./cassandra/ci/jmxremote.password.tmp
docker cp ./cassandra/ci/jmxremote.password.tmp $NAME:/etc/cassandra/jmxremote.password
rm -f ./cassandra/ci/jmxremote.password.tmp

docker start $NAME

# If we add versions, ensure that this log matching works.
COUNT=0
until [[ `docker logs $NAME 2>&1` =~ .*"Listening for thrift clients" || `docker logs $NAME 2>&1` =~ .*"Created default superuser role 'cassandra'" ]];
do
  sleep 2

done

IP_ADDR=$(docker inspect ${NAME} | grep '"IPAddress"' | cut -d':' -f2 | cut -d'"' -f2)
IP_ADDR=$(echo $IP_ADDR | cut -d " " -f2)

echo "Your cassandra container is running at $IP_ADDR"

echo 'running'
