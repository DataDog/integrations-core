#!/bin/bash

set -ex

sudo sysctl -w vm.max_map_count=$(expr 6 \* 65536)

set +ex
