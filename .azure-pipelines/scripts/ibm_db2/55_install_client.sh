#!/bin/bash

# This script installs IBM MQ development version on the CI machines to be able to
# * Compile pymqi image
# * Run integration tests on the machine

set -ex

IBM_DB_FOLDER=/opt/ibm_db
DB2_URL=https://ddintegrations.blob.core.windows.net/ibm-db2/linuxx64_odbc_cli.tar.gz

mkdir -p $IBM_DB_FOLDER
pushd $IBM_DB_FOLDER

  # Retry necessary due to flaky download that might trigger:
  # curl: (56) OpenSSL SSL_read: SSL_ERROR_SYSCALL, errno 110
  for i in 2 4 8 16 32; do
    curl --verbose -LO $DB2_URL && break
    echo "[INFO] Wait $i seconds and retry curl download"
    sleep $i
  done

  tar -zxvf ./*.tar.gz

popd

ls $IBM_DB_FOLDER
ls $IBM_DB_FOLDER/clidriver

set +ex
