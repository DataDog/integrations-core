set -euo pipefail

# Use config mapped to /root/.kube/config
kubectl config set-context kind-linkerd

# Install linkerd CLI and deploy
echo "###  LINKERD INSTALL  ###"
linkerd install | kubectl apply -f -
echo "###  LINKERD CHECK  ###"
linkerd check # will wait for linkerd to be available

# Install demo linkerd app
echo "###  EMOJIVOTO DEPLOY  ###"
curl -sL https://run.linkerd.io/emojivoto.yml | kubectl apply -f -
echo "###  EMOJIVOTO WAIT  ###"
kubectl wait pods -n emojivoto --all --for=condition=Ready --timeout=300s
echo "###  EMOJIVOTO INJECT  ###"
kubectl get -n emojivoto deploy -o yaml | linkerd inject - | kubectl apply -f -
echo "###  EMOJIVOTO CHECK  ###"
linkerd -n emojivoto check --proxy
echo "###  LINKERD METRICS FORWARD  ###"
kubectl port-forward --address 0.0.0.0 -n linkerd deployment/linkerd-controller 4191:4191 >/tmp/linkerd-metrics-port-forward.log 2>&1 &
for attempt in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:4191/metrics >/dev/null; then
        break
    fi
    sleep 1
done
curl -fsS http://127.0.0.1:4191/metrics >/dev/null
echo "###  LINKERD DEPLOY COMPLETE  ###"

# run forever so container doesn't exit
tail -f /dev/null
