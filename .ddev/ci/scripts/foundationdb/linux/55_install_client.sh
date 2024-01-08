#!/bin/bash

# This script installs FoundationDB on the CI machines to be able to
# * Run integration tests on the machine

set -ex

TMP_DIR=/tmp/fdb
FDB_URL=https://github.com/apple/foundationdb/releases/download/7.3.27/foundationdb-clients_7.3.27-1_amd64.deb

mkdir -p $TMP_DIR
pushd $TMP_DIR

curl --verbose -LO $FDB_URL

sudo dpkg -i foundationdb-clients_7.3.27-1_amd64.deb
sudo apt-get install -f

popd

set +ex
