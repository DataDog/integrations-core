#!/usr/bin/env bash

# This script allows you to install the latest version of librdkafka in the agent container
# Thanks to this you can run the kerberos test even if the agent is shipped with a different version of librdkafka
# WARN: YOU STILL NEED TO BUMP THE VERSION OF LIBRDKAFKA IN THE AGENT REPO

# Format:
# define RD_KAFKA_VERSION   0x020200ff
# Interpreted as hex MM.mm.rr.xx:
#
# MM = Major
# mm = minor
# rr = revision
# xx = pre-release id (0xff is the final release)
# So in the example: 2.2.0
VERSION_HEX=$(grep "#define RD_KAFKA_VERSION" /opt/datadog-agent/embedded/include/librdkafka/rdkafka.h | cut -d ' ' -f 3)

if [ "$VERSION_HEX" != "0x${LIBRDKAFKA_VERSION}ff" ]; then
    apt-get update
    apt-get install --no-install-recommends --yes \
                build-essential \
                git \
                libsasl2-dev \
                libssl-dev \
                libzstd-dev

    git clone --branch v$CONFLUENT_KAFKA_VERSION https://github.com/edenhill/librdkafka.git

    cd librdkafka

    export LDFLAGS="-L/opt/datadog-agent/embedded/lib -I/opt/datadog-agent/embedded/include"
    export CFLAGS="-L/opt/datadog-agent/embedded/lib -I/opt/datadog-agent/embedded/include"
    export LD_RUN_PATH="/opt/datadog-agent/embedded/lib"

    ./configure --enable-sasl --prefix=/opt/datadog-agent/embedded
    make
    make install

    pip uninstall -y confluent-kafka
    pip install --no-binary confluent-kafka confluent-kafka==$CONFLUENT_KAFKA_VERSION
fi

