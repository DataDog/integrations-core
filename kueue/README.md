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
- `get` and `list` on `workloads` in the `kueue.x-k8s.io` API group, for Workload lifecycle events and the experimental scheduling goodput. Set `collect_workload_events: false` to disable event collection. Scheduling goodput still needs these permissions when `collect_scheduling_goodput` is enabled, and it keeps working when `collect_workload_events` is `false`, such as when the Cluster Agent `job_scheduler_events` check sends the Workload events.

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
available. Instance tags, including the tags you set in `tags` and the tags Autodiscovery adds from the controller pod,
apply to metrics only, not to events. Eviction events also include the eviction reason, and preemption events include
the Kueue preemption reason when available. Pending events include the reason reported by Kueue.

Events also carry the scheduler tags that the Agent adds to the pods of every batch scheduler, so that the same
queries work for Kueue and other schedulers: `job_scheduler:kueue`, `job_scheduler_workload` (the Workload name), and
`job_scheduler_queue` (the ClusterQueue, when the Workload has been admitted).

Each event also carries `kueue_workload_event_index`, a per-Workload integer that increases for every event the check
emits for that Workload. Kueue often stamps several transitions with the same second-resolution timestamp; sort by
`timestamp`, then by `kueue_workload_event_index` as an integer, to order those events. The index is kept in the Agent
persistent cache so a process restart continues the sequence for Workloads still present in the API. The cache is
cleared when the check configuration changes, and a new pod starts the sequence at `0` because the run directory is
not preserved across container recreation.

The first collection run seeds the Workload state and does not emit events for already existing transitions.

### Scheduling goodput (experimental)

Set `collect_scheduling_goodput: true` to measure how much of the GPU time that Kueue Workloads request is spent waiting to become fully runnable. A GPU Workload is one whose pods request `nvidia.com/gpu` or `amd.com/gpu`. The check doesn't count MIG profiles or other GPU partitions. On every run, each GPU Workload adds the time since the previous run, multiplied by its requested GPUs, to one of two counts. The check submits both counts in GPU-hours, as one series per Workload:

- `gpu.scheduling.badput_time`: the Workload waits for quota, for admission, or for its pods to be ready, or it was evicted or preempted and waits to be admitted again. It is tagged with a `reason`, one of six general categories shared with the other scheduler integrations, such as `quota_or_capacity` or `startup_or_system`, and with the raw Kueue `scheduler_reason` when Kueue reports one.
- `gpu.scheduling.fully_admitted_time`: the Workload is admitted and Kueue reports `PodsReady`.

Badput doesn't stop when Kueue admits a Workload. It stops once Kueue reports `PodsReady=True`, so a Workload that is admitted but whose pods are pending or only partly ready keeps accumulating badput, with `reason:startup_or_system`. After a preemption, the badput is tagged `reason:preemption_or_reclaim` until Kueue admits the Workload again.

The `reason` tag is derived from the blocking Workload condition, mostly `QuotaReserved=False`. `scheduler_reason` keeps the raw Kueue value for detail, so the `reason` tag has a fixed set of six values:

| `reason` | What it means | Kueue `scheduler_reason` |
|---|---|---|
| `quota_or_capacity` | The Workload waits for capacity because of quota or allocation policies. Compare the declared quota with the fleet to decide whether to rebalance quota or add capacity. | `WaitingForQuota`, `ExceedsMaxQuota` |
| `placement_or_topology` | Capacity may exist, but it can't satisfy the placement requirements. Investigate placement and fragmentation. `NoMatchingFlavor` can also be a configuration issue. | `TopologyPlacementFailed`, `NoMatchingFlavor` |
| `configuration_or_request` | The Workload, queue, or resource configuration prevents the admission. Review and correct the request or the configuration. | `Misconfigured`, `ClusterQueueStopped`, `LocalQueueStopped` |
| `preemption_or_reclaim` | The Workload waits for resources to be reclaimed, or it lost its resources to another Workload. Review the priority and borrowing policies. | `WaitingForPreemptedWorkloads`, and a Workload that Kueue preempted and hasn't admitted again, with the reason of its `Preempted` condition |
| `startup_or_system` | The Workload can't become runnable because of startup, infrastructure, or control-plane problems. Pod and infrastructure data are needed to find the cause. | `WaitingForPodsReady`, `WaitForStart`, `PodsReadyTimeout`, `UnsatisfiedAdmissionChecks`, `UnsatisfiedChecks`, `NoReservationUnsatisfiedChecks`, `AdmissionCheck` |
| `other_or_unknown` | Evaluation is pending, the Workload is suspended (which can be intentional), or there isn't enough context to classify it. | `PendingEvaluation`, `Suspended`, `DRAResourcesUnresolved`, `UnrecordableResourceUsage`, and any other value |

To investigate badput:

1. Detect high scheduling badput and use `reason` to find the type of blocking condition. Use `scheduler_reason` for the exact Kueue condition.
2. Find the Workloads with the highest waiting time, with `job_scheduler_workload`, and group them by `gpu_type`.
3. Correlate the result with the state of that GPU fleet. For example, if most affected Workloads request A100s, inspect the A100 fleet.

Without the `UnadmittedWorkloadsObservability` feature gate, Kueue reports `Pending` or `Inadmissible`, and the check reads the cause from the condition message.

**Requirements**: Kueue reports `PodsReady` only when [`waitForPodsReady`][16] is enabled. Without it, the check can't measure the fully admitted time, so it submits no goodput metrics and logs a warning. The node Agent needs `get` and `list` on `workloads.kueue.x-k8s.io`. Only the instance that scraped the Kueue leader submits the metrics. The `workload_events_namespaces` option also limits which Workloads the check counts.

**Querying**: The scheduling goodput of a group, such as a ClusterQueue, is `fully_admitted_time / (fully_admitted_time + badput_time)` summed over its series:

```text
sum:gpu.scheduling.fully_admitted_time{*} by {kueue_cluster_queue}.as_count().fill(zero) / (sum:gpu.scheduling.fully_admitted_time{*} by {kueue_cluster_queue}.as_count().fill(zero) + sum:gpu.scheduling.badput_time{*} by {kueue_cluster_queue}.as_count().fill(zero))
```

Use `.fill(zero)` so that a group that stops reporting does not repeat its last value. On every run where a Workload is counted, it submits both metrics, with a value of 0 for the metric that doesn't apply. This way, a group's goodput is defined even when all its Workloads are waiting or all are running. The 0 `badput_time` point has no `reason` tag, so grouping badput by `reason` shows an extra group with no reason. A Workload name is unique only within a namespace, so group by `kube_namespace` and `kueue_workload` to look at a single Workload.

**Tags**: Both metrics are tagged with `kueue_workload`, `kueue_local_queue`, `kube_namespace`, and the scheduler tags shared by all batch schedulers: `job_scheduler:kueue` and `job_scheduler_workload` (the Workload name). When the ClusterQueue is known, they're also tagged with `kueue_cluster_queue` and `job_scheduler_queue`. The shared tags match the ones on the Workload events, so the same queries work for Kueue and KAI. A Workload that isn't admitted yet has no ClusterQueue, so the check reads it from the Agent tagger. Both metrics also carry `gpu_type` (for example `a100`), when it's known. Once Kueue assigned a ResourceFlavor, it comes from the Agent tagger, which reads it from the flavor's `nvidia.com/gpu.product` node label, like the `gpu_type` of the Agent's GPU metrics. Before that, the check uses the model that the Workload's pods require in their `nodeSelector` or `nodeAffinity`. Without either, the tag is unset. The tagger lookup requires [Kueue metadata in the Cluster Agent](#cluster-agent-configuration-and-gpu-monitoring-integration), and the Cluster Agent service account needs `get`, `list`, and `watch` on `localqueues`, `clusterqueues`, `resourceflavors`, and `workloads` in the `kueue.x-k8s.io` API group. Without them, the badput of pending Workloads has no ClusterQueue tag, so group goodput by `kueue_local_queue` instead. The check doesn't add instance tags, including the tags that Autodiscovery adds from the controller pod, so they don't collide with the Workload's tags.

**Cost**: Each Workload active in an hour adds at least two custom metric series, plus one per extra badput reason and per `gpu_type` value it has over its life, so the number of series grows with how many Workloads are created.

### Service Checks

See [service_checks.json][15] for a list of service checks provided by this integration.

## Uninstallation

To disable the integration, remove the `kueue.yaml` entry from the Cluster Agent `confd` configuration, or remove the Autodiscovery annotations from the Kueue metrics Service.

## Support

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
[15]: https://github.com/DataDog/integrations-core/blob/master/kueue/assets/service_checks.json
[16]: https://kueue.sigs.k8s.io/docs/tasks/manage/setup_wait_for_pods_ready/
