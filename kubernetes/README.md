# Kubernetes Integration

## Overview

Get metrics from kubernetes service in real time to:

* Visualize and monitor kubernetes states
* Be notified about kubernetes failovers and events.

## Setup
### Installation

Install the `dd-check-kubernetes` package manually or with your favorite configuration manager

### Configuration

Edit the `kubernetes.yaml` file to point to your server and port, set the masters to monitor

### Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        kubernetes
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The kubernetes check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/kubernetes/metadata.csv) for a list of metrics provided by this integration.

### Events
The Kubernetes check does not include any event at this time.

### Service Checks
The Kubernetes check does not include any service check at this time.

## Troubleshooting
### Can I install the agent on my Kubernetes master node(s) ?
Yes, since Kubernetes 1.6, the concept of [Taints and tolerations](http://blog.kubernetes.io/2017/03/advanced-scheduling-in-kubernetes.html) was introduced. Now rather than the master being off limits, it's simply tainted.  Add the required toleration to the pod to run it:

Add the following lines to your Deployment (or Daemonset if you are running a multi-master setup):
```
spec:
 tolerations: 
 - key: node-role.kubernetes.io/master
   effect: NoSchedule
```

### Why is the Kubernetes check failing with a ConnectTimeout error to port 10250?
The agent assumes that the kubelet API is available at the default gateway of the container. If that's not the case because you are using a software defined networks like Calico or Flannel, the agent needs to be specified using an environment variable:
```
          - name: KUBERNETES_KUBELET_HOST
            valueFrom:
              fieldRef:
                fieldPath: spec.nodeName
```
See [this PR](https://github.com/DataDog/dd-agent/pull/3051)

###  Why is there a container in each Kubernetes pod with 0% CPU and minimal disk/ram?
These are pause containers (docker_image:gcr.io/google_containers/pause.*) that K8s injects into every pod to keep it populated even if the "real” container is restarting/stopped. 

The docker_daemon check ignores them through a default exclusion list, but they will show up for K8s metrics like *kubernetes.cpu.usage.total* and *kubernetes.filesystem.usage*.

## Further Reading
### Blog Article
To get a better idea of how (or why) to integrate your Kubernetes service, check out our [series of blog posts](https://www.datadoghq.com/blog/monitoring-kubernetes-era/) about it.

### Knowledge Base 
* [How to get more out of your Kubernetes integration?](https://help.datadoghq.com/hc/en-us/articles/115001293983-How-to-get-more-out-of-your-Kubernetes-integration)
* [How to report host disk metrics when dd-agent runs in a docker container?](https://help.datadoghq.com/hc/en-us/articles/115001786703-How-to-report-host-disk-metrics-when-dd-agent-runs-in-a-docker-container-)
