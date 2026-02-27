#!/bin/bash
set -e

pg_ctl -D ${PGDATA} -l /tmp/logfile -w stop
rm -rf ${PGDATA}/*

echo "Testing primary"
while ! pg_isready -U datadog -d datadog_test -h postgres -p 5432 ; do
    echo "Primary not running, waiting"
    sleep 1
done

echo "Running pg basebackup"
export PGPASSWORD='replicator'
pg_basebackup -h postgres -U replicator -X stream -v -R -D ${PGDATA}
echo "pg basebackup executed"

pg_ctl -D ${PGDATA} -w start
