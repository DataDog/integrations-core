#!/bin/bash

# This script installs FoundationDB on the CI machines to be able to
# * Run integration tests on the machine

set -ex

FOUNDATIONDB_VERSION="6.3.15"
foundationdb_version_from_pyproject_toml=$(grep -e "foundationdb==" foundationdb/pyproject.toml | cut -f 3 -d = | cut -f 1 -d '"')
if [ ${foundationdb_version_from_pyproject_toml} != ${FOUNDATIONDB_VERSION}]; then
    echo "foundationdb/pyproject has version ${foundationdb_version_from_pyproject_toml} but ${0} is installing version ${FOUNDATIONDB_VERSION}. Make sure they're in sync."
    exit 1
fi
TMP_DIR=/tmp/fdb
FDB_URL=https://github.com/apple/foundationdb/releases/download/${FOUNDATIONDB_VERSION}/foundationdb-clients_${FOUNDATIONDB_VERSION}-1_amd64.deb

mkdir -p $TMP_DIR
pushd $TMP_DIR

curl --verbose -LO $FDB_URL

sudo dpkg -i foundationdb-clients_${FOUNDATIONDB_VERSION}-1_amd64.deb
sudo apt-get install -f

popd

set +ex
