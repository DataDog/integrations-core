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
echo "###  LINKERD DEPLOY COMPLETE  ###"

# run forever so container doesn't exit
tail -f /dev/null
