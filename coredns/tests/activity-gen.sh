#!/bin/sh
# Drives coredns-full so the coredns check reports its full metric surface
# with non-zero values (an idle CoreDNS reports zero for every rate/counter
# metric). Consumes DNS_HOST from the fixture.
set -eu

DNS_HOST="${DNS_HOST:-coredns}"
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever

log() { echo "activity-gen: $*"; }

# Opt out of the workload for a quiescent coredns-full: ACTIVITY_GEN=0 keeps
# the container running (so dependents still start) but generates no traffic.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

log "installing dig"
apk add --no-cache bind-tools >/dev/null

# coredns has no depends_on/healthcheck condition pointing back at this
# service (that would create a dependency cycle on the entrypoint), so wait
# out its own startup here instead.
log "waiting for ${DNS_HOST}:53 to answer"
until dig example.com "@${DNS_HOST}" -p 53 +time=2 +tries=1 >/dev/null 2>&1; do
  sleep 1
done

end=0
[ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
i=0

while :; do
  i=$(( i + 1 ))

  # example.com is forwarded to the host resolver (forward plugin) and cached
  # (cache 30): the first lookup per 30s window is a cache miss plus a
  # forward request/response/rcode; repeats within that window are cache hits.
  dig example.com "@${DNS_HOST}" -p 53 +short >/dev/null 2>&1 || true

  # Names outside the example.com forward zone resolve locally (SERVFAIL):
  # more cache misses and response-code variety without touching forward.
  dig "miss-$i.invalid" "@${DNS_HOST}" -p 53 +short >/dev/null 2>&1 || true

  if [ $(( i % 10 )) -eq 0 ]; then
    log "iteration $i"
  fi

  [ "$end" -gt 0 ] && [ "$(date +%s)" -ge "$end" ] && break
  sleep 1
done

log "PASS: activity workload complete after $i iterations"
