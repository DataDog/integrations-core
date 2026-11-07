#!/bin/bash
# Runs on every container start (/container-entrypoint-startdb.d), before the
# image healthcheck reports ready. Switches datafile I/O to O_DIRECT so reads
# bypass the host page cache: served from the page cache they complete in a few
# microseconds and V$SYSMETRIC's whole-millisecond "Average Synchronous
# Single-Block Read Latency" (oracle.avg_synchronous_single_block_read_latency)
# stays 0. The parameter is static, so the first start bounces the instance once.
set -euo pipefail

current=$(sqlplus -s / as sysdba <<'SQL'
set heading off feedback off pagesize 0
select value from v$parameter where name = 'filesystemio_options';
exit
SQL
)

if [ "$(echo "${current}" | tr -d '[:space:]')" != "SETALL" ]; then
  echo "direct-io: setting filesystemio_options=SETALL and restarting the instance"
  sqlplus -s / as sysdba <<'SQL'
whenever sqlerror exit failure
alter system set filesystemio_options = SETALL scope = spfile;
shutdown immediate
startup
alter pluggable database all open;
exit
SQL
fi
