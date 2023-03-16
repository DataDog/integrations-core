#!/bin/bash

# TODO Remove this script once the library is installed at the agent level

apt-get update
apt-get install -y --no-install-recommends gcc git libssl-dev g++ make build-essential libsasl2-modules-gssapi-mit krb5-user
cd /tmp && git clone https://github.com/edenhill/librdkafka.git
cd librdkafka && git checkout tags/v2.0.2
./configure && make && make install && ldconfig
cd ../ && rm -rf librdkafka
pip install --no-binary confluent-kafka confluent-kafka

chmod 777 -R /var/lib/secret
kinit -R -t "/var/lib/secret/kafka-client.key" -k kafka_producer