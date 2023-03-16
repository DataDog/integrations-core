#!/bin/bash

kinit -k -t /var/lib/secret/kafka-admin.key admin/for-kafka
kafka-acls --bootstrap-server broker.kerberos-demo.local:9092 --command-config /etc/kafka/command.properties --add --allow-principal User:kafka_producer --producer --topic=*

kinit -k -t /var/lib/secret/kafka-admin.key admin/for-kafka
kafka-acls --bootstrap-server broker.kerberos-demo.local:9092 --command-config /etc/kafka/command.properties --add --allow-principal User:kafka_consumer --consumer --topic=* --group=*
