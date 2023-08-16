#!/bin/bash

set -ex

sudo sysctl -w vm.max_map_count=262144

set +ex
