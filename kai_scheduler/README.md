# Agent Check: KAI Scheduler

## Overview

This check monitors [KAI Scheduler][1] through the Datadog Agent.

KAI Scheduler is a Kubernetes scheduler for AI and GPU workloads. It schedules pods into hierarchical queues with quotas, fair share, priorities, and preemption. This integration collects metrics from the KAI scheduler and queue-controller to help you monitor queue quotas and allocation, fair share, scheduling latency, and preemption.

## Setup

### Installation

The KAI Scheduler check is included in the [Datadog Agent][2] package.
No additional installation is required on your server.

### Configuration

KAI Scheduler exposes its metrics from two deployments in the `kai-scheduler` namespace. Each one serves Prometheus metrics over plain HTTP on port `8080`:

- The scheduler, through the `kai-scheduler-<shard>` service (`kai-scheduler-default` for the default shard), serves scheduling cycle, action, preemption, and queue fair share metrics.
- The queue-controller, through the `queue-controller` service, serves queue quota and allocation metrics.

A single instance scrapes any combination of these endpoints. Each metric is tagged with `kai_component` (`scheduler` or `queue_controller`) so that the generic metrics of each component can be told apart.

KAI Scheduler is a cluster-level service. Configure this integration as a Cluster Agent [cluster check][10] so only one Agent instance scrapes the endpoints. For file or ConfigMap based configuration, set `cluster_check: true` in the instance:

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

Queue metrics from the scheduler and the queue-controller share the `kai_queue` tag, which holds the Queue's `metadata.name`, so that quota, allocation, fair share, and usage can be compared per queue. Queues with a `spec.displayName` are also tagged with `kai_queue_display_name`. Tags without a value, such as labels that KAI leaves empty, are not submitted. Memory metrics are reported in bytes, CPU metrics in cores, and GPU metrics in devices.

KAI counts evicted pods per pod group and never deletes those series. To keep the number of contexts bounded, `kai.evicted_pods.count` reports the pods evicted since the previous check run, summed by `kube_namespace`, `kai_nodepool`, and `action`. Evictions that happened before the first successful check run are not reported. The check keeps the previous value of up to 10,000 pod group series. Beyond that, it reports the increase of the summed counters instead, which undercounts evictions in a group whose pod group series KAI removed during that check run. To see which workloads were evicted and by which preemptor, collect the Kubernetes `Evict` events that KAI records on each evicted PodGroup.

The `kai.scheduling_cycle.latency.milliseconds`, `kai.session.*.latency.milliseconds`, `kai.action.latency.milliseconds`, and `kai.plugin.latency.milliseconds` gauges hold the duration of the most recent scheduling cycle only. The scheduler runs a cycle every second by default, so each check run samples one cycle and short spikes between check runs are not visible. A scheduler that is consistently slow is still visible in every sample.

### Events

The KAI Scheduler integration does not include any events.

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
