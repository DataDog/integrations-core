set -euo pipefail

# Use config mapped to /root/.kube/config
kubectl config set-context kind-linkerd

# Install linkerd CLI and deploy
echo "###  LINKERD INSTALL  ###"
linkerd install | kubectl apply -f -
echo "###  LINKERD CHECK  ###"
linkerd check # will wait for linkerd to be available
echo "###  LINKERD METRICS SERVICE  ###"
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: linkerd-controller-proxy-metrics
  namespace: linkerd
spec:
  selector:
    linkerd.io/control-plane-component: controller
  ports:
  - name: proxy-metrics
    port: 4191
    targetPort: 4191
EOF
for attempt in $(seq 1 30); do
    if [ "$(kubectl -n linkerd get endpoints linkerd-controller-proxy-metrics -o jsonpath='{.subsets[0].addresses[0].ip}')" ]; then
        break
    fi
    sleep 1
done
test -n "$(kubectl -n linkerd get endpoints linkerd-controller-proxy-metrics -o jsonpath='{.subsets[0].addresses[0].ip}')"

# Install demo linkerd app
echo "###  EMOJIVOTO DEPLOY  ###"
curl -sL https://run.linkerd.io/emojivoto.yml | kubectl apply -f -
echo "###  EMOJIVOTO WAIT  ###"
kubectl wait pods -n emojivoto --all --for=condition=Ready --timeout=300s
echo "###  EMOJIVOTO INJECT  ###"
kubectl get -n emojivoto deploy -o yaml | linkerd inject - | kubectl apply -f -
echo "###  EMOJIVOTO CHECK  ###"
linkerd -n emojivoto check --proxy
echo "###  LINKERD DEPLOY COMPLETE  ###"

# run forever so container doesn't exit
tail -f /dev/null
