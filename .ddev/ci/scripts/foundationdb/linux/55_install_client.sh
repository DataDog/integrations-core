#!/bin/bash

# This script installs FoundationDB on the CI machines to be able to
# * Run integration tests on the machine

set -ex

# Try the runner image's package index first to avoid an unnecessary mirror refresh.
apt_install() {
  if sudo timeout 120 apt-get install "$@"; then
    return
  fi
  if ! sudo timeout 60 apt-get update; then
    sleep 10
    sudo timeout 60 apt-get update || return 1
  fi
  sudo timeout 120 apt-get install "$@" || return 1
}

TMP_DIR=/tmp/fdb
FDB_URL=https://github.com/apple/foundationdb/releases/download/6.3.15/foundationdb-clients_6.3.15-1_amd64.deb

mkdir -p $TMP_DIR
pushd $TMP_DIR

curl --verbose -LO $FDB_URL

sudo dpkg -i foundationdb-clients_6.3.15-1_amd64.deb
apt_install -f

popd

set +ex
