#!/bin/bash

apt-get update
apt-get install -y --no-install-recommends gcc git libssl-dev g++ make build-essential libsasl2-modules-gssapi-mit krb5-user
cd /tmp && git clone https://github.com/edenhill/librdkafka.git
cd librdkafka && git checkout tags/v2.2.0
./configure && make && make install && ldconfig
cd ../ && rm -rf librdkafka
pip install --no-binary confluent-kafka confluent-kafka
