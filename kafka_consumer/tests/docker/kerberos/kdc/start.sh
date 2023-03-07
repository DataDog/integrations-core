#!/usr/bin/env bash

rm -r /var/lib/secret/*

kadmin.local -w password -q "modprinc -maxrenewlife 11days +allow_renewable krbtgt/TEST.CONFLUENT.IO"  > /dev/null

# Kafka service principal:
kadmin.local -w password -q "add_principal -randkey kafka/broker.kerberos-demo.local@TEST.CONFLUENT.IO"  > /dev/null
kadmin.local -w password -q "modprinc -maxlife 11days -maxrenewlife 11days +allow_renewable kafka/broker.kerberos-demo.local@TEST.CONFLUENT.IO"  > /dev/null
kadmin.local -w password -q "add_principal -randkey kafka/broker2.kerberos-demo.local@TEST.CONFLUENT.IO"  > /dev/null
kadmin.local -w password -q "modprinc -maxlife 11days -maxrenewlife 11days +allow_renewable kafka/broker2.kerberos-demo.local@TEST.CONFLUENT.IO"  > /dev/null

# Zookeeper service principal:
kadmin.local -w password -q "add_principal -randkey zookeeper/zookeeper.kerberos-demo.local@TEST.CONFLUENT.IO"  > /dev/null
kadmin.local -w password -q "modprinc -maxlife 11days -maxrenewlife 11days +allow_renewable zookeeper/zookeeper.kerberos-demo.local@TEST.CONFLUENT.IO"  > /dev/null

# Create a principal with which to connect to Zookeeper from brokers - NB use the same credential on all brokers!
kadmin.local -w password -q "add_principal -randkey zkclient@TEST.CONFLUENT.IO"  > /dev/null
kadmin.local -w password -q "modprinc -maxlife 11days -maxrenewlife 11days +allow_renewable zkclient@TEST.CONFLUENT.IO"  > /dev/null

# Create client principals to connect in to the cluster:
kadmin.local -w password -q "add_principal -randkey kafka_producer@TEST.CONFLUENT.IO"  > /dev/null
kadmin.local -w password -q "modprinc -maxlife 11days -maxrenewlife 11days +allow_renewable kafka_producer@TEST.CONFLUENT.IO"  > /dev/null
kadmin.local -w password -q "add_principal -randkey kafka_producer/instance_demo@TEST.CONFLUENT.IO"  > /dev/null
kadmin.local -w password -q "modprinc -maxlife 11days -maxrenewlife 11days +allow_renewable kafka_producer/instance_demo@TEST.CONFLUENT.IO"  > /d
kadmin.local -w password -q "add_principal -randkey kafka_consumer@TEST.CONFLUENT.IO"  > /dev/null
kadmin.local -w password -q "modprinc -maxlife 11days -maxrenewlife 11days +allow_renewable kafka_consumer@TEST.CONFLUENT.IO"  > /dev/null

# Create an admin principal for the cluster, which we'll use to setup ACLs.
# Look after this - its also declared a super user in broker config.
kadmin.local -w password -q "add_principal -randkey admin/for-kafka@TEST.CONFLUENT.IO"  > /dev/null
kadmin.local -w password -q "modprinc -maxlife 11days -maxrenewlife 11days +allow_renewable admin/for-kafka@TEST.CONFLUENT.IO"  > /dev/null

kadmin.local -w password -q "ktadd  -k /var/lib/secret/broker.key -norandkey kafka/broker.kerberos-demo.local@TEST.CONFLUENT.IO " > /dev/null
kadmin.local -w password -q "ktadd  -k /var/lib/secret/broker2.key -norandkey kafka/broker2.kerberos-demo.local@TEST.CONFLUENT.IO " > /dev/null
kadmin.local -w password -q "ktadd  -k /var/lib/secret/zookeeper.key -norandkey zookeeper/zookeeper.kerberos-demo.local@TEST.CONFLUENT.IO " > /dev/null
kadmin.local -w password -q "ktadd  -k /var/lib/secret/zookeeper-client.key -norandkey zkclient@TEST.CONFLUENT.IO " > /dev/null
kadmin.local -w password -q "ktadd  -k /var/lib/secret/kafka-client.key -norandkey kafka_producer@TEST.CONFLUENT.IO " > /dev/null
kadmin.local -w password -q "ktadd  -k /var/lib/secret/kafka-client.key -norandkey kafka_producer/instance_demo@TEST.CONFLUENT.IO " > /dev/null
kadmin.local -w password -q "ktadd  -k /var/lib/secret/kafka-client.key -norandkey kafka_consumer@TEST.CONFLUENT.IO " > /dev/null
kadmin.local -w password -q "ktadd  -k /var/lib/secret/kafka-admin.key -norandkey admin/for-kafka@TEST.CONFLUENT.IO " > /dev/null

chmod a+r /var/lib/secret/broker.key
chmod a+r /var/lib/secret/broker2.key
chmod a+r /var/lib/secret/zookeeper.key
chmod a+r /var/lib/secret/zookeeper-client.key
chmod a+r /var/lib/secret/kafka-client.key
chmod a+r /var/lib/secret/kafka-admin.key

/usr/sbin/krb5kdc -n