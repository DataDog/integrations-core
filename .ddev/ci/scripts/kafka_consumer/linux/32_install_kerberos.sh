#!/bin/bash

set -ex

sudo apt update
sudo apt install -y --no-install-recommends build-essential libkrb5-dev wget software-properties-common lsb-release gcc make python3 python3-pip python3-dev libsasl2-modules-gssapi-mit krb5-user

# Install librdkafka from source since no binaries are available for the distribution we use on the CI:
git clone https://github.com/confluentinc/librdkafka
cd librdkafka
git checkout v2.3.0
sudo ./configure --install-deps --prefix=/usr
make
sudo make install

set +ex
