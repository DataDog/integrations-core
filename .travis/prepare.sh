#!/bin/bash

case "${CHECK}" in
    couchbase|mcache)
        sudo service postgresql stop
        while sudo lsof -Pi :5432 -sTCP:LISTEN -t; do sleep 1; done
        ;;
    pgbouncer|postgres)
        sudo service memcached stop
        while sudo lsof -Pi :11211 -sTCP:LISTEN -t; do sleep 1; done
        ;;
esac
