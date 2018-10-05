#!/bin/bash

set -ex

# Stop any services that bind to ports we need.
if [[ "$CHECK" =~ ^$|couchbase|mcache ]]; then
    sudo service memcached stop
    while sudo lsof -Pi :11211 -sTCP:LISTEN -t; do sleep 1; done
fi

if [[ "$CHECK" =~ ^$|pgbouncer|postgres ]]; then
    sudo service postgresql stop
    while sudo lsof -Pi :5432 -sTCP:LISTEN -t; do sleep 1; done
fi

# Turn off hugepages and defrag
(echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled || true)
(echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag || true)

set +ex
