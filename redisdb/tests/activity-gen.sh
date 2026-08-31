#!/bin/sh
# Drives redis-full so the redisdb check and the OTel redis receiver report their
# full metric surface with non-zero values (an idle Redis reports zero for most
# counters). Runs setup once, then loops the workload. Consumes
# DB_HOST/DB_PORT/REDIS_PASSWORD from the fixture.
set -eu

R="redis-cli --no-auth-warning -h ${DB_HOST} -p ${DB_PORT:-6379} -a ${REDIS_PASSWORD}"
DB="${ACTIVITY_DB:-14}"
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever

log() { echo "activity-gen: $*"; }

# Eviction ceiling + policy (matches the compose master; re-set so the script
# also works against a plain Redis) and a slowlog threshold above ordinary
# commands but below the DEBUG SLEEP below.
log "configuring eviction ceiling and slowlog threshold"
$R config set maxmemory 16mb               > /dev/null
$R config set maxmemory-policy allkeys-lru  > /dev/null
$R config set slowlog-log-slower-than 5000  > /dev/null

# Lua interpreter memory stays at its floor until a script runs.
$R eval "return redis.status_reply('OK')" 0 > /dev/null

# Client-side caching: tracking_total_keys is non-zero only while a RESP3 client
# holds CLIENT TRACKING ON, so keep one session open for the task's lifetime.
log "opening tracked RESP3 session"
{
  echo "client tracking on"
  while :; do echo "get track:key"; sleep 2; done
} | $R -3 -n "$DB" > /dev/null 2>&1 &
$R -n "$DB" set "track:key" seed > /dev/null

end=0
[ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
i=0

while :; do
  i=$(( i + 1 ))

  # keyspace hits/misses/expires/avg_ttl, across two DBs for multiple series.
  for db in "$DB" $(( DB - 1 )); do
    $R -n "$db" mset "hit:$i" "v$i" "hit2:$i" "v$i" > /dev/null
    $R -n "$db" get "hit:$i"        > /dev/null   # hit
    $R -n "$db" get "absent:$i"     > /dev/null   # miss
    $R -n "$db" set "ttl:$i" v ex 2 > /dev/null   # expires, then expired
  done

  # command variety -> widens the cmd dimension of command_stats.
  $R -n "$DB" lpush "list:$i" a b c    > /dev/null
  $R -n "$DB" lrange "list:$i" 0 -1    > /dev/null
  $R -n "$DB" sadd "set:$i" x y z      > /dev/null
  $R -n "$DB" smembers "set:$i"        > /dev/null
  $R -n "$DB" zadd "zset:$i" 1 a 2 b   > /dev/null
  $R -n "$DB" hset "hash:$i" f v       > /dev/null
  $R -n "$DB" xadd "stream:$i" '*' f v > /dev/null
  $R -n "$DB" incr "counter"           > /dev/null
  $R -n "$DB" client setinfo lib-name activity-gen > /dev/null 2>&1 || true  # 7.2+

  # net in/out bytes + client buffer high-water marks.
  $R -n "$DB" set "big:$i" "$(head -c 32768 /dev/zero | tr '\0' 'x')" > /dev/null
  $R -n "$DB" get "big:$i" > /dev/null

  # eviction: write past the ceiling so allkeys-lru has to evict.
  $R -n "$DB" eval \
    "for j=1,200 do redis.call('SET', KEYS[1]..j, string.rep('x', 4096)) end return 1" \
    1 "fill:$i:" > /dev/null

  # blocked clients: BLPOP on an empty key parks a client while it waits.
  $R -n "$DB" blpop "never:$i" 3 > /dev/null 2>&1 &

  # fork/rdb: latest_fork_usec stays 0 until the first background save.
  if [ $(( i % 5 )) -eq 1 ]; then $R bgsave > /dev/null 2>&1 || true; fi

  # slowlog: DEBUG SLEEP exceeds the 5ms threshold set above.
  if [ $(( i % 5 )) -eq 2 ]; then $R debug sleep 0.05 > /dev/null 2>&1 || true; fi

  # connection churn: total_connections_received.
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
