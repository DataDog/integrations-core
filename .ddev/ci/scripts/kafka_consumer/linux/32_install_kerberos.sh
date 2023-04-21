#!/bin/bash

set -ex

sudo apt-get update
sudo apt install build-essential
sudo apt-get install -y --no-install-recommends libkrb5-dev wget software-properties-common lsb-release gcc make python3 python3-pip python3-dev libsasl2-modules-gssapi-mit krb5-user

# Install the latest version of librdkafka:
wget -qO - https://packages.confluent.io/deb/7.3/archive.key | sudo apt-key add -
sudo add-apt-repository "deb https://packages.confluent.io/clients/deb $(lsb_release -cs) main"
sudo apt update
sudo apt install -y librdkafka-dev

set +ex
