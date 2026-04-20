#!/bin/bash

set -ex

sudo apt update
sudo apt install -y --no-install-recommends build-essential libkrb5-dev libzstd-dev wget software-properties-common lsb-release gcc make python3 python3-pip python3-dev libsasl2-modules-gssapi-mit krb5-user

# Install librdkafka from source since no binaries are available for the distribution we use on the CI:
LIBRDKAFKA_VERSION="v2.13.2"
LIBRDKAFKA_SHA256="14972092e4115f6e99f798a7cb420cbf6daa0c73502b3c52ae42fb5b418eea8f"
LIBRDKAFKA_TARBALL=".tar.gz"

wget "https://github.com/confluentinc/librdkafka/archive/refs/tags/"
echo "  " | sha256sum -c -
tar -xzf ""
cd "librdkafka-"
sudo ./configure --install-deps --prefix=/usr
make
sudo make install

set +ex
