## Overview

Red Hat OpenShift is an open source container application platform based on the Kubernetes container orchestrator for enterprise application development and deployment.

## Setup
### Installation

To install the Agent, refer to the [Agent installation instructions][1] for kubernetes. The default configuration targets OpenShift 3.7.0 and later, as it relies on features and endpoints introduced in this version.

### Configuration

Starting with version 6.1, the Datadog Agent supports monitoring OpenShift Origin and Enterprise clusters. Depending on your needs and the [security constraints][2] of your cluster, three deployment scenarios are supported:

* [Restricted SCC operations](#restricted-scc-operations)
* [Host network SCC operations](#host-network-scc-operations)
* [Custom Datadog SCC for all features](#custom-datadog-scc-for-all-features)

| Security Context Constraints   | [Restricted](#restricted-scc-operations) | [Host network](#host-network-scc-operations) | [Custom](#custom-datadog-scc-for-all-features) |
|--------------------------------|------------------------------------------|----------------------------------------------|------------------------------------------------|
| Kubernetes layer monitoring    | ✅                                        | ✅                                            | ✅                                              |
| Kubernetes-based Autodiscovery | ✅                                        | ✅                                            | ✅                                              |
| Dogstatsd intake               | 🔶                                       | ✅                                            | ✅                                              |
| APM trace intake               | 🔶                                       | ✅                                            | ✅                                              |
| Logs network intake            | 🔶                                       | ✅                                            | ✅                                              |
| Host network metrics           | ❌                                        | ❌                                            | ✅                                              |
| Docker layer monitoring        | ❌                                        | ❌                                            | ✅                                              |
| Container logs collection      | ❌                                        | ❌                                            | ✅                                              |
| Live Container monitoring      | ❌                                        | ❌                                            | ✅                                              |
| Live Process monitoring        | ❌                                        | ❌                                            | ✅                                              |

#### Restricted SCC operations

This mode does not require granting special permissions to the [`datadog-agent` daemonset][3], other than the [RBAC][4] permissions needed to access the kubelet and the APIserver. You can get started with this [kubelet-only template][5].

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
If SELinux is in enforcing mode, it is recommend to grant [the `spc_t` type][6] to the datadog-agent pod. In order to deploy our agent, Datadog created a [datadog-agent SCC][7] that you can apply after [creating the datadog-agent service account][4]. It grants the following permissions:

* `allowHostPorts: true`: Binds Dogstatsd / APM / Logs intakes to the node's IP.
* `allowHostPID: true`: Enables Origin Detection for Dogstatsd metrics submitted by Unix Socket.
* `volumes: hostPath`: Accesses the Docker socket and the host's `proc` and `cgroup` folders, for metric collection.
* `SELinux type: spc_t`: Accesses the Docker socket and all processes' `proc` and `cgroup` folders, for metric collection. You can read more about this type [in this Red Hat article][6].

### Validation

Run the [Agent’s status subcommand][8] and look for openshift under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Events
The OpenShift check does not include any events.

### Service Checks
The OpenShift check does not include any Service Checks.

## Troubleshooting
Need help? Contact [Datadog support][10].


[1]: https://docs.datadoghq.com/agent/kubernetes
[2]: https://docs.openshift.org/latest/admin_guide/manage_scc.html
[3]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup
[4]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/?tab=k8sfile#configure-rbac-permissions
[5]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/manifests/agent-kubelet-only.yaml
[6]: https://developers.redhat.com/blog/2014/11/06/introducing-a-super-privileged-container-concept
[7]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/manifests/openshift/scc.yaml
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/openshift/metadata.csv
[10]: https://docs.datadoghq.com/help
