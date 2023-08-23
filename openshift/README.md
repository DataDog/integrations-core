## Overview

Red Hat OpenShift is an open source container application platform based on the Kubernetes container orchestrator for enterprise application development and deployment.

> This README describes the necessary configuration to enable collection of OpenShift-specific metrics in the Agent. Data described here are collected by the [`kubernetes_apiserver` check][1]. You must configure the check to collect the `openshift.*` metrics.

## Setup

### Installation

To install the Agent, see the [Agent installation instructions][2] for Kubernetes. The default configuration targets OpenShift 3.7.0+ and OpenShift 4.0+, as it relies on features and endpoints introduced in this version.

Alternatively, the [Datadog Operator][3] can be used to install and manage the Datadog Agent. The Datadog Operator can be installed using OpenShift's [OperatorHub][4].

### Security Context Constraints configuration


If you are deploying the Datadog Agent using any of the methods linked in the installation instructions above, you must include Security Context Constraints (SCCs) for the Agent to collect data. Follow the instructions below as they relate to your deployment.

<!-- xxx tabs xxx -->
<!-- xxx tab "Helm" xxx -->

The SCC can be applied directly within your Datadog agent's `values.yaml`. Add the following block underneath the `agents:` section in the file. 

```yaml
...
agents:
...
  podSecurity:
    securityContextConstraints:
      create: true
...
```

You can apply this when you initially deploy the Agent. Or, you can execute a `helm upgrade` after making this change to apply the SCC. 

<!-- xxz tab xxx -->
<!-- xxx tab "Daemonset" xxx -->

Depending on your needs and the [security constraints][5] of your cluster, three deployment scenarios are supported:

- [Restricted SCC operations](#restricted-scc-operations)
- [Host network SCC operations](#host)
- [Custom Datadog SCC for all features](#custom-datadog-scc-for-all-features)

| Security Context Constraints   | [Restricted](#restricted-scc-operations) | [Host network](#host) | [Custom](#custom-datadog-scc-for-all-features) |
|--------------------------------|------------------------------------------|-----------------------|------------------------------------------------|
| Kubernetes layer monitoring    | Supported                                | Supported             | Supported                                             |
| Kubernetes-based Autodiscovery | Supported                                | Supported             | Supported                                             |
| Dogstatsd intake               | Not supported                            | Supported             | Supported                                             |
| APM trace intake               | Not supported                            | Supported             | Supported                                             |
| Logs network intake            | Not supported                            | Supported             | Supported                                             |
| Host network metrics           | Not supported                            | Supported             | Supported                                             |
| Docker layer monitoring        | Not supported                            | Not supported         | Supported                                             |
| Container logs collection      | Not supported                            | Not supported         | Supported                                             |
| Live Container monitoring      | Not supported                            | Not supported         | Supported                                             |
| Live Process monitoring        | Not supported                            | Not supported         | Supported                                             |


<!-- xxz tab xxx -->
<!-- xxx tab "Operator" xxx -->

For instructions on how to install the Datadog Operator and `DatadogAgent` resource in OpenShift, see the [OpenShift installation guide][6].

If the Operator has been deployed with Operator Lifecycle Manager (OLM), then the necessary default SCCs present in OpenShift are automatically associated with the `datadog-agent-scc` `ServiceAccount` The Agent can then be deployed with the `DatadogAgent` CustomResourceDefinition, referencing this Service Account on the Node Agent and Cluster Agent pods.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx --> 

#### Log collection

See [Kubernetes Log Collection][7] for further information.

#### Restricted SCC operations

This mode does not require granting special permissions to the [`datadog-agent` daemonset][8], other than the [RBAC][9] permissions needed to access the kubelet and the APIserver. You can get started with this [kubelet-only template][10].

The recommended ingestion method for Dogstatsd, APM, and logs is to bind the Datadog Agent to a host port. This way, the target IP is constant and easily discoverable by your applications. The default restricted OpenShift SCC does not allow binding to the host port. You can set the Agent to listen on it's own IP, but you need to handle the discovery of that IP from your application.

The Agent supports working on a `sidecar` run mode, to enable running the Agent in your application's pod for easier discoverability.

#### Host

Add the `allowHostPorts` permission to the pod with the standard `hostnetwork` or `hostaccess` SCC, or by creating your own. In this case, you can add the relevant port bindings in your pod specs:

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
If SELinux is in enforcing mode, it is recommended to grant [the `spc_t` type][11] to the datadog-agent pod. In order to deploy the agent you can use the following [datadog-agent SCC][12] that can be applied after [creating the datadog-agent service account][9]. It grants the following permissions:

- `allowHostPorts: true`: Binds Dogstatsd / APM / Logs intakes to the node's IP.
- `allowHostPID: true`: Enables Origin Detection for Dogstatsd metrics submitted by Unix Socket.
- `volumes: hostPath`: Accesses the Docker socket and the host's `proc` and `cgroup` folders, for metric collection.
- `SELinux type: spc_t`: Accesses the Docker socket and all processes' `proc` and `cgroup` folders, for metric collection. See [Introducing a Super Privileged Container Concept][11] for more details.

<div class="alert alert-info">
Do not forget to add a <a href="https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/?tab=k8sfile#configure-rbac-permissions">datadog-agent service account</a> to the newly created <a href="https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/manifests/openshift/scc.yaml">datadog-agent SCC</a> by adding <code>system:serviceaccount:<datadog-agent namespace>:<datadog-agent service account name></code> to the <code>users</code> section.
</div>

<div class="alert alert-warning">
<b>OpenShift 4.0+</b>: If you used the OpenShift installer on a supported cloud provider, you must deploy the SCC with <code>allowHostNetwork: true</code> in the <code>scc.yaml</code> manifest, as well as <code>hostNetwork: true</code> in the Agent configuration to get host tags and aliases. Access to metadata servers from the Pod network is otherwise restricted.
</div>

**Note**: The Docker socket is owned by the root group, so you may need to elevate the Agent's privileges to pull in Docker metrics. To run the Agent process as a root user, you can configure your SCC with the following:

```yaml
runAsUser:
  type: RunAsAny
```

### Validation

See [kubernetes_apiserver][1]

## Data Collected

### Metrics

See [metadata.csv][13] for a list of metrics provided by this integration.

### Events

The OpenShift check does not include any events.

### Service Checks

The OpenShift check does not include any Service Checks.

## Troubleshooting

Need help? Contact [Datadog support][14].

[1]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/kubernetes_apiserver.d/conf.yaml.example
[2]: https://docs.datadoghq.com/agent/kubernetes/
[3]: https://github.com/DataDog/datadog-operator/
[4]: https://docs.openshift.com/container-platform/4.10/operators/understanding/olm-understanding-operatorhub.html
[5]: https://docs.openshift.com/enterprise/3.0/admin_guide/manage_scc.html
[6]: https://github.com/DataDog/datadog-operator/blob/main/docs/install-openshift.md
[7]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=daemonset
[8]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/
[9]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/?tab=k8sfile#configure-rbac-permissions
[10]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/manifests/agent-kubelet-only.yaml
[11]: https://developers.redhat.com/blog/2014/11/06/introducing-a-super-privileged-container-concept
[12]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/manifests/openshift/scc.yaml
[13]: https://github.com/DataDog/integrations-core/blob/master/openshift/metadata.csv
[14]: https://docs.datadoghq.com/help/
