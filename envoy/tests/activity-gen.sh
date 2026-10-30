#!/bin/sh
# Drives envoy-full so the envoy check reports its dashboard and monitor metrics
# with non-zero values (an idle Envoy reports zero for most counters and active
# gauges). Waits for the proxy, primes the admin runtime layer once, then loops
# the workload. Consumes ENVOY_HOST/ENVOY_PORT (admin) from the fixture.
set -eu

ADMIN="http://${ENVOY_HOST}:${ENVOY_PORT:-8001}"
FRONT="http://${ENVOY_HOST}:80"
LIMITED="http://${ENVOY_HOST}:82"
DYN="${ENVOY_DYNAMIC_DIR:-/var/run/envoy-dynamic}"
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever

log() { echo "activity-gen: $*"; }
get() { curl -s -o /dev/null --max-time 5 "$@" || true; }
set_pressure() { { echo "$1" > "${DYN}/pressure.tmp" && mv "${DYN}/pressure.tmp" "${DYN}/pressure"; } || log "cannot write ${DYN}/pressure"; }

# Opt out of the workload for a quiescent envoy-full: ACTIVITY_GEN=0 keeps the
# container running (so dependents still start) but generates no traffic.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

log "waiting for ${ADMIN}/ready"
until curl -fs "${ADMIN}/ready" 2>/dev/null | grep -q LIVE; do sleep 1; done

# runtime.admin_overrides_active is 1 only while the admin layer holds a key.
get -X POST "${ADMIN}/runtime_modify?envoy_full.seeded=true"

# Long-held requests keep the active gauges non-zero at scrape time: HTTP/1.1 and
# HTTP/2 downstream connections (http.downstream_cx_http1_active/_http2_active),
# in-flight requests (http.downstream_rq_active, cluster.upstream_rq_active), and
# the single connection the `limited` listener allows, so further connections to
# it overflow (listener.downstream_cx_overflow).
hold() {
  while :; do curl -s -o /dev/null --max-time 40 "$@" || sleep 1; done
}
hold "${FRONT}/slow?s=30" &
hold --http2-prior-knowledge "${FRONT}/slow?s=30" &
hold "${LIMITED}/slow?s=30" &

end=0
[ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
i=0

while :; do
  i=$(( i + 1 ))

  # 2xx through both HTTP/1.1 and HTTP/2 to the reused sidecar services
  # (upstream/downstream rq, rq_time histograms, cx bytes, cx length).
  for svc in 1 2 1 2; do
    get "${FRONT}/service/${svc}"
    get --http2-prior-knowledge "${FRONT}/service/${svc}"
  done

  # Many of the requests in this loop are answered in under a millisecond, which
  # Envoy records as 0; enough 10ms backend responses keep the low
  # http.downstream_rq_time percentiles (P25) above 0.
  n=0
  while [ "$n" -lt 30 ]; do get "${FRONT}/slow?s=0.01"; n=$(( n + 1 )); done

  # Upstream-originated 3xx/4xx/5xx (cluster.upstream_rq_Nxx, listener.http.downstream_rq_Nxx).
  for code in 302 404 503; do get "${FRONT}/status/${code}"; done

  # 101 Switching Protocols (listener.http.downstream_rq_1xx).
  get -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
    -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' "${FRONT}/ws"

  get "${FRONT}/timeout"                               # cluster.upstream_rq_timeout (504)
  get "${FRONT}/panic"                                 # cluster.lb_healthy_panic
  get "${FRONT}/blackhole"                             # cluster.upstream_cx_connect_timeout
  get -H 'x-target-cluster: does-not-exist' "${FRONT}/nocluster"   # http.no_cluster
  get "${FRONT}/no/such/route"                         # http.no_route
  get "${LIMITED}/"                                    # listener.downstream_cx_overflow

  # Malformed request line (http.downstream_cx_protocol_error).
  printf 'NOT HTTP\r\n\r\n' | nc -w 1 "${ENVOY_HOST}" 80 > /dev/null 2>&1 || true

  # A body uploaded slower than request_timeout to an upstream that does not
  # answer early (http.downstream_rq_timeout, 408).
  head -c 8000 /dev/zero | curl -s -o /dev/null --max-time 5 --limit-rate 1k \
    -X POST --data-binary @- "${FRONT}/slow?s=10" &

  # Each /runtime_modify reloads the runtime snapshot. The seed nested the disk
  # layer past Envoy's walk limit, which fails the load (runtime.load_error), so
  # park that tree on every other iteration to let the load succeed
  # (runtime.load_success).
  if [ $(( i % 2 )) -eq 0 ]; then
    mv "${DYN}/runtime/1" "${DYN}/parked-runtime" || log "cannot park ${DYN}/runtime/1"
  fi
  get -X POST "${ADMIN}/runtime_modify?envoy_full.iteration=${i}"
  if [ -d "${DYN}/parked-runtime" ]; then
    mv "${DYN}/parked-runtime" "${DYN}/runtime/1" || log "cannot restore ${DYN}/runtime/1"
  fi

  if [ $(( i % 2 )) -eq 0 ]; then
    # Re-publish the file CDS with a new version: re-validating its deprecated
    # field counts runtime.deprecated_feature_use. Envoy reloads on the move.
    { sed "s/^version_info: .*/version_info: \"${i}\"/" "${DYN}/cds.yaml" > "${DYN}/cds.yaml.tmp" \
      && mv "${DYN}/cds.yaml.tmp" "${DYN}/cds.yaml"; } || log "cannot re-publish ${DYN}/cds.yaml"

    # Briefly trip the overload manager so new connections are rejected
    # (listener.downstream_cx_overload_reject), then release it. Envoy only
    # re-reads the pressure file when one is moved into place.
    set_pressure 1
    sleep 0.5
    get "${FRONT}/service/1"
    set_pressure 0
    sleep 0.5
  fi

  [ $(( i % 30 )) -eq 0 ] && log "iteration ${i}"

  if [ "$end" -gt 0 ] && [ "$(date +%s)" -ge "$end" ]; then
    log "PASS: completed ${i} iterations in ${DURATION}s"
    exec sleep infinity
  fi
  sleep 1
done
