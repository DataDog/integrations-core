#!/bin/bash

set -ex

if [ -z "$CHECK" ]; then
    OUT=$(ddev test --list)
    if [[ "$OUT" != *"sqlserver"* ]]; then
        exit 0
    fi
else
    if [ $CHECK != "sqlserver" ]; then
        exit 0
    fi
fi

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  tdsodbc \
  unixodbc-dev

set +ex
