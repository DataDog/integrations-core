#!/bin/bash

set -ex

# The default number of memory addresses is 65536, i.e. 512MB (Linux 64-bit).
# => To get 6GB, we multiply that amount by 12.
sudo sysctl -w vm.max_map_count=$(expr 16 \* 65536)

set +ex
