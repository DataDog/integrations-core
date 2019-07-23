#!/bin/bash

sed -i 's/HADOOP_CLIENT_OPTS= /HADOOP_CLIENT_OPTS=/' /opt/hive/bin/ext/metastore.sh

/opt/hive/bin/schematool -dbType derby -initSchema

# Starting the metastore with the JMX options
export HADOOP_CLIENT_OPTS=$JMX_METASTORE

/opt/hive/bin/hive --service metastore --verbose &

unset HADOOP_CLIENT_OPTS

# Waiting for the metastore setup
while ! nc -z localhost 9083; do   
  sleep 3
done

hadoop fs -mkdir       /tmp
hadoop fs -mkdir -p    /user/hive/warehouse
hadoop fs -chmod g+w   /tmp
hadoop fs -chmod g+w   /user/hive/warehouse

# Starting the hiveserver with the JMX options
export HADOOP_CLIENT_OPTS=$JMX_HIVESERVER

cd $HIVE_HOME/bin
./hiveserver2 --hiveconf hive.server2.enable.doAs=false &

unset HADOOP_CLIENT_OPTS

while true; do sleep 1000; done
