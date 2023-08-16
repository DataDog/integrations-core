# Agent Check: Helm

## Overview

This check monitors Helm deployments through the Datadog Agent.

Helm supports multiple storage backends. In v3, Helm defaults to Kubernetes secrets and in v2, Helm defaults to ConfigMaps. This check supports both options.

## Setup

### Installation

The Helm check is included in the [Datadog Agent][1] package.
No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Helm" xxx -->

This is a cluster check. You can enable this check by adding `datadog.helmCheck.enabled` to your Helm chart.

**Note**: If no configuration is required, an empty `conf.d` can be passed.

For more information, see the [Cluster Check documentation][2].

<!-- xxz tab xxx -->
<!-- xxx tab "Operator" xxx -->

This is a cluster check. You can enable this check by providing a configuration file `helm.yaml` to the cluster Agent in your `DatadogAgent` deployment configuration.

```
apiVersion: datadoghq.com/v2alpha1
kind: DatadogAgent
metadata:
  name: datadog
spec:
  [...]
  override:
    clusterAgent:
      [...]
      extraConfd:
        configDataMap:
          helm.yaml: |-
            init_config:
            instances:
            - collect_events: false
```

This check requires additional permissions bound to the Kubernetes service account used by the cluster Agent pod to access the releases stored by Helm.

```
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: datadog-helm-check
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: datadog-helm-check
subjects:
  - kind: ServiceAccount
    name: datadog-cluster-agent
    namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: datadog-helm-check
rules:
- apiGroups:
  - ""
  resources:
  - secrets
  - configmaps
  verbs:
  - get
  - list
  - watch
```

**Note**: The `ServiceAccount` subject is an example with the installation in the `default` namespace. Adjust `name` and `namespace` in accordance with your deployment.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][3] and look for `helm` under the Checks section.

## Data Collected

### Metrics

This check reports a gauge, `helm.release`, set to 1 for each release deployed
in the cluster. The metric has tags that identify the Helm release such as name, app
version, chart version, and revision.

See [metadata.csv][4] for a list of metrics provided by this check.

### Events

This check emits events when the `collect_events` option is set to `true`. The default is `false`.

When the option is enabled, the check emits events when:
- A new release is deployed.
- A release is deleted.
- A release is upgraded (new revision).
- There's a status change, for example from deployed to superseded.

### Service Checks

See [service_checks.json][5] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][6].

## Further Reading

Additional helpful documentation, links, and articles:

- [Blog: Monitor your Helm-managed Kubernetes applications with Datadog][7]


[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://docs.datadoghq.com/agent/cluster_agent/clusterchecks/
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/helm/metadata.csv
[5]: https://github.com/DataDog/integrations-core/blob/master/helm/assets/service_checks.json
[6]: https://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/monitor-helm-kubernetes-with-datadog/
