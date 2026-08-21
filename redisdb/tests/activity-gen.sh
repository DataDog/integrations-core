#!/bin/sh
# Drives the Redis fixture through states that make the redisdb check and the
# OTel redis receiver report their full metric surface with non-zero values.
#
# Without this, an idle Redis reports zero for most counters, and any assertion
# that compares 0 to 0 passes without proving anything. Each block below targets
# metrics that stay absent or flat otherwise.
#
# Runs setup once, then loops the workload so both collectors see activity
# across several scrape intervals. Consumes DB_HOST/DB_PORT/REDIS_PASSWORD from
# the redis-full fixture; connects through the info-proxy exactly like any other
# client (CONFIG/CLUSTER pass through to the master).
set -eu

R="redis-cli --no-auth-warning -h ${DB_HOST} -p ${DB_PORT:-6379} -a ${REDIS_PASSWORD}"
DB="${ACTIVITY_DB:-14}"
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever

log() { echo "activity-gen: $*"; }

# --- setup ----------------------------------------------------------------
# Eviction needs a maxmemory ceiling and a policy that actually evicts. Matches
# the full-coverage.compose master (--maxmemory 16mb allkeys-lru); re-set here so
# the script also works when pointed at a plain Redis. Also populates
# redis.mem.maxmemory, which is 0 (unlimited) by default.
log "configuring eviction ceiling and slowlog threshold"
$R config set maxmemory 16mb              > /dev/null
$R config set maxmemory-policy allkeys-lru > /dev/null
# 5ms so ordinary commands are not logged but DEBUG SLEEP below is.
$R config set slowlog-log-slower-than 5000 > /dev/null

# Lua interpreter memory stays at its floor until a script is evaluated.
log "seeding lua interpreter"
$R eval "return redis.status_reply('OK')" 0 > /dev/null

# tracking_total_keys counts keys in the server's client-side-caching
# invalidation table, which only exists while a RESP3 client holds
# CLIENT TRACKING ON. A one-shot redis-cli closes its connection and the table
# drops back to 0, so hold one session open for the life of this task and keep
# reading through it. Without this the metric reports a constant 0 and its
# assertion compares 0 to 0.
log "opening tracked RESP3 session for client-side caching"
{
  echo "client tracking on"
  while :; do
    echo "get track:key"
    sleep 2
  done
} | $R -3 -n "$DB" > /dev/null 2>&1 &
$R -n "$DB" set "track:key" seed > /dev/null

end=0
[ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
i=0

while :; do
  i=$(( i + 1 ))

  # --- keyspace: hits, misses, keys, expires, avg_ttl --------------------
  # Spread across two DBs so per-db metrics report more than one series.
  for db in "$DB" $(( DB - 1 )); do
    $R -n "$db" mset "hit:$i" "v$i" "hit2:$i" "v$i" > /dev/null
    $R -n "$db" get "hit:$i"      > /dev/null   # hit
    $R -n "$db" get "absent:$i"   > /dev/null   # miss
    $R -n "$db" set "ttl:$i" "v" ex 2 > /dev/null   # expires + avg_ttl, then expired
  done

  # --- command variety: redis.cmd.calls / redis.cmd.usec ----------------
  # command_stats is per-command, so exercising several command families
  # widens the cmd dimension instead of deepening a single series.
  $R -n "$DB" lpush "list:$i" a b c   > /dev/null
  $R -n "$DB" lrange "list:$i" 0 -1   > /dev/null
  $R -n "$DB" sadd "set:$i" x y z     > /dev/null
  $R -n "$DB" smembers "set:$i"       > /dev/null
  $R -n "$DB" zadd "zset:$i" 1 a 2 b  > /dev/null
  $R -n "$DB" hset "hash:$i" f v      > /dev/null
  $R -n "$DB" xadd "stream:$i" '*' f v > /dev/null
  $R -n "$DB" incr "counter"          > /dev/null
  # CLIENT SETINFO advertises a client lib-name, surfacing it in CLIENT INFO/LIST
  # and adding a client|setinfo entry to command_stats. Redis 7.2+ only.
  $R -n "$DB" client setinfo lib-name activity-gen > /dev/null 2>&1 || true

  # --- net.input / net.output and client buffer high-water marks --------
  # A large write then a large read moves total_net_input_bytes and
  # total_net_output_bytes, and raises client_recent_max_{input,output}_buffer.
  $R -n "$DB" set "big:$i" "$(head -c 32768 /dev/zero | tr '\0' 'x')" > /dev/null
  $R -n "$DB" get "big:$i" > /dev/null

  # --- eviction: redis.keys.evicted -------------------------------------
  # Write past the 16mb ceiling in bursts so allkeys-lru has to evict.
  $R -n "$DB" eval \
    "for j=1,200 do redis.call('SET', KEYS[1]..j, string.rep('x', 4096)) end return 1" \
    1 "fill:$i:" > /dev/null

  # --- blocked clients: redis.clients.blocked ---------------------------
  # BLPOP on an empty key parks a client; it is counted while blocked.
  $R -n "$DB" blpop "never:$i" 3 > /dev/null 2>&1 &

  # --- fork + rdb: redis.latest_fork, redis.rdb.changes_since_last_save -
  # latest_fork_usec stays 0 until the first background save.
  if [ $(( i % 5 )) -eq 1 ]; then
    log "iteration $i: triggering BGSAVE"
    $R bgsave > /dev/null 2>&1 || true
  fi

  # --- slowlog ----------------------------------------------------------
  # DEBUG SLEEP exceeds the 5ms threshold, so the check reports slowlog rates.
  if [ $(( i % 5 )) -eq 2 ]; then
    $R debug sleep 0.05 > /dev/null 2>&1 || true
  fi

  # --- connection churn: redis.net.total_connections_received -----------
  # Each redis-cli invocation opens a fresh connection, but an explicit burst
  # keeps the counter climbing between scrapes.
  for _ in 1 2 3; do $R ping > /dev/null; done

  if [ $(( i % 10 )) -eq 0 ]; then
    stats=$($R info stats)
    log "iteration $i: keys=$($R -n "$DB" dbsize)" \
        "evicted=$(echo "$stats" | sed -n 's/^evicted_keys:\([0-9]*\).*/\1/p')" \
        "expired=$(echo "$stats" | sed -n 's/^expired_keys:\([0-9]*\).*/\1/p')"
  fi

  [ "$end" -gt 0 ] && [ "$(date +%s)" -ge "$end" ] && break
  sleep 1
done

log "PASS: activity workload complete after $i iterations"
