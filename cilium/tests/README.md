# Cilium E2E

## Requirements
* [kind](https://kind.sigs.k8s.io/docs/user/quick-start/)
  * MacOS via homebrew: `brew install kind`
  * Windows via chocolatey: `choco install kind` 
* [helm](https://helm.sh/docs/intro/install/)
  * MacOS via homebrew: `brew install helm`
  * Windows via chocolatey: `choco install kubernetes-helm`

The E2E [`conftest.py`](/conftest.py) handles the rest:
1. Creates the kind cluster
2. Installs the cilium helm repo
3. Deploys a cilium environment to the kind cluster via helm

Note: On MacOS, you may get pop-ups asking to accept incoming kubectl connections. Click OK.

## How to Interact with the E2E Cilium Cluster

Make sure you have `kubectl` installed. 

1. Run `kind export kubeconfig --name cluster-cilium-<ENV>` to set the `kubectl` context. 
  
  ```
  kind export kubeconfig --name cluster-cilium-py38-1.11
  ```
2. Now, you can run `kubectl` commands to inspect the cluster:
```
# View cilium pods
kubectl get pods --namespace cilium                             
NAME                               READY   STATUS    RESTARTS   AGE
cilium-5r6p9                       1/1     Running   0          23m
cilium-operator-7678d97bcb-b9v6n   1/1     Running   0          23m
cilium-operator-7678d97bcb-gdl8c   1/1     Running   0          23m
cilium-xw974                       1/1     Running   0          23m

# Inspect pod details
kubectl describe pod <pod_name> --namespace cilium

# Shell into a pod
kubectl exec -it <pod_name> --namespace cilium -- bash
```
Note: The cilium pods are all under the `cilium` namespace, so you'll need to include the namespace in all `kubectl` commands.