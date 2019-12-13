#!/bin/bash

set -ex

# Allocate 2GB for activemq
# The default number of memory addresses is 65536, i.e. 512MB (Linux 64-bit).
# => To get 2GB, we multiply that amount by 4.
sudo sysctl -w vm.max_map_count=$(expr 4 \* 65536)

set +ex
