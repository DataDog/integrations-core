## Overview

Red Hat OpenShift is an open source container application platform based on the Kubernetes container orchestrator for enterprise application development and deployment.

> There is currently no separate `openshift` check, this README describes the necessary configuration to enable collection of OpenShift specific metrics in the Agent. Data described here are collected by the [`kube-apiserver-metrics` check][1], setting up this check is necessary to collect the `openshift.*` metrics.

## Setup

### Installation

To install the Agent, refer to the [Agent installation instructions][2] for kubernetes. The default configuration targets OpenShift 3.7.0+ and OpenShift 4.0+, as it relies on features and endpoints introduced in this version.

### Configuration

Starting with version 6.1, the Datadog Agent supports monitoring OpenShift Origin and Enterprise clusters. Depending on your needs and the [security constraints][3] of your cluster, three deployment scenarios are supported:

- [Restricted SCC operations](#restricted-scc-operations)
- [Host network SCC operations](#host-network-scc-operations)
- [Custom Datadog SCC for all features](#custom-datadog-scc-for-all-features)

| Security Context Constraints   | [Restricted](#restricted-scc-operations) | [Host network](#host-network-scc-operations) | [Custom](#custom-datadog-scc-for-all-features) |
| ------------------------------ | ---------------------------------------- | -------------------------------------------- | ---------------------------------------------- |
| Kubernetes layer monitoring    | ✅                                       | ✅                                           | ✅                                             |
| Kubernetes-based Autodiscovery | ✅                                       | ✅                                           | ✅                                             |
| Dogstatsd intake               | 🔶                                       | ✅                                           | ✅                                             |
| APM trace intake               | 🔶                                       | ✅                                           | ✅                                             |
| Logs network intake            | 🔶                                       | ✅                                           | ✅                                             |
| Host network metrics           | ❌                                       | ❌                                           | ✅                                             |
| Docker layer monitoring        | ❌                                       | ❌                                           | ✅                                             |
| Container logs collection      | ❌                                       | ❌                                           | ✅                                             |
| Live Container monitoring      | ❌                                       | ❌                                           | ✅                                             |
| Live Process monitoring        | ❌                                       | ❌                                           | ✅                                             |

<div class="alert alert-warning">
<bold>OpenShift 4.0+</bold>: If you used the OpenShift installer on a supported cloud provider, you must deploy the Agent with <code>hostNetwork: true</code> in the <code>datadog.yaml</code> configuration file to get host tags and aliases. Access to metadata servers from the PODs network is otherwise restricted.
</div>

#### Log collection

Refer to the [Kubernetes Log Collection][12] documentation for further information.

#### Restricted SCC operations

This mode does not require granting special permissions to the [`datadog-agent` daemonset][4], other than the [RBAC][5] permissions needed to access the kubelet and the APIserver. You can get started with this [kubelet-only template][6].

The recommended ingestion method for Dogstatsd, APM, and logs is to bind the Datadog Agent to a host port. This way, the target IP is constant and easily discoverable by your applications. As the default restricted OpenShift SCC does not allow to bind to host port, you can set the Agent to listen on it's own IP, but you will need to handle the discovery of that IP from your application.

The Agent suports working on a `sidecar` run mode, to enable running the Agent in your application's pod for easier discoverability.

#### Host network SCC operations

Add the `allowHostPorts` permission to the pod (either via the standard `hostnetwork` or `hostaccess` SCC, or by creating your own). In this case, you can add the relevant port bindings in your pod specs:

```yaml
ports:
  - containerPort: 8125
    name: dogstatsdport
    protocol: UDP
  - containerPort: 8126
    name: traceport
    protocol: TCP
```

#### Custom Datadog SCC for all features

If SELinux is in permissive mode or disabled, enable the `hostaccess` SCC to benefit from all features.
If SELinux is in enforcing mode, it is recommended to grant [the `spc_t` type][7] to the datadog-agent pod. In order to deploy the agent you can use the following [datadog-agent SCC][8] that can be applied after [creating the datadog-agent service account][5]. It grants the following permissions:

- `allowHostPorts: true`: Binds Dogstatsd / APM / Logs intakes to the node's IP.
- `allowHostPID: true`: Enables Origin Detection for Dogstatsd metrics submitted by Unix Socket.
- `volumes: hostPath`: Accesses the Docker socket and the host's `proc` and `cgroup` folders, for metric collection.
- `SELinux type: spc_t`: Accesses the Docker socket and all processes' `proc` and `cgroup` folders, for metric collection. You can read more about this type [in this Red Hat article][7].

<div class="alert alert-info">
Do not forget to add a <a href="https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/?tab=k8sfile#configure-rbac-permissions">datadog-agent service account</a> to the newly created <a href="https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/manifests/openshift/scc.yaml">datadog-agent SCC</a> by adding <code>system:serviceaccount:<datadog-agent namespace>:<datadog-agent service account name></code> to the <code>users</code> section.
</div>

<div class="alert alert-warning">
<b>OpenShift 4.0+</b>: If you used the OpenShift installer on a supported cloud provider, you must deploy the Agent with <code>allowHostNetwork: true</code> in the <code>datadog.yaml</code> configuration file to get host tags and aliases. Access to metadata servers from the PODs network is otherwise restricted.
</div>

**Note**: The Docker socket is owned by the root group, so you may need to elevate the Agent's privileges to pull in Docker metrics. To run the Agent process as a root user, you can configure your SCC with the following:

```yaml
runAsUser:
  type: RunAsAny
```

### Validation

See [kube_apiserver_metrics][1]

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.

### Events

The OpenShift check does not include any events.

### Service Checks

The OpenShift check does not include any Service Checks.

## Troubleshooting

Need help? Contact [Datadog support][11].

[1]: https://github.com/DataDog/integrations-core/tree/master/kube_apiserver_metrics
[2]: https://docs.datadoghq.com/agent/kubernetes
[3]: https://docs.openshift.org/latest/admin_guide/manage_scc.html
[4]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup
[5]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/?tab=k8sfile#configure-rbac-permissions
[6]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/manifests/agent-kubelet-only.yaml
[7]: https://developers.redhat.com/blog/2014/11/06/introducing-a-super-privileged-container-concept
[8]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/manifests/openshift/scc.yaml
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/openshift/metadata.csv
[11]: https://docs.datadoghq.com/help
[12]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/#log-collection
