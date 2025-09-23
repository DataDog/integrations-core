#!/bin/bash

set -ex

# Turn off hugepages and defrag, see:
# https://github.com/DataDog/integrations-core/pull/2134
(echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled || true)
(echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag || true)

set +ex
