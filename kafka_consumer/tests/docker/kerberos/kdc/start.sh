#!/usr/bin/env bash

rm /var/lib/secret/*.key

# Kafka service principal:
kadmin.local -w password -q "add_principal -randkey kafka/broker.kerberos-demo.local@TEST.CONFLUENT.IO"  > /dev/null

# Zookeeper service principal:
kadmin.local -w password -q "add_principal -randkey zookeeper/zookeeper.kerberos-demo.local@TEST.CONFLUENT.IO"  > /dev/null

# Create a principal with which to connect to Zookeeper from brokers - NB use the same credential on all brokers!
kadmin.local -w password -q "add_principal -randkey zkclient@TEST.CONFLUENT.IO"  > /dev/null

# Create client principals to connect in to the cluster:
kadmin.local -w password -q "add_principal -randkey kafka/localhost@TEST.CONFLUENT.IO"  > /dev/null

kadmin.local -w password -q "ktadd  -k /var/lib/secret/zookeeper.key -norandkey zookeeper/zookeeper.kerberos-demo.local@TEST.CONFLUENT.IO " > /dev/null
kadmin.local -w password -q "ktadd  -k /var/lib/secret/zookeeper-client.key -norandkey zkclient@TEST.CONFLUENT.IO " > /dev/null
kadmin.local -w password -q "ktadd  -k /var/lib/secret/localhost.key -norandkey kafka/localhost@TEST.CONFLUENT.IO " > /dev/null

chmod 777 /var/lib/secret/broker.key
chmod 777 /var/lib/secret/zookeeper.key
chmod 777 /var/lib/secret/zookeeper-client.key
chmod 777 /var/lib/secret/localhost.key

/usr/sbin/krb5kdc -n
