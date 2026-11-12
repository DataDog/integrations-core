# Agent Check: KAI Scheduler

## Overview

This check monitors [KAI Scheduler][1] through the Datadog Agent.

KAI Scheduler is a Kubernetes scheduler for AI and GPU workloads. It schedules pods into hierarchical queues with quotas, fair share, priorities, and preemption. This integration collects metrics from the KAI scheduler and queue-controller to help you monitor queue quotas and allocation, fair share, scheduling latency, and preemption, and sends events for PodGroup life cycle transitions.

## Setup

### Installation

The KAI Scheduler check is included in the [Datadog Agent][2] package.
No additional installation is required on your server.

### Configuration

This integration is part of GPU Monitoring. Enable GPU Monitoring in the configuration of the Agent that runs the check, which is the Cluster Check Runner or node Agent that the cluster check is dispatched to:

```yaml
gpu:
  enabled: true
```

The equivalent environment variable is `DD_GPU_ENABLED=true`. When GPU Monitoring is disabled, the Agent skips every configured KAI Scheduler instance.

KAI Scheduler exposes its metrics from two deployments in the `kai-scheduler` namespace. Each one serves Prometheus metrics over plain HTTP on port `8080`:

- The scheduler, through the `kai-scheduler-<shard>` service (`kai-scheduler-default` for the default shard), serves scheduling cycle, action, preemption, and queue fair share metrics.
- The queue-controller, through the `queue-controller` service, serves queue quota and allocation metrics.

A single instance scrapes any combination of these endpoints. Each metric is tagged with `kai_component` (`scheduler` or `queue_controller`) so that the generic metrics of each component can be told apart.

KAI Scheduler is a cluster-level service. Configure this integration as a Cluster Agent [cluster check][10] so only one Agent instance scrapes the endpoints. For file- or ConfigMap-based configuration, set `cluster_check: true` in the instance:

```yaml
clusterAgent:
  confd:
    kai_scheduler.yaml: |-
      cluster_check: true
      init_config:
      instances:
      - scheduler_endpoint: http://kai-scheduler-default.kai-scheduler.svc:8080/metrics
        queue_controller_endpoint: http://queue-controller.kai-scheduler.svc:8080/metrics
```

If you run several scheduling shards, add one `scheduler_endpoint` instance per shard service.
If you enable `collect_podgroup_events` on more than one instance, each instance polls every PodGroup in the cluster and reports the same [events](#events). Set `collect_podgroup_events: false` on all instances except one.

#### Binder metrics (optional)

The binder, through the `binder` service, binds the pods that the scheduler places. It exposes no KAI-specific metrics, only generic controller-runtime, Go, and process metrics. Its `bindrequest` controller reconcile errors, reconcile latency, and work queue depth show pods that the scheduler placed but that failed to bind, for example because of a GPU sharing reservation or volume error. To collect them, add `binder_endpoint: http://binder.kai-scheduler.svc:8080/metrics` to the instance. These metrics are tagged with `kai_component:binder`.

See the [sample kai_scheduler.d/conf.yaml][4] for all available configuration options.

#### Metrics namespace

The check expects KAI's default metrics namespace, `kai`. Do not change it with the `--metrics-namespace` flag or the `queueController.metricsNamespace` setting. The scheduler also exposes an unprefixed copy of each of its metrics that is never updated, so the check only collects the `kai_`-prefixed names.

### Validation

[Run the Cluster Agent's `clusterchecks` subcommand][11] and look for `kai_scheduler` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

Queue metrics from the scheduler and the queue-controller share the `kai_queue` tag, which holds the queue's `metadata.name`, so that quota, allocation, fair share, and usage can be compared per queue. Queues with a `spec.displayName` are also tagged with `kai_queue_display_name`. Tags without a value, such as labels that KAI leaves empty, are not submitted. Memory metrics are reported in bytes, CPU metrics in cores, and GPU metrics in devices.

KAI counts evicted pods per pod group and never deletes those series. To keep the number of contexts bounded, `kai.evicted_pods.count` reports the pods evicted since the previous check run, summed by `kube_namespace`, `kai_nodepool`, and `action`. Evictions that happened before the first successful check run are not reported. The check keeps the previous value of up to 10,000 pod group series. Beyond that, it reports the increase of the summed counters instead, which undercounts evictions in a group whose pod group series KAI removed during that check run. To see which workloads were evicted and by which preemptor, use the `kai.podgroup.evicted` [events](#events).

The `kai.scheduling_cycle.latency.milliseconds`, `kai.session.*.latency.milliseconds`, `kai.action.latency.milliseconds`, and `kai.plugin.latency.milliseconds` gauges hold the duration of the most recent scheduling cycle only. The scheduler runs a cycle every second by default, so each check run samples one cycle and short spikes between check runs are not visible. A scheduler that is consistently slow is still visible in every sample.

Histograms, such as `kai.task.scheduling_latency.milliseconds` and `kai.task.bind_latency.milliseconds`, are submitted as [distributions][12] so that percentiles can be queried, along with their `.count` and `.sum` counters. Set `histogram_buckets_as_distributions: false` to submit the buckets as `.bucket` counts instead.

### Events

By default, the KAI Scheduler integration polls the KAI PodGroup custom resources and sends Datadog events for life cycle transitions:

- **Created** (`kai.podgroup.created`): A PodGroup appears after the check has initialized its state.
- **Pending** (`kai.podgroup.pending`): The scheduler cannot schedule the PodGroup on a node pool and adds an `UnschedulableOnNodePool` scheduling condition for it.
- **Admitted** (`kai.podgroup.admitted`): The scheduler allocates pods to a PodGroup that has none allocated, such as a new PodGroup, an evicted one, or a Job that starts its next pod, and updates its `kai.scheduler/last-start-timestamp` annotation.
- **Evicted** (`kai.podgroup.evicted`): The scheduler evicts some or all of the PodGroup's pods to preempt, reclaim, or consolidate, or because they are background pods whose capacity it gives to other pods, and updates its `kai.scheduler/last-eviction-timestamp` annotation. KAI sets this annotation starting with version `0.17.0`. Stale gang evictions do not update it, so they are only counted in `kai.evicted_pods.count`.

KAI does not record quota reservation, pod readiness, or completion on the PodGroup, so there are no equivalents of the Kueue `quota_reserved`, `running`, and `finished` Workload events.

Events are tagged with `kube_namespace`, `kai_workload` (the PodGroup name), `kai_workload_uid`, `kai_queue`, `kai_nodepool`, `kai_transition`, and `kai_workload_priority_class` when the PodGroup sets a priority class. The `kai_queue` tag matches the tag the Agent adds to the metrics of the PodGroup's pods, and so does `kai_workload` when the Agent collects tags with `orchestrator` cardinality. Pending events take the node pool from the scheduling condition, and other events from the `kai.scheduler/node-pool` PodGroup label, so other events are tagged `kai_nodepool:default` when KAI is configured with another `global.nodePoolLabelKey`. Instance tags, including the tags you set in `tags` and the tags Autodiscovery adds from the KAI pods, apply to metrics only, not to events.

Pending events include the scheduling error and a `kai_pending_reason` tag for each reason KAI reports, such as `OverLimit`. Admitted events include the queued wait time when the check can determine it, counted from the PodGroup creation or from the latest eviction. After an eviction of only some of the pods, it can also include time the PodGroup spent running. Eviction events include the message and the eviction action, and are tagged with `kai_eviction_action` (such as `preempt` or `reclaim`) and `kai_evicted_by` (the preemptor PodGroup), when available from the `Evict` Kubernetes event that KAI records on the PodGroup.

Each event also includes `kai_workload_event_index`, an integer that goes up by one for each event the check emits for a PodGroup. KAI timestamps transitions to the second, so several events can have the same timestamp. To put events in order, sort by timestamp first, then by `kai_workload_event_index` as an integer.

The Agent stores the index in its persistent cache. After a process restart, the sequence picks up where it left off for PodGroups that still exist in the API. The sequence restarts at 0 in two cases:

- The check configuration changes, which clears the cache.
- A new pod starts. The run directory doesn't survive container recreation.

The first collection run records the current state of each PodGroup. It doesn't emit events for transitions that happened before that run.

Collecting events requires `list` role-based access control (RBAC) permission on `podgroups.scheduling.run.ai`, and `list` on `events` for the eviction details. Every instance with `collect_podgroup_events` enabled polls all the PodGroups of the cluster, so when you configure several instances, such as one per scheduling shard, set `collect_podgroup_events: false` on all but one of them. Set it to `false` on every instance to disable events.

### Scheduling goodput (experimental)

Set `collect_scheduling_goodput: true` to submit how much of the GPU time requested by KAI PodGroups was spent waiting to become fully runnable. A GPU PodGroup is one whose pods request `nvidia.com/gpu` or `amd.com/gpu`, or a KAI GPU fraction with the `gpu-fraction` annotation; MIG profiles are not counted. On every run, each GPU PodGroup adds the time since the previous run multiplied by the GPUs requested by its active pods to one of two counts, in GPU-hours, submitted as one series per PodGroup:

- `gpu.scheduling.badput_time`: the PodGroup waits for quota or for room in the cluster, some of its pods are not running yet, or it was preempted and waits to run again. It is tagged with a `reason` shared with the other scheduler integrations, such as `quota_exhausted`, `no_matching_resources` or `preempted`, and with the raw KAI `scheduler_reason` when KAI reports one.
- `gpu.scheduling.fully_admitted_time`: every active pod of the PodGroup runs, with at least `minMember` pods running or completed.

**Requirements**: the service account of the Agent that runs the check, such as the cluster check runner, needs cluster-wide `list` on `podgroups.scheduling.run.ai` and on `pods`, and `get` on `jobs.batch`, which tells whether a PodGroup without pods waits for new ones or is done. Every instance with `collect_scheduling_goodput` enabled counts the whole cluster, so enable it on one instance only.

**Querying**: the scheduling goodput of a group, such as a KAI queue, is `fully_admitted_time / (fully_admitted_time + badput_time)` summed over its series:

```text
sum:gpu.scheduling.fully_admitted_time{*} by {kai_queue}.as_count().fill(zero) / (sum:gpu.scheduling.fully_admitted_time{*} by {kai_queue}.as_count().fill(zero) + sum:gpu.scheduling.badput_time{*} by {kai_queue}.as_count().fill(zero))
```

Use `.fill(zero)` so that a group that stops reporting does not repeat its last value. Each PodGroup submits both metrics on every run where it is counted, the other metric with a value of 0, so that the goodput of a group is defined even when all its PodGroups wait or all run. That 0 `badput_time` point has no `reason` tag, so grouping badput by `reason` shows an extra group without one. A PodGroup name is only unique within a namespace, so group by `kube_namespace` and `kai_workload` to look at a single PodGroup.

**Tags**: both metrics are tagged with `kai_workload`, `kube_scheduler:kai`, `kube_scheduler_queue`, `kai_queue` and `kube_namespace`. Instance tags, including the tags Autodiscovery adds from the scraped pods, are not added, so that they do not collide with the tags of the PodGroup.

**Cost**: each PodGroup active in an hour adds at least two custom metric series, plus one per extra badput reason, so the number of series grows with how many PodGroups are created.

### Service Checks

The KAI Scheduler integration does not include any service checks of its own. The `kai.openmetrics.health` service check, inherited from the OpenMetrics base check, reports whether each endpoint can be scraped.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://github.com/kai-scheduler/KAI-Scheduler
[2]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/kai_scheduler/datadog_checks/kai_scheduler/data/conf.yaml.example
[7]: https://github.com/DataDog/integrations-core/blob/master/kai_scheduler/metadata.csv
[8]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/containers/cluster_agent/clusterchecks/?tab=helm#configuration-from-configuration-files
[11]: https://docs.datadoghq.com/containers/troubleshooting/cluster-and-endpoint-checks/#dispatching-logic-in-the-cluster-agent
[12]: https://docs.datadoghq.com/metrics/distributions/
