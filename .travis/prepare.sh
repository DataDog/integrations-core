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

set +ex
