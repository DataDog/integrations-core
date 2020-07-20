# Prometheus Integration

## Overview

Extract custom metrics from any Prometheus endpoints. **Note**: Datadog recommends using the [OpenMetrics check][10] since it is more efficient and fully supports Prometheus text format. Use the Prometheus check only when the metrics endpoint does not support a text format.

<div class="alert alert-warning">
All the metrics retrieved by this integration are considered <a href="https://docs.datadoghq.com/developers/metrics/custom_metrics">custom metrics</a>.
</div>

**See the [Prometheus metrics collection Getting Started][8] to learn how to configure a Prometheus Check.**

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][9] for guidance on applying these instructions.

### Installation

The Prometheus check is packaged with the Agent starting version 6.1.0.

### Configuration

Edit the `prometheus.d/conf.yaml` file to retrieve metrics from applications that expose OpenMetrics / Prometheus end points.

Each instance is at least composed of:

| Setting          | Description                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------- |
| `prometheus_url` | A URL that points to the metric route (**Note:** must be unique)                                                    |
| `namespace`      | This namespace is prepended to all metrics (to avoid metrics name collision)                                        |
| `metrics`        | A list of metrics to retrieve as custom metrics in the form `- <METRIC_NAME>` or `- <METRIC_NAME>: <RENAME_METRIC>` |

When listing metrics, it's possible to use the wildcard `*` like this `- <METRIC_NAME>*` to retrieve all matching metrics. **Note:** use wildcards with caution as it can potentially send a lot of custom metrics.

More advanced settings (ssl, labels joining, custom tags,...) are documented in the [sample prometheus.d/conf.yaml][2]

Due to the nature of this integration, it's possible to submit a high number of custom metrics to Datadog. To provide users control over the maximum number of metrics sent in the case of configuration errors or input changes, the check has a default limit of 2000 metrics. If needed, this limit can be increased by setting the option `max_returned_metrics` in the `prometheus.d/conf.yaml` file.

If `send_monotonic_counter: True`, the Agent sends the deltas of the values in question, and the in-app type is set to count (this is the default behaviour). If `send_monotonic_counter: False`, the Agent sends the raw, monotonically increasing value, and the in-app type is set to gauge.

### Validation

[Run the Agent's `status` subcommand][3] and look for `prometheus` under the Checks section.

## Data Collected

### Metrics

All metrics collected by the prometheus check are forwarded to Datadog as custom metrics.

Note: Bucket data for a given `<HISTOGRAM_METRIC_NAME>` Prometheus histogram metric are stored in the `<HISTOGRAM_METRIC_NAME>.count` metric within Datadog with the tags `upper_bound` including the name of the buckets. To access the `+Inf` bucket, use `upper_bound:none`.

### Events

The Prometheus check does not include any events.

### Service Checks

The Prometheus check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][4].

## Further Reading

- [Introducing Prometheus support for Datadog Agent 6][5]
- [Configuring a Prometheus Check][6]
- [Writing a custom Prometheus Check][7]

[2]: https://github.com/DataDog/integrations-core/blob/master/prometheus/datadog_checks/prometheus/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[4]: https://docs.datadoghq.com/help/
[5]: https://www.datadoghq.com/blog/monitor-prometheus-metrics
[6]: https://docs.datadoghq.com/agent/prometheus/
[7]: https://docs.datadoghq.com/developers/prometheus/
[8]: https://docs.datadoghq.com/getting_started/integrations/prometheus/
[9]: https://docs.datadoghq.com/getting_started/integrations/prometheus?tab=docker#configuration
[10]: https://docs.datadoghq.com/integrations/openmetrics/
