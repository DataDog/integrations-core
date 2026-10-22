#!/bin/bash

set -ex

sudo apt update
sudo apt install -y --no-install-recommends build-essential libkrb5-dev libzstd-dev wget software-properties-common lsb-release gcc make python3 python3-pip python3-dev libsasl2-modules-gssapi-mit krb5-user

# Install librdkafka from source since no binaries are available for the distribution we use on the CI:
LIBRDKAFKA_VERSION="v2.13.2"
LIBRDKAFKA_SHA256="14972092e4115f6e99f798a7cb420cbf6daa0c73502b3c52ae42fb5b418eea8f"
LIBRDKAFKA_TARBALL="${LIBRDKAFKA_VERSION}.tar.gz"
# Test against the same librdkafka the Agent ships: apply the PATCHES from .builders/images/linux-*/build_script.sh
LIBRDKAFKA_PATCHES_DIR="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)/.builders/patches"
LIBRDKAFKA_PATCHES="librdkafka-fix-coord-request-uaf.patch librdkafka-fix-offsetfetch-null-cgrp.patch"

wget "https://github.com/confluentinc/librdkafka/archive/refs/tags/${LIBRDKAFKA_TARBALL}"
echo "${LIBRDKAFKA_SHA256}  ${LIBRDKAFKA_TARBALL}" | sha256sum -c -
tar -xzf "${LIBRDKAFKA_TARBALL}"
cd "librdkafka-${LIBRDKAFKA_VERSION#v}"
for patch in ${LIBRDKAFKA_PATCHES}; do
    patch -p1 -i "${LIBRDKAFKA_PATCHES_DIR}/${patch}"
done
sudo ./configure --install-deps --prefix=/usr
make
sudo make install

set +ex
