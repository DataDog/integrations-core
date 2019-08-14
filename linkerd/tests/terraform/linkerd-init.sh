curl -LO https://storage.googleapis.com/kubernetes-release/release/`curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt`/bin/linux/amd64/kubectl
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
export KUBECONFIG=kubeconfig

curl -sL https://run.linkerd.io/install | sh
export PATH=$PATH:$HOME/.linkerd2/bin
linkerd install | kubectl apply -f -
linkerd check # will wait for linkerd to be available
curl -sL https://run.linkerd.io/emojivoto.yml | kubectl apply -f -
kubectl wait pods -n emojivoto --all --for=condition=Ready --timeout=300s
kubectl get -n emojivoto deploy -o yaml | linkerd inject - | kubectl apply -f -
linkerd -n emojivoto check --proxy
