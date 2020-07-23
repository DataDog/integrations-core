#!/bin/bash

set -ex

# https://github.com/aerospike/aerospike-client-c#build-prerequisites
sudo apt-get update
sudo apt-get install -y --no-install-recommends libc6-dev libssl-dev autoconf automake libtool g++ ncurses-dev

# The binary wheels on PyPI are not yet compatible with OpenSSL 1.1.0+, see:
# https://github.com/aerospike/aerospike-client-python/issues/214#issuecomment-385451007
# https://github.com/aerospike/aerospike-client-python/issues/227#issuecomment-423220411
git clone https://github.com/aerospike/aerospike-client-c.git /tmp/aerospike-client-c
cd /tmp/aerospike-client-c

# This needs to be kept in sync with whatever the Python library was built with.
# For example, version 3.10.0 was built with version 4.6.10 of the C library, see:
# https://github.com/aerospike/aerospike-client-python/blob/3.10.0/setup.py#L32-L33
git checkout 4.6.10

git submodule update --init
make clean
make

set +ex
