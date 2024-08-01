# Agent Check: Kubevirt API

## Overview

This check monitors [Kubevirt API][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Kubevirt API check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

The main use case to run the `kubevirt_api` check is as a [cluster level check][4].

In order to do that, you will need to update some RBAC permissions to give the datadog-agent read-only access to the `Pods` and `KubeVirt` resources by following the steps below:

1. Add the `get` and `list` pods permissions to the `datadog-agent` service account:

   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRole
   metadata:
   name: datadog-agent-pods
   rules:
   - apiGroups:
       - ""
       resources:
       - pods
       verbs:
       - get
       - list
   ---
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRoleBinding
   metadata:
   labels:
   name: datadog-agent-pods-binding
   roleRef:
   apiGroup: rbac.authorization.k8s.io
   kind: ClusterRole
   name: datadog-agent-pods
   subjects:
   - kind: ServiceAccount
       name: datadog-agent
       namespace: default
   ```

2. Bind the `kubevirt.io:view` ClusterRole to the `datadog-agent` service account:

   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRoleBinding
   metadata:
   name: datadog-agent-kubevirt
   roleRef:
   apiGroup: rbac.authorization.k8s.io
   kind: ClusterRole
   name: kubevirt.io:view
   subjects:

   - kind: ServiceAccount
   name: datadog-agent
   namespace: default
   ```

3. Annotate the service of your `virt-api` with the following:

   Replace `DD_CLUSTER_NAME` with the name you want for your cluster and `KUBE_NAMESPACE` with the namespace where you have deployed KubeVirt.

   ```yaml
   annotations:
   ad.datadoghq.com/endpoints.check_names: '["kubevirt_api"]'
   ad.datadoghq.com/endpoints.init_configs: "[{}]"
   ad.datadoghq.com/endpoints.instances: '[{ "kube_cluster_name": "<DD_CLUSTER_NAME>", "KUBE_NAMESPACE": "<kube_namespace>", "kubevirt_api_metrics_endpoint": "https://%%host%%:%%port%%/metrics", "kubevirt_api_healthz_endpoint": "https://%%host%%:%%port%%/healthz"}]'
   ```

Then the Datadog Cluster Agent schedules the check(s) for each endpoint onto Datadog Agent(s).

### Validation

[Run the Cluster Agent's `clusterchecks` subcommand][7] inside your Cluster Agent container and look for the `kubevirt_api` check under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The Kubevirt API integration does not include any events.

### Service Checks

The Kubevirt API integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://docs.datadoghq.com/integrations/kubevirt_api
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://docs.datadoghq.com/containers/cluster_agent/clusterchecks/?tab=datadogoperator
[7]: https://docs.datadoghq.com/containers/troubleshooting/cluster-and-endpoint-checks/#dispatching-logic-in-the-cluster-agent
[8]: https://github.com/DataDog/integrations-core/blob/master/kubevirt_api/metadata.csv
[9]: https://docs.datadoghq.com/help/
