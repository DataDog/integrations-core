# Kubernetes Integration

![Kubernetes Dashboard][1]

## Overview

Get metrics from the Kubernetes service in real time to:

- Visualize and monitor Kubernetes states
- Be notified about Kubernetes failovers and events.

Note: This check only works with Agent v5. For Agent v6+, see the [kubelet check][2].

## Setup

### Installation

The Kubernetes check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Kubernetes servers.

For more information on installing the Datadog Agent on your Kubernetes clusters, see the [Kubernetes documentation][4].

To collect Kubernetes State metrics, see the [kubernetes_state integration][5].

### Configuration

Edit the `kubernetes.yaml` file to point to your server and port, set the masters to monitor.

### Validation

Run the [Agent's status subcommand][6] and look for `kubernetes` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

As of the v5.17.0 release, the Datadog Agent supports a built-in [leader election option](#gathering-kubernetes-events) for the Kubernetes event collector. Once enabled, you no longer need to deploy an additional event collection container to your cluster. Instead, Agents coordinate to ensure only one Agent instance is gathering events at a given time, events below are available:

- Backoff
- Conflict
- Delete
- DeletingAllPods
- Didn't have enough resource
- Error
- Failed
- FailedCreate
- FailedDelete
- FailedMount
- FailedSync
- Failedvalidation
- FreeDiskSpaceFailed
- HostPortConflict
- InsufficientFreeCPU
- InsufficientFreeMemory
- InvalidDiskCapacity
- Killing
- KubeletsetupFailed
- NodeNotReady
- NodeoutofDisk
- OutofDisk
- Rebooted
- TerminatedAllPods
- Unable
- Unhealthy

### Service Checks

The Kubernetes check does not include any service checks.

## Troubleshooting

### Agent installation on Kubernetes master nodes

Since Kubernetes v1.6, the concept of [Taints and tolerations][8] was introduced. The master node is no longer off limits, it's simply tainted. Add the required toleration to the pod to run it.

Add the following lines to your Deployment (or Daemonset if you are running a multi-master setup):

```yaml
spec:
  tolerations:
    - key: node-role.kubernetes.io/master
      effect: NoSchedule
```

### Why is the Kubernetes check failing with a ConnectTimeout error to port 10250?

The Agent assumes the kubelet API is available at the default gateway of the container. If that's not the case because you are using a software defined networks like Calico or Flannel, the Agent needs to be specified using an environment variable:

```yaml
- name: KUBERNETES_KUBELET_HOST
  valueFrom:
    fieldRef:
      fieldPath: spec.nodeName
```

For reference, see this [pull request][9].

### Why is there a container in each Kubernetes pod with 0% CPU and minimal disk/ram?

These are pause containers (`docker_image:gcr.io/google_containers/pause.*`) that K8s injects into every pod to keep it populated even if the "real" container is restarting or stopped.

The docker_daemon check ignores them through a default exclusion list, but they do show up for K8s metrics like `kubernetes.cpu.usage.total` and `kubernetes.filesystem.usage`.

## Further Reading

- [Monitoring in the Kubernetes era][10]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kubernetes/images/kubernetes_dashboard.png
[2]: https://docs.datadoghq.com/integrations/kubelet
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://docs.datadoghq.com/agent/kubernetes/
[5]: https://docs.datadoghq.com/integrations/kubernetes/#kubernetes-state-metrics
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kubernetes/metadata.csv
[8]: https://blog.kubernetes.io/2017/03/advanced-scheduling-in-kubernetes.html
[9]: https://github.com/DataDog/dd-agent/pull/3051
[10]: https://www.datadoghq.com/blog/monitoring-kubernetes-era
