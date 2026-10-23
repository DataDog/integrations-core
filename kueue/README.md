# Agent Check: Kueue

## Overview

This check monitors Kueue through the Datadog Agent.

Kueue is a Kubernetes workload queueing system that allows you to manage and schedule workloads on your Kubernetes cluster. It provides a way to prioritize and manage workloads, and to ensure that workloads are scheduled in a fair and efficient manner. This integration collects metrics from the Kueue controller manager and Kueue API server to help you monitor the health and performance of your Kueue cluster.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3].

### Installation

The Kueue check is included in the [Datadog Agent][2] package.
No additional installation is required on your server.

### Configuration

Configure this integration as an [endpoints check][14], so that each Kueue controller manager pod is scraped individually. Endpoints checks are dispatched by the Cluster Agent to the node Agent running on the node of each Kueue pod, so cluster checks must be enabled. A node Agent must run on the nodes that host Kueue; if Kueue runs on control plane nodes, add the matching tolerations to the node Agent.

Kueue serves its metrics over HTTPS (port `8443` by default) with a self-signed certificate, and authorizes callers with their service account token. The node Agent service account needs the following permissions:

- `get` on the `/metrics` non-resource URL. The default Datadog Helm chart and Datadog Operator node Agent roles already include it.
- `get` and `list` on `workloads` in the `kueue.x-k8s.io` API group, for Workload lifecycle events. Set `collect_workload_events: false` to disable event collection.

1. To collect optional ClusterQueue resource metrics, such as `kueue.cluster_queue.resource_usage.gpu`, configure Kueue with `metrics.enableClusterQueueResources: true` and restart the Kueue controller manager.

2. Provide an endpoints check configuration to the Cluster Agent, targeting the Kueue metrics Service:

   ```yaml
   clusterAgent:
     confd:
       kueue.yaml: |-
         advanced_ad_identifiers:
           - kube_endpoints:
               name: kueue-controller-manager-metrics-service
               namespace: kueue-system
         cluster_check: true
         init_config:
         instances:
           - openmetrics_endpoint: https://%%host%%:%%port%%/metrics
             tls_verify: false
             auth_token:
               reader:
                 type: file
                 path: /var/run/secrets/kubernetes.io/serviceaccount/token
               writer:
                 type: header
                 name: Authorization
                 value: "Bearer <TOKEN>"
                 placeholder: "<TOKEN>"
   ```

   `%%host%%` resolves to the IP of each Kueue pod, and `%%port%%` to the last port of the Service endpoints. If your Kueue metrics Service exposes more than one port, set the port explicitly.

3. Alternatively, annotate the Kueue metrics Service with Autodiscovery endpoints check annotations:

   ```yaml
   ad.datadoghq.com/endpoints.checks: |
     {
       "kueue": {
         "instances": [
           {
             "openmetrics_endpoint": "https://%%host%%:%%port%%/metrics",
             "tls_verify": false,
             "auth_token": {
               "reader": {"type": "file", "path": "/var/run/secrets/kubernetes.io/serviceaccount/token"},
               "writer": {"type": "header", "name": "Authorization", "value": "Bearer <TOKEN>", "placeholder": "<TOKEN>"}
             }
           }
         ]
       }
     }
   ```

A cluster check that scrapes the Service URL, such as `https://kueue-controller-manager-metrics-service.kueue-system.svc:8443/metrics`, only works with a single Kueue replica. See [High availability](#high-availability).

See the [sample kueue.d/conf.yaml][4] for all available configuration options.

### High availability

When Kueue runs with more than one replica, every replica exports the same state gauges, such as `kueue.pending_workloads` or `kueue.cluster_queue.resource_usage.*`, labeled with `replica_role:leader` or `replica_role:follower`. Most counters and histograms, and the `kueue.local_queue.resource_usage.*`, `kueue.local_queue.resource_reservation.*` and `kueue.local_queue.status` metrics, are only exported by the leader. Scraping through the Service reaches a random replica, so leader-only metrics would be missing from some collection runs. Use the endpoints check configuration above to scrape every replica.

With one check instance per replica:

- Samples labeled `replica_role:follower` are dropped, so state gauges are not reported twice. Samples without a `replica_role` label, such as Go runtime, process, and controller-runtime metrics, are reported for every replica. Set `collect_follower_metrics: true` to keep follower samples.
- Every instance polls the Workload resources, but only the instance that scraped the leader, or a replica reporting `replica_role:standalone` or no `replica_role` label, submits Workload events. The role is read from the collected samples, so do not exclude follower samples with `exclude_metrics_by_labels` or exclude every `replica_role`-labeled metric: the follower instances would then see no role and submit duplicate events.
- After a leader failover, the new leader reports its gauges immediately, and its counters start from zero. It keeps exporting the series it recorded as a follower, still labeled `replica_role:follower`; those are dropped, and the replica is treated as the leader. Transitions that its instance observes before the replica reports `replica_role:leader` are not submitted as events. Few transitions happen in this window, since Workload conditions are written by the leader.

### Cluster agent configuration and GPU monitoring integration

Enabling [GPU monitoring][13] will enrich the Kueue integration with GPU-related data, and will also show GPU-related tags in the Kueue metrics. In order to enable this part of the integration, two settings need to be configured in the Datadog Agent configuration:

```yaml
gpu:
  enabled: true

cluster_agent:
  kueue:
    enabled: true
```

### Log collection

The Kueue controller manager writes logs to its container output, which Kubernetes captures as container logs. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][12]. Logs are collected by the node Agent running on the node that hosts the Kueue controller manager.

After log collection has been enabled, set the Kueue log configuration as an Autodiscovery annotation on the controller manager's pod template. This allows it to persist despite pod restarts. Add it under `spec.template.metadata.annotations` of the `kueue-controller-manager` deployment, or set `controllerManager.manager.podAnnotations` if you install Kueue with the Helm chart:

```yaml
ad.datadoghq.com/manager.logs: |
  [
    {
      "source": "kueue",
      "service": "<SERVICE>"
    }
  ]
```

This annotation targets the container named `manager`, which is the container name used by both the Kueue release manifests and the Helm chart. Replace `manager` with the name (`.spec.containers[i].name`) of your Kueue container if you use a different name.

### Validation

[Run the Cluster Agent's `clusterchecks` subcommand][11] and look for one `kueue` check per Kueue pod under the `Pod-backed Endpoints-Checks` section. Then run the `status` subcommand on the node Agents listed for those checks.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

By default, the Kueue integration polls the Kueue Workload custom resources and sends Datadog events for lifecycle
transitions:

- `kueue.workload.created`: a Workload appears after the check has initialized its state.
- `kueue.workload.pending`: the Workload cannot reserve quota and its `QuotaReserved` condition becomes `False`
  with reason `Pending` or `Inadmissible`.
- `kueue.workload.quota_reserved`: the `QuotaReserved` condition becomes `True`.
- `kueue.workload.admitted`: the `Admitted` condition becomes `True`.
- `kueue.workload.running`: the `PodsReady` condition becomes `True`.
- `kueue.workload.evicted`: the `Evicted` condition becomes `True`.
- `kueue.workload.finished`: the `Finished` condition becomes `True`.

Events are tagged with the Workload namespace, name, UID, LocalQueue, transition, priority, and ClusterQueue when
available. Eviction events also include the eviction reason, and preemption events include the Kueue preemption reason
when available. Pending events include the reason reported by Kueue.

The first collection run seeds the Workload state and does not emit events for already existing transitions.

## Troubleshooting

Need help? Contact [Datadog support][8].


[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kueue/datadog_checks/kueue/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kueue/metadata.csv
[8]: https://docs.datadoghq.com/help/
[11]: https://docs.datadoghq.com/containers/troubleshooting/cluster-and-endpoint-checks/#dispatching-logic-in-the-cluster-agent
[12]: https://docs.datadoghq.com/containers/kubernetes/log/
[13]: https://docs.datadoghq.com/gpu_monitoring/
[14]: https://docs.datadoghq.com/containers/cluster_agent/endpointschecks/
