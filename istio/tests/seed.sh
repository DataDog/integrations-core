#!/bin/sh
# One-shot setup for istio-full: installs istiod into the compose k3s cluster,
# deploys the sidecar-injected mesh workload, and applies the Istio config and
# drills (compose/full-coverage/drills.yaml) behind the pilot gauges. Runs on
# the k3s image (kubectl) with istioctl copied in.
set -eu

M=/opt/istio-full/manifests
log() { echo "seed: $*"; }

# k3s writes a kubeconfig for 127.0.0.1; reach the API server by its compose name.
sed 's#https://127.0.0.1:6443#https://k3s:6443#' /kubeconfig/kubeconfig.yaml > /tmp/kubeconfig
export KUBECONFIG=/tmp/kubeconfig
ISTIOCTL=/tools/istioctl

# A 1s debounce (default 100ms) keeps each multi-object churn.yaml apply in a
# single push, so the drill gauges are recorded together.
log "installing istio ${ISTIO_VERSION} (minimal profile: istiod only)"
$ISTIOCTL install -y --set profile=minimal --set values.pilot.env.PILOT_DEBOUNCE_AFTER=1s
kubectl -n istio-system wait deployment/istiod --for=condition=Available --timeout=300s

log "deploying the mesh workload"
kubectl apply -f "$M/mesh.yaml"
kubectl -n mesh wait deployment --all --for=condition=Available --timeout=300s

log "applying istio config and the pilot gauge drills"
kubectl apply -f "$M/istio-config.yaml"
kubectl apply -f "$M/drills.yaml"
kubectl -n mesh wait deployment/notready --for=condition=Available --timeout=300s
ip=$(kubectl -n mesh get pod -l app=notready -o jsonpath='{.items[0].status.podIP}')
sed "s/__IP__/$ip/" "$M/notready-endpoints.yaml" | kubectl apply -f -
sed "s/__N__/1/g" "$M/churn.yaml" | kubectl apply -f -

# Prime the request/TCP families before the first scrape.
kubectl -n mesh exec deploy/client -c client -- sh -c \
  'for i in $(seq 20); do curl -s -o /dev/null http://web/; curl -s -o /dev/null http://web:8080/; done'

log "seed-done"
