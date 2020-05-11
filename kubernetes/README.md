# Kubernetes Integration

![Kubernetes Dashboard][1]

## Overview

Get metrics from the Kubernetes service in real time to:

- Visualize and monitor Kubernetes states
- Be notified about Kubernetes failovers and events.

## Setup

### Installation

The Kubernetes check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your Kubernetes servers.

For more information on installing the Datadog Agent on your Kubernetes clusters, see the [Kubernetes documentation page][2].

To collect Kubernetes State metrics, please refer to the [kubernetes_state integration][13].


### Configuration

Edit the `kubernetes.yaml` file to point to your server and port, set the masters to monitor. See the [sample kubernetes.yaml][4] for all available configuration options.


### Validation

[Run the Agent's `status` subcommand][8] and look for `kubernetes` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Events

As the 5.17.0 release, Datadog Agent now supports built in [leader election option](#gathering-kubernetes-events) for the Kubernetes event collector. Once enabled, you no longer need to deploy an additional event collection container to your cluster. Instead agents will coordinate to ensure only one agent instance is gathering events at a given time, events below will be available:

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

### Can I install the agent on my Kubernetes master node(s) ?

Yes, since Kubernetes 1.6, the concept of [Taints and tolerations][10] was introduced. Now rather than the master being off limits, it's simply tainted. Add the required toleration to the pod to run it:

Add the following lines to your Deployment (or Daemonset if you are running a multi-master setup):

```yaml
spec:
  tolerations:
    - key: node-role.kubernetes.io/master
      effect: NoSchedule
```

### Why is the Kubernetes check failing with a ConnectTimeout error to port 10250?

The agent assumes that the kubelet API is available at the default gateway of the container. If that's not the case because you are using a software defined networks like Calico or Flannel, the agent needs to be specified using an environment variable:

```yaml
- name: KUBERNETES_KUBELET_HOST
  valueFrom:
    fieldRef:
      fieldPath: spec.nodeName
```

See [this PR][11]

### Why is there a container in each Kubernetes pod with 0% CPU and minimal disk/ram?

These are pause containers (docker_image:gcr.io/google_containers/pause.\*) that K8s injects into every pod to keep it populated even if the "real" container is restarting/stopped.

The docker_daemon check ignores them through a default exclusion list, but they will show up for K8s metrics like `kubernetes.cpu.usage.total` and `kubernetes.filesystem.usage`.

## Further Reading

To get a better idea of how (or why) to integrate your Kubernetes service, check out our [series of blog posts][12] about it.

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kubernetes/images/kubernetes_dashboard.png
[2]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://github.com/DataDog/integrations-core/blob/master/kubernetes/datadog_checks/kubernetes/data/conf.yaml.example
[5]: https://kubernetes.io/docs/api-reference/v1.7/#configmap-v1-core
[6]: https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account
[7]: https://github.com/DataDog/integrations-core/blob/master/kubernetes/datadog_checks/kubernetes/data/conf.yaml.example#L118
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/kubernetes/metadata.csv
[10]: https://blog.kubernetes.io/2017/03/advanced-scheduling-in-kubernetes.html
[11]: https://github.com/DataDog/dd-agent/pull/3051
[12]: https://www.datadoghq.com/blog/monitoring-kubernetes-era
[13]: https://docs.datadoghq.com/integrations/kubernetes/#kubernetes-state-metrics
