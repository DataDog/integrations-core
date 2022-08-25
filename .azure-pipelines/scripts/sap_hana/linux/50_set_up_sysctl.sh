#!/bin/bash

set -ex

# 6GB is proven to be enough for SAP HANA to run.
# The default number of memory addresses is 65536, i.e. 512MB (Linux 64-bit).
# => To get 6GB, we multiply that amount by 12.
sudo sysctl -w vm.max_map_count=$(expr 16 \* 65536)

# Recommended settings on https://developers.sap.com/tutorials/hxe-ua-install-using-docker.html
sudo sysctl -w fs.file-max=20000000
sudo sysctl -w fs.aio-max-nr=262144
sudo sysctl -w vm.memory_failure_early_kill=1

set +ex
