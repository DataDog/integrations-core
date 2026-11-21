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

log() { echo "activity-gen: $*"; }
warn() { echo "activity-gen: $*" >&2; }
# Non-2xx answers are intended (they drive the error metrics), so only a
# transport failure means a metric may have lost its traffic: report it on
# stderr and keep going.
get() { curl -s -o /dev/null --max-time 5 "$@" || warn "curl exit $? for: $*"; }
# Requests whose failure is the point (rejected or reset connections).
expect_fail() { curl -s -o /dev/null --max-time 5 "$@" || :; }
# Admin calls must succeed; -f also reports an HTTP error status.
admin() { curl -fs -o /dev/null --max-time 5 -X POST "${ADMIN}/$1" || warn "admin $1 failed (curl exit $?)"; }
set_pressure() { { echo "$1" > "${DYN}/pressure.tmp" && mv "${DYN}/pressure.tmp" "${DYN}/pressure"; } || warn "cannot write ${DYN}/pressure"; }

# Opt out of the workload for a quiescent envoy-full: ACTIVITY_GEN=0 keeps the
# container running (so dependents still start) but generates no traffic.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

log "waiting for ${ADMIN}/ready"
until curl -fs "${ADMIN}/ready" 2>/dev/null | grep -q LIVE; do sleep 1; done

# runtime.admin_overrides_active is 1 only while the admin layer holds a key.
admin "runtime_modify?envoy_full.seeded=true"

# Long-held requests keep the active gauges non-zero at scrape time: HTTP/1.1 and
# HTTP/2 downstream connections (http.downstream_cx_http1_active/_http2_active),
# in-flight requests (http.downstream_rq_active, cluster.upstream_rq_active), and
# the single connection the `limited` listener allows, so further connections to
# it overflow (listener.downstream_cx_overflow).
hold() {
  while :; do curl -s -o /dev/null --max-time 40 "$@" || { warn "held request failed (curl exit $?): $*"; sleep 1; }; done
}
hold "${FRONT}/slow?s=30" &
hold --http2-prior-knowledge "${FRONT}/slow?s=30" &
hold "${LIMITED}/slow?s=30" &

# Many requests in the main loop are answered in under a millisecond, which
# Envoy records as 0. A steady stream of 10ms backend responses keeps the low
# http.downstream_rq_time percentiles (P25) above 0 in every stats interval,
# and running it apart keeps the main loop short. Its requests fail while the
# main loop trips the overload manager, so it backs off instead of logging; the
# main loop's requests to the same listener still report a lasting failure.
while :; do curl -s -o /dev/null --max-time 5 "${FRONT}/slow?s=0.01" || sleep 0.2; done &

i=0

while :; do
  i=$(( i + 1 ))

  # 2xx through both HTTP/1.1 and HTTP/2 to the reused sidecar services
  # (upstream/downstream rq, rq_time histograms, cx bytes, cx length).
  for svc in 1 2 1 2; do
    get "${FRONT}/service/${svc}"
    get --http2-prior-knowledge "${FRONT}/service/${svc}"
  done

  # Upstream-originated 3xx/4xx/5xx (cluster.upstream_rq_Nxx, listener.http.downstream_rq_Nxx).
  for code in 302 404 503; do get "${FRONT}/status/${code}"; done

  # 101 Switching Protocols (listener.http.downstream_rq_1xx). The backend closes
  # right after the upgrade, so curl reports an empty reply.
  expect_fail -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
    -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' "${FRONT}/ws"

  get "${FRONT}/timeout"                               # cluster.upstream_rq_timeout (504)
  get "${FRONT}/panic"                                 # cluster.lb_healthy_panic
  get "${FRONT}/blackhole"                             # cluster.upstream_cx_connect_timeout
  get -H 'x-target-cluster: does-not-exist' "${FRONT}/nocluster"   # http.no_cluster
  get "${FRONT}/no/such/route"                         # http.no_route
  expect_fail "${LIMITED}/"                            # listener.downstream_cx_overflow

  # Malformed request line (http.downstream_cx_protocol_error).
  printf 'NOT HTTP\r\n\r\n' | nc -w 1 "${ENVOY_HOST}" 80 > /dev/null 2>&1 || warn "nc to ${ENVOY_HOST}:80 failed"

  # A body uploaded slower than request_timeout to an upstream that does not
  # answer early (http.downstream_rq_timeout, 408). Envoy cuts the upload short,
  # so curl failing here is expected.
  head -c 8000 /dev/zero | expect_fail --limit-rate 1k -X POST --data-binary @- "${FRONT}/slow?s=10" &

  # Each /runtime_modify reloads the runtime snapshot. The seed nested the disk
  # layer past Envoy's walk limit, which fails the load (runtime.load_error), so
  # reload once with that tree parked (runtime.load_success) and once with it
  # back. Both run every iteration so each counter moves within a short check
  # interval.
  mv "${DYN}/runtime/1" "${DYN}/parked-runtime" || warn "cannot park ${DYN}/runtime/1"
  admin "runtime_modify?envoy_full.iteration=${i}"
  if [ -d "${DYN}/parked-runtime" ]; then
    mv "${DYN}/parked-runtime" "${DYN}/runtime/1" || warn "cannot restore ${DYN}/runtime/1"
  fi
  admin "runtime_modify?envoy_full.iteration=${i}"

  # Re-publish the file CDS with a new version: re-validating its deprecated
  # field counts runtime.deprecated_feature_use. Envoy reloads on the move.
  { sed "s/^version_info: .*/version_info: \"${i}\"/" "${DYN}/cds.yaml" > "${DYN}/cds.yaml.tmp" \
    && mv "${DYN}/cds.yaml.tmp" "${DYN}/cds.yaml"; } || warn "cannot re-publish ${DYN}/cds.yaml"

  # Briefly trip the overload manager so new connections are rejected
  # (listener.downstream_cx_overload_reject), then release it. Envoy only
  # re-reads the pressure file when one is moved into place. Its two waits also
  # pace the loop.
  set_pressure 1
  sleep 0.5
  expect_fail "${FRONT}/service/1"
  set_pressure 0
  sleep 0.5

  [ $(( i % 30 )) -eq 0 ] && log "iteration ${i}"
done
