#!/bin/bash

# This script installs IBM MQ development version on the CI machines to be able to
# * Compile pymqi image
# * Run integration tests on the machine

set -ex

IBM_DB_FOLDER=/opt/ibm_db
DB2_URL=https://ddintegrations.blob.core.windows.net/ibm-db2/linuxx64_odbc_cli.tar.gz


sudo apt-get update
sudo apt-get install -y --no-install-recommends gcc libxml2 tar

echo "Downloading ODBC clidriver"

mkdir -p $IBM_DB_FOLDER
pushd $IBM_DB_FOLDER

  # Retry necessary due to flaky download that might trigger:
  # curl: (56) OpenSSL SSL_read: SSL_ERROR_SYSCALL, errno 110
  for i in 2 4 8 16 32; do
    curl --verbose -LO $DB2_URL && break
    echo "[INFO] Wait $i seconds and retry curl download"
    sleep $i
  done

  echo "Extracting ODBC clidriver"
  tar -zxvf ./*.tar.gz

popd

chmod -R a+xr /opt/ibm_db/clidriver
ls /opt/ibm_db
ls /opt/ibm_db/clidriver
echo "Finding libdb2.so.1"
find / -name libdb2.so.1


set +ex
