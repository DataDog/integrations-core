#!/bin/bash

set -ex

sudo apt-get update
sudo apt-get install -y --no-install-recommends tdsodbc unixodbc-dev

set +ex
