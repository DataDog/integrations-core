#!/bin/sh
# Drives istio-full so the istio check reports its counters and histograms with
# non-zero deltas across scrapes (an idle mesh leaves them flat). Runs on the
# k3s image (kubectl) against the compose k3s cluster that seed.sh set up.
# No `set -e`: a failed kubectl call (API server busy, pod churn race) must not
# end the workload, since nothing restarts it.
set -u

M=/opt/istio-full/manifests
DURATION="${ACTIVITY_DURATION:-0}"   # 0 = run forever

log() { echo "activity-gen: $*"; }

# Opt out of the workload for a quiescent istio-full: ACTIVITY_GEN=0 keeps the
# container running (so dependents still start) but generates no traffic.
if [ "${ACTIVITY_GEN:-1}" = "0" ]; then
  log "disabled via ACTIVITY_GEN=0; idling"
  exec sleep infinity
fi

sed 's#https://127.0.0.1:6443#https://k3s:6443#' /kubeconfig/kubeconfig.yaml > /tmp/kubeconfig
export KUBECONFIG=/tmp/kubeconfig

PAUSE_IMAGE=rancher/mirrored-pause:3.6   # k3s's sandbox image, already on the node

end=0
[ "$DURATION" -gt 0 ] && end=$(( $(date +%s) + DURATION ))
i=0

while :; do
  i=$(( i + 1 ))
  n=$(( i % 50 + 1 ))

  # Order matters: istiod reports the drill gauges from its latest push context,
  # so the full push from churn.yaml goes last and every other config change
  # lands before it.

  # A virtual service with no route is rejected by the webhook (galley_validation_failed).
  printf '%s\n' \
    'apiVersion: networking.istio.io/v1' 'kind: VirtualService' \
    'metadata: {name: invalid, namespace: mesh}' \
    'spec: {hosts: [web.mesh.svc.cluster.local], http: [{route: []}]}' \
    | kubectl apply -f - > /dev/null 2>&1 || true

  # Knock the validating webhook to failurePolicy=Ignore so istiod reconciles it
  # back. While the deny label is set, the drills.yaml admission policy rejects
  # istiod's update (galley_validation_config_update_error{reason="Forbidden"});
  # removing the label lets istiod's next attempt through
  # (galley_validation_config_updates).
  W=validatingwebhookconfiguration/istio-validator-istio-system
  kubectl label "$W" istio-full/deny-istiod-update=true --overwrite > /dev/null
  kubectl patch "$W" --type=json \
    -p '[{"op":"replace","path":"/webhooks/0/failurePolicy","value":"Ignore"}]' > /dev/null
  sleep 2
  kubectl label "$W" istio-full/deny-istiod-update- > /dev/null

  # Sidecar injection: one injected pod (sidecar_injection_requests/success_total,
  # and its proxy's CSR moves citadel_server_*), one opted out by annotation
  # (sidecar_injection_skip_total), and one the injector rejects for an invalid
  # annotation (sidecar_injection_failure_total; the pod is never created).
  kubectl -n mesh delete pod -l istio-full/churn=inject --wait=false > /dev/null 2>&1 || true
  kubectl -n mesh run "inject-$i" --image="$PAUSE_IMAGE" --restart=Never \
    --labels=istio-full/churn=inject > /dev/null
  kubectl -n mesh run "skip-$i" --image="$PAUSE_IMAGE" --restart=Never \
    --labels=istio-full/churn=inject --annotations=sidecar.istio.io/inject=false > /dev/null
  kubectl -n mesh run "fail-$i" --image="$PAUSE_IMAGE" --restart=Never \
    --labels=istio-full/churn=inject \
    --annotations=traffic.sidecar.istio.io/includeOutboundIPRanges=invalid > /dev/null 2>&1 || true

  # Keep the unready endpoint on the notready pod's current IP.
  ip=$(kubectl -n mesh get pod -l app=notready -o jsonpath='{.items[0].status.podIP}' 2>/dev/null || true)
  [ -n "$ip" ] && sed "s/__IP__/$ip/" "$M/notready-endpoints.yaml" | kubectl apply -f - > /dev/null

  # Mesh traffic from the scraped client sidecar: HTTP requests with bodies
  # (istio_requests_total, istio_request_duration_milliseconds,
  # istio_request_bytes, istio_response_bytes) and plain TCP on the tcp- port
  # (istio_tcp_connections_opened/closed_total, istio_tcp_sent/received_bytes_total).
  kubectl -n mesh exec deploy/client -c client -- sh -c '
    for j in $(seq 10); do
      curl -s -o /dev/null http://web/
      curl -s -o /dev/null -X POST --data-binary "$(head -c 2048 /dev/zero | tr "\0" x)" http://web/
      curl -s -o /dev/null http://web:8080/
    done' || log "traffic batch failed"

  # Config churn through the validation webhook (galley_validation_passed) and
  # into one full push (pilot_xds_pushes, pilot_k8s_cfg_events, pilot_push_triggers,
  # pilot_inbound_updates, pilot_proxy_convergence_time, pilot_xds_push_time,
  # grpc_server_msg_*) that re-records the drill gauges. See churn.yaml.
  sed "s/__N__/$n/g" "$M/churn.yaml" | kubectl apply -f - > /dev/null || log "churn apply failed"

  if [ $(( i % 10 )) -eq 0 ]; then
    log "iteration $i: $(kubectl -n mesh get pods --no-headers 2>/dev/null | wc -l) pods in mesh"
  fi

  [ "$end" -gt 0 ] && [ "$(date +%s)" -ge "$end" ] && break
  sleep 1
done

log "PASS: activity workload complete after $i iterations"
