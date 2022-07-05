#!/bin/bash

# This script installs IBM MQ development version on the CI machines to be able to
# * Compile pymqi image
# * Run integration tests on the machine

set -ex

IBM_DB_FOLDER=/opt/ibm_db
IBM_DB_HOME=$IBM_DB_FOLDER/clidriver
DB2_CLI_URL=https://ddintegrations.blob.core.windows.net/ibm-db2/linuxx64_odbc_cli.tar.gz


sudo apt-get update
sudo apt-get install -y --no-install-recommends gcc libxml2 tar

echo "Downloading ODBC clidriver"

mkdir -p $IBM_DB_FOLDER
pushd $IBM_DB_FOLDER

  # Retry necessary due to flaky download that might trigger:
  # curl: (56) OpenSSL SSL_read: SSL_ERROR_SYSCALL, errno 110
  for i in 2 4 8 16 32; do
    curl --verbose -LO $DB2_CLI_URL && break
    echo "[INFO] Wait $i seconds and retry curl download"
    sleep $i
  done

  echo "Extracting ODBC clidriver"
  tar -zxvf ./*.tar.gz

popd

chmod -R a+xr $IBM_DB_HOME
ls $IBM_DB_HOME
ls $IBM_DB_HOME/lib

export LD_LIBRARY_PATH=$IBM_DB_HOME/lib:$LD_LIBRARY_PATH
ldconfig

set +ex
