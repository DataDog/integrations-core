#!/bin/sh
# Drives coredns-full so the coredns check reports its full metric surface
# with non-zero values (an idle CoreDNS reports zero for every rate/counter
# metric). Consumes DNS_HOSTS from the fixture.
set -eu

# Candidate names for the CoreDNS server, first answering one wins: plain
# `docker compose` exposes it by service name (`coredns`), while evalya aliases
# the entrypoint service only by its task id (`coredns-full`).
DNS_HOSTS="${DNS_HOSTS:-coredns coredns-full}"

log() { echo "activity-gen: $*"; }

# Keeps the workload going when a query fails, but reports it: a failing
# query silently drops the coverage it was meant to produce. NXDOMAIN and
# SERVFAIL answers are expected and exit 0; only transport failures land here.
query() {
  if ! out=$(dig "$@" "@${DNS_HOST}" -p 53 +short 2>&1); then
    echo "activity-gen: dig $* failed: $out" >&2
  fi
}

# Opt out of the workload for a quiescent coredns-full: ACTIVITY_GEN=0 keeps
# the container running (so dependents still start) but generates no traffic.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

# coredns has no depends_on/healthcheck condition pointing back at this
# service (that would create a dependency cycle on the entrypoint), so wait
# out its own startup here instead.
log "waiting for one of [${DNS_HOSTS}] to answer on :53"
DNS_HOST=""
while [ -z "$DNS_HOST" ]; do
  for h in $DNS_HOSTS; do
    if dig example.com "@$h" -p 53 +time=2 +tries=1 >/dev/null 2>&1; then
      DNS_HOST="$h"
      break
    fi
  done
  [ -n "$DNS_HOST" ] || sleep 1
done
log "querying ${DNS_HOST}:53"

# process_cpu_seconds_total ticks in 10ms steps, and three queries a second
# often use less than that between two check runs, so it reads zero. A batch
# of cache hits from one dig process adds enough CPU to move it every run.
BURST_FILE=/tmp/burst
n=0
while [ "$n" -lt 50 ]; do echo example.com; n=$(( n + 1 )); done > "$BURST_FILE"

i=0

while :; do
  i=$(( i + 1 ))

  # example.com is forwarded to the local upstream (forward plugin) and cached
  # (cache 30): the first lookup per 30s window is a cache miss plus a
  # forward request/response/rcode; repeats within that window are cache hits.
  query example.com

  # A unique name inside the forward zone always misses the cache, so every
  # iteration reaches forward. Without it forward fires once per 30s window and
  # a short scrape interval often sees no forward_response_rcode_count change.
  # The upstream answers these NXDOMAIN.
  query "fwd-$i.example.com"

  # Names outside the example.com forward zone resolve locally (SERVFAIL):
  # more cache misses and response-code variety without touching forward.
  query "miss-$i.invalid"

  query -f "$BURST_FILE"

  if [ $(( i % 10 )) -eq 0 ]; then
    log "iteration $i"
  fi
  sleep 1
done
