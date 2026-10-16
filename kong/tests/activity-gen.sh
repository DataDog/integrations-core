#!/bin/sh
# Drives kong-full so the kong check reports its dashboard metrics with non-zero
# values (an idle Kong reports no request, bandwidth, or latency series). Loops
# proxied traffic against every node in KONG_HOSTS, authenticated with
# KONG_CONSUMER_KEY.
set -eu

HOSTS="${KONG_HOSTS:-${DB_HOST:-kong}}"
PORT="${KONG_PROXY_PORT:-8000}"
KEY="${KONG_CONSUMER_KEY}"
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever

log() { echo "activity-gen: $*"; }

# Opt out of the workload for a quiescent kong-full: ACTIVITY_GEN=0 keeps the
# container running (so dependents still start) but generates no traffic.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

# connections_waiting counts idle keep-alive client connections, so hold one per
# node: curl reuses a single connection for the globbed URLs and --rate leaves it
# idle between transfers (well under Kong's 60s keepalive_timeout).
for host in $HOSTS; do
  log "opening idle keep-alive session to ${host}"
  curl -sS -o /dev/null --rate 4/m -H "apikey: ${KEY}" "http://${host}:${PORT}/?keepalive=[1-1000000]" &
done

end=0
[ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
i=0

while :; do
  i=$(( i + 1 ))

  for host in $HOSTS; do
    base="http://${host}:${PORT}"
    # Authenticated 200s: http.requests/http.status/http.consumer.status,
    # bandwidth (ingress+egress), and kong/request/upstream latency histograms.
    curl -sS -o /dev/null -H "apikey: ${KEY}" "${base}/" || true
    curl -sS -o /dev/null -H "apikey: ${KEY}" -d "payload-${i}" "${base}/" || true
    # 401 (no credential) and 404 (upstream miss) widen the code dimension.
    curl -sS -o /dev/null "${base}/" || true
    curl -sS -o /dev/null -H "apikey: ${KEY}" "${base}/missing-${i}" || true
  done

  [ $(( i % 100 )) -eq 0 ] && log "iteration ${i}"

  if [ "$end" -gt 0 ] && [ "$(date +%s)" -ge "$end" ]; then
    log "PASS: ran ${i} iterations in ${DURATION}s"
    exit 0
  fi

  sleep 1
done
