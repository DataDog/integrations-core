#!/bin/bash

set -ex

if [ -z "$CHECK" ]; then
    OUT=$(ddev test --list)
    if [[ "$OUT" != *"cacti"* ]]; then
        exit 0
    fi
else
    if [ $CHECK != "cacti" ]; then
        exit 0
    fi
fi

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  rrdtool \
  librrd-dev \
  libpython-dev \
  build-essential

set +ex
