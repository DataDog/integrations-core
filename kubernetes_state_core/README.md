# Agent Check: Kubernetes State Core

## Overview

Get metrics from Kubernetes service in real-time to:

- Visualize and monitor Kubernetes states.
- Be notified about Kubernetes failovers and events.

The Kubernetes State Metrics Core check leverages [kube-state-metrics version 2+][1] and includes major performance and tagging improvements compared to the legacy `kubernetes_state` check.

As opposed to the legacy check, with the Kubernetes State Metrics Core check, you no longer need to deploy `kube-state-metrics` in your cluster.

Kubernetes State Metrics Core provides a better alternative to the legacy `kubernetes_state` check as it offers more granular metrics and tags. See the [Major Changes][2] and [Data Collected][3] for more details.

## Setup

### Installation

The Kubernetes State Metrics Core check is included in the [Datadog Cluster Agent][4] image, so you don't need to install anything else on your Kubernetes servers.

### Requirements

- Datadog Cluster Agent v1.12+

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Helm" xxx -->

In your Helm `values.yaml`, add the following:

```yaml
datadog:
  # (...)
  kubeStateMetricsCore:
    enabled: true
```

<!-- xxz tab xxx -->
<!-- xxx tab "Operator" xxx -->

To enable the `kubernetes_state_core` check, the setting `spec.features.kubeStateMetricsCore.enabled` must be set to `true` in the DatadogAgent resource:

```yaml
apiVersion: datadoghq.com/v1alpha1
kind: DatadogAgent
metadata:
  name: datadog
spec:
  credentials:
    apiKey: <DATADOG_API_KEY>
    appKey: <DATADOG_APP_KEY>
  features:
    kubeStateMetricsCore:
      enabled: true
  # (...)
```

Note: Datadog Operator v0.7.0 or greater is required.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

## Migration from kubernetes_state to kubernetes_state_core

### Tags removal

In the original `kubernetes_state` check, several tags have been flagged as deprecated and replaced by new tags. To determine your migration path, check which tags are submitted with your metrics.

In the `kubernetes_state_core` check, only the non-deprecated tags are submitted. Before migrating from `kubernetes_state` to `kubernetes_state_core`, verify that only official tags are used in monitors and dashboards.

Here is the mapping between deprecated tags and the official tags that have replaced them:

| deprecated tag        | official tag                |
|-----------------------|-----------------------------|
| cluster_name          | kube_cluster_name           |
| container             | kube_container_name         |
| cronjob               | kube_cronjob                |
| daemonset             | kube_daemon_set             |
| deployment            | kube_deployment             |
| image                 | image_name                  |
| job                   | kube_job                    |
| job_name              | kube_job                    |
| namespace             | kube_namespace              |
| phase                 | pod_phase                   |
| pod                   | pod_name                    |
| replicaset            | kube_replica_set            |
| replicationcontroller | kube_replication_controller |
| statefulset           | kube_stateful_set           |

### Backward incompatibility changes

The Kubernetes State Metrics Core check is not backward compatible, be sure to read the changes carefully before migrating from the legacy `kubernetes_state` check.

`kubernetes_state.node.by_condition`
: A new metric with node name granularity. It replaces `kubernetes_state.nodes.by_condition`.

`kubernetes_state.persistentvolume.by_phase`
: A new metric with persistentvolume name granularity. It replaces `kubernetes_state.persistentvolumes.by_phase`.

`kubernetes_state.pod.status_phase`
: The metric is tagged with pod level tags, like `pod_name`.

`kubernetes_state.node.count`
: The metric is not tagged with `host` anymore. It aggregates the nodes count by `kernel_version` `os_image` `container_runtime_version` `kubelet_version`.

`kubernetes_state.container.waiting` and `kubernetes_state.container.status_report.count.waiting`
: These metrics no longer emit a 0 value if no pods are waiting. They only report non-zero values.

`kube_job`
: In `kubernetes_state`, the `kube_job` tag value is the `CronJob` name if the `Job` had `CronJob` as an owner, otherwise it is the `Job` name. In `kubernetes_state_core`, the `kube_job` tag value is always the `Job` name, and a new `kube_cronjob` tag key is added with the `CronJob` name as the tag value. When migrating to `kubernetes_state_core`, it's recommended to use the new tag or `kube_job:foo*`, where `foo` is the `CronJob` name, for query filters.

<!-- xxx tabs xxx -->
<!-- xxx tab "Helm" xxx -->

Enabling `kubeStateMetricsCore` in your Helm `values.yaml` configures the Agent to ignore the auto configuration file for legacy `kubernetes_state` check. The goal is to avoid running both checks simultaneously.

If you still want to enable both checks simultaneously for the migration phase, disable the `ignoreLegacyKSMCheck` field in your `values.yaml`.

**Note**: `ignoreLegacyKSMCheck` makes the Agent only ignore the auto configuration for the legacy `kubernetes_state` check. Custom `kubernetes_state` configurations need to be removed manually.

The Kubernetes State Metrics Core check does not require deploying `kube-state-metrics` in your cluster anymore, you can disable deploying `kube-state-metrics` as part of the Datadog Helm Chart. To do this, add the following in your Helm `values.yaml`:

```yaml
datadog:
  # (...)
  kubeStateMetricsEnabled: false
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

**Important Note:** The Kubernetes State Metrics Core check is an alternative to the legacy `kubernetes_state` check. Datadog recommends not enabling both checks simultaneously to guarantee consistent metrics.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

**Note:** You can configure [Datadog Standard labels][6] on your Kubernetes objects to get the `env` `service` `version` tags.

### Events

The Kubernetes State Metrics Core check does not include any events.

### Service Checks

See [../kubernetes/assets/service_checks.json][7] for a list of service checks provided by this integration.

### Validation

[Run the Cluster Agent's `status` subcommand][8] inside your Cluster Agent container and look for `kubernetes_state_core` under the Checks section.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

{{< partial name="whats-next/whats-next.html" >}}


[1]: https://kubernetes.io/blog/2021/04/13/kube-state-metrics-v-2-0/
[2]: /integrations/kubernetes_state_core/#migration-from-kubernetes_state-to-kubernetes_state_core
[3]: /integrations/kubernetes_state_core/#data-collected
[4]: /agent/cluster_agent/
[5]: https://github.com/DataDog/integrations-core/blob/master/kubernetes_state_core/metadata.csv
[6]: /getting_started/tagging/unified_service_tagging/?tab=kubernetes#configuration-1
[7]: https://github.com/DataDog/integrations-core/blob/master/kubernetes/assets/service_checks.json
[8]: /agent/guide/agent-commands/?tab=clusteragent#agent-status-and-information
[9]: https://docs.datadoghq.com/help/
