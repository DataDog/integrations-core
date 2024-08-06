# Agent Check: Kubevirt Controller

## Overview

This check monitors [Kubevirt Controller][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Kubevirt Controller check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

The main use case to run the `kubevirt_controller` check is as a [cluster level check][4].

In order to do that, you will need to update some RBAC permissions to give the datadog-agent read-only access to the`KubeVirt` resources by following the steps below:

1. Bind the `kubevirt.io:view` ClusterRole to the `datadog-agent` service account:

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

2. Annotate the pods template of your `virt-controller` deployment by patching the `KubeVirt` resource as follows:

```yaml
apiVersion: kubevirt.io/v1
kind: KubeVirt
metadata:
  name: kubevirt
  namespace: kubevirt
spec:
  certificateRotateStrategy: {}
  configuration: {}
  customizeComponents:
    patches:
    - resourceType: Deployment
        resourceName: virt-controller
        patch: '{"spec": {"template":{"metadata":{"annotations":{ "ad.datadoghq.com/virt-controller.check_names": "[\"kubevirt_controller\"]", "ad.datadoghq.com/virt-controller.init_configs": "[{}]", "ad.datadoghq.com/virt-controller.instances": "[{ \"kubevirt_controller_metrics_endpoint\": \"https://%%host%%:%%port%%/metrics\",\"kubevirt_controller_healthz_endpoint\": \"https://%%host%%:%%port%%/healthz\", \"kube_namespace\":\"%%kube_namespace%%\", \"kube_pod_name\":\"%%kube_pod_name%%\", \"kube_cluster_name\": \"<DD_CLUSTER_NAME>\", \"tls_verify\": \"false\"}]"}}}}}'
        type: strategic
```

Replace `<DD_CLUSTER_NAME>` with the name you want for your cluster.

### Validation

[Run the Cluster Agent's `clusterchecks` subcommand][7] inside your Cluster Agent container and look for the `kubevirt_api` check under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Kubevirt Controller integration does not include any events.

### Service Checks

The Kubevirt Controller integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kubevirt_controller/datadog_checks/kubevirt_controller/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kubevirt_controller/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kubevirt_controller/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
