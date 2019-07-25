#!/bin/bash
# Download istio
curl -L https://git.io/getLatestIstio | ISTIO_VERSION=$ISTIO_VERSION sh -
export PATH=$PWD/istio-$ISTIO_VERSION/bin:$PATH

kubectl create serviceaccount --namespace kube-system tiller || true
kubectl create clusterrolebinding tiller-cluster-rule --clusterrole=cluster-admin --serviceaccount=kube-system:tiller || true
helm init --upgrade --service-account tiller --wait
kubectl create ns istio-system || true
kubectl label namespace default istio-injection=enabled

# istio-init install
helm install ./istio-$ISTIO_VERSION/install/kubernetes/helm/istio-init --name istio-init --namespace istio-system --version $ISTIO_VERSION --wait
kubectl wait jobs --all --for=condition=complete --namespace=istio-system --timeout=300s

# istio install
helm install ./istio-$ISTIO_VERSION/install/kubernetes/helm/istio --name istio --namespace istio-system --version $ISTIO_VERSION --wait

# Example application install
kubectl apply -f ./istio-$ISTIO_VERSION/samples/bookinfo/platform/kube/bookinfo.yaml
kubectl wait pods --all --for=condition=Ready --timeout=300s

# Adds a gateway to the app
kubectl apply -f ./istio-$ISTIO_VERSION/samples/bookinfo/networking/bookinfo-gateway.yaml
kubectl wait pods --all --for=condition=Ready --timeout=300s
