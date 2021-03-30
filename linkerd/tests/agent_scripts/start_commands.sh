# Install kubectl and linkerd on agent container

curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

#curl -LO https://storage.googleapis.com/kubernetes-release/release/`curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt`/bin/linux/amd64/kubectl
#chmod +x ./kubectl
#sudo mv ./kubectl /usr/local/bin/kubectl
#export KUBECONFIG=kubeconfig

# Use config mapped to /root/.kube/config
kubectl config set-context kind-linkerd

# Install linkerd CLI and deploy
curl -sL https://run.linkerd.io/install | sh
export PATH=$PATH:$HOME/.linkerd2/bin
linkerd install | kubectl apply -f -
linkerd check # will wait for linkerd to be available

# Install demo linkerd app
curl -sL https://run.linkerd.io/emojivoto.yml | kubectl apply -f -
kubectl wait pods -n emojivoto --all --for=condition=Ready --timeout=300s
kubectl get -n emojivoto deploy -o yaml | linkerd inject - | kubectl apply -f -
linkerd -n emojivoto check --proxy