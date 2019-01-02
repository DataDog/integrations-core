# Prometheus Integration

## Overview

Extract custom metrics from any prometheus endpoints.

<div class="alert alert-warning">
All the metrics retrieved by this integration are considered custom metrics.
</div>

## Setup

### Installation

The Prometheus check is packaged with the Agent starting version 6.1.0.

### Configuration

Edit the `prometheus.d/conf.yaml` file to retrieve metrics from applications that expose OpenMetrics / Prometheus end points.

Each instance is at least composed of:

| Setting          | Description                                                                                                      |
|------------------|------------------------------------------------------------------------------------------------------------------|
| `prometheus_url` | A URL that points to the metric route (**Note:** must be unique)                                                 |
| `namespace`      | This namespace is prepended to all metrics (to avoid metrics name collision)                                     |
| `metrics`        | A list of metrics to retrieve as custom metrics in the form `- <METRIC_NAME>` or `- <METRIC_NAME:RENAME_METRIC>` |

When listing metrics, it's possible to use the wildcard `*` like this `- <METRIC_NAME>*` to retrieve all matching metrics. **Note:** use wildcards with caution as it can potentially send a lot of custom metrics.

More advanced settings (ssl, labels joining, custom tags,...) are documented in the [sample prometheus.d/conf.yaml][2]

Due to the nature of this integration, it's possible to submit a high number of custom metrics to Datadog. To provide users control over the maximum number of metrics sent in the case of configuration errors or input changes, the check has a default limit of 2000 metrics. If needed, this limit can be increased by setting the option `max_returned_metrics` in the `prometheus.d/conf.yaml` file.

### Validation

[Run the Agent's `status` subcommand][1] and look for `prometheus` under the Checks section.

## Data Collected
### Metrics

All metrics collected by the prometheus check are forwarded to Datadog as custom metrics.

### Events
The Prometheus check does not include any events at this time.

### Service Checks

The Prometheus check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog support][3].

## Further Reading

* [Introducing Prometheus support for Datadog Agent 6][4]
* [Configuring a Prometheus Check][5]
* [Writing a custom Prometheus Check][6]

[1]: https://docs.datadoghq.com/agent/faq/agent-status-and-information/
[2]: https://github.com/DataDog/integrations-core/blob/master/prometheus/datadog_checks/prometheus/data/conf.yaml.example
[3]: https://docs.datadoghq.com/help/
[4]: https://www.datadoghq.com/blog/monitor-prometheus-metrics/
[5]: https://docs.datadoghq.com/agent/prometheus/
[6]: https://docs.datadoghq.com/developers/prometheus/
