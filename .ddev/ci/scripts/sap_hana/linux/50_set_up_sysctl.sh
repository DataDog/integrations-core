#!/bin/bash

set -ex

# Recommended settings on https://developers.sap.com/tutorials/hxe-ua-install-using-docker.html
sudo sysctl -w fs.file-max=20000000
sudo sysctl -w fs.aio-max-nr=262144
sudo sysctl -w  vm.max_map_count=270435456  # Doubling the recommended value
sudo sysctl -w vm.memory_failure_early_kill=1

set +ex
