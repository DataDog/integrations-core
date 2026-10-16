#!/bin/sh
# Drives scylla-full so the scylla check reports its dashboard metrics with
# non-zero values (an idle node reports zero for the coordinator, cache, and
# transport counters). Consumes DB_HOST/DB_PORT/DB_USERNAME/DB_PASSWORD from the
# fixture.
set -eu

API="http://${DB_HOST}:${SCYLLA_API_PORT:-10000}"
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever

log() { echo "activity-gen: $*" >&2; }

# Opt out of the workload for a quiescent scylla-full: ACTIVITY_GEN=0 keeps the
# container running (so dependents still start) but generates no traffic.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

# ~15 KB value: a 60-row batch of these (~900 KB) is too slow for a 1ms write
# timeout, while staying under the 1 MB batch size failure threshold.
BIG=$(head -c 15000 /dev/zero | tr '\0' 'x')

# Emits CQL forever (or until ACTIVITY_DURATION) on stdout. It is piped into a
# single long-lived cqlsh session, so traffic is continuous rather than bursty
# and the pipe throttles generation to the rate cqlsh can execute. Logs go to
# stderr. Timeouts are deliberate; cqlsh reports them and keeps going.
workload() {
  end=0
  [ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
  i=0

  while :; do
    i=$(( i + 1 ))

    # coordinator_total_write_attempts_local_node, coordinator_write_latency,
    # coordinator_reads_local_node, coordinator_read_latency, cache.row_hits
    # (and cache.row_misses right after caches are dropped below).
    j=0
    while [ $j -lt 20 ]; do
      k=$(( (i + j) % 50 ))
      echo "INSERT INTO activity.kv (k, c, v) VALUES ($k, $(( i % 100 )), 'v$i');"
      echo "SELECT * FROM activity.kv WHERE k = $k;"
      j=$(( j + 1 ))
    done

    # coordinator_read_timeouts: Scylla's per-query timeout is too short to read
    # the large partitions written by the batch below (small ones finish in time).
    echo "SELECT * FROM activity.kv WHERE k IN ($(seq -s, 1000 1059)) USING TIMEOUT 1ms;"

    # coordinator_write_timeouts: a large batch under the same 1ms timeout.
    # Keys cycle through a fixed range so the table does not grow without bound.
    echo "BEGIN UNLOGGED BATCH USING TIMEOUT 1ms"
    j=0
    while [ $j -lt 60 ]; do
      echo "INSERT INTO activity.kv (k, c, v) VALUES ($(( 1000 + j )), $(( i % 10 )), '$BIG');"
      j=$(( j + 1 ))
    done
    echo "APPLY BATCH;"

    # cache.row_misses: flush the memtable to sstables, then drop the row cache
    # so the next reads have to go to disk.
    if [ $(( i % 5 )) -eq 0 ]; then
      curl -sf -X POST "$API/storage_service/keyspace_flush/activity" > /dev/null || true
      curl -sf -X POST "$API/system/drop_sstable_caches" > /dev/null || true
    fi

    if [ $(( i % 10 )) -eq 0 ]; then
      m=$(curl -sf "http://${DB_HOST}:9180/metrics" || true)
      log "iteration $i:" \
          "row_misses=$(echo "$m" | sed -n 's/^scylla_cache_row_misses{[^}]*} \([0-9]*\).*/\1/p')" \
          "read_timeouts=$(echo "$m" | sed -n 's/^scylla_storage_proxy_coordinator_read_timeouts{[^}]*} \([0-9]*\).*/\1/p' | head -1)" \
          "write_timeouts=$(echo "$m" | sed -n 's/^scylla_storage_proxy_coordinator_write_timeouts{[^}]*} \([0-9]*\).*/\1/p' | head -1)"
    fi

    [ "$end" -gt 0 ] && [ "$(date +%s)" -ge "$end" ] && break
    sleep 1
  done

  log "PASS: activity workload complete after $i iterations"
}

workload | cqlsh "$DB_HOST" "${DB_PORT:-9042}" -u "$DB_USERNAME" -p "$DB_PASSWORD" > /dev/null 2>&1 || true
