#!/bin/bash

set -ex

# Allocate 3GB for activemq
# The default number of memory addresses is 65536, i.e. 512MB (Linux 64-bit).
# => To get 3GB, we multiply that amount by 6.
sudo sysctl -w vm.max_map_count=$(expr 6 \* 65536)

set +ex
