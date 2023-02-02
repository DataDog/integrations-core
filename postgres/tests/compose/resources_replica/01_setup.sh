#!/bin/bash
set -e

echo "Testing primary"
while ! nc -z postgres 5432 ; do
    echo "Primary not running, waiting"
    sleep 1
done

pg_ctl -D /var/lib/postgresql/data -l /tmp/logfile stop
rm -rf /var/lib/postgresql/data/*

echo "Running pg basebackup"
export PGPASSWORD='replicator'
pg_basebackup -h postgres -U replicator -X stream -v -R -D /var/lib/postgresql/data/
echo "pg basebackup ran"

pg_ctl -D /var/lib/postgresql/data -l /tmp/logfile start
