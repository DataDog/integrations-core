# Overview

The e2e environment spins up a kafka cluster with a zookeeper and a simple hello world connector.

# Useful command line

Run the command inside the kind container: 

```commandline
docker exec -it cluster-strimzi-py3.8-0.34-control-plane /bin/bash
```

## Pods 

```commandline
kubectl -n kafka get pods
```

## Deployments 

```commandline
kubectl -n kafka get deployments
```

## Logs

Cluster operator logs: 

```commandline
kubectl logs -f -l name=strimzi-cluster-operator --all-containers -n kafka
```

User operator logs: 

```commandline
kubectl logs -n kafka <pod-name> -c user-operator
```

Topic operator logs: 

```commandline
kubectl logs -n kafka <pod-name> -c topic-operator
```

Connect logs: 

```commandline
kubectl logs -n kafka my-connect-connect-ccdf4f9f9-7x8g6
```