# Prometheus Integration

## Overview

Connect to Prometheus to:
- Extract custom metrics from Prometheus endpoints
- See Prometheus Alertmanager alerts in your Datadog event stream

**Note**: Datadog recommends using the [OpenMetrics check][1] since it is more efficient and fully supports Prometheus text format. Use the Prometheus check only when the metrics endpoint does not support a text format.

<div class="alert alert-warning">
All the metrics retrieved by this integration are considered <a href="https://docs.datadoghq.com/developers/metrics/custom_metrics">custom metrics</a>.
</div>

**See the [Prometheus metrics collection Getting Started][2] to learn how to configure a Prometheus Check.**

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Prometheus check is packaged with the [Datadog Agent][4] starting version 6.1.0.

### Configuration

Edit the `prometheus.d/conf.yaml` file to retrieve metrics from applications that expose OpenMetrics / Prometheus end points.

Each instance is at least composed of:

| Setting          | Description                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------- |
| `prometheus_url` | A URL that points to the metric route (**Note:** must be unique)                                                    |
| `namespace`      | This namespace is prepended to all metrics (to avoid metrics name collision)                                        |
| `metrics`        | A list of metrics to retrieve as custom metrics in the form `- <METRIC_NAME>` or `- <METRIC_NAME>: <RENAME_METRIC>` |

When listing metrics, it's possible to use the wildcard `*` like this `- <METRIC_NAME>*` to retrieve all matching metrics. **Note:** use wildcards with caution as it can potentially send a lot of custom metrics.

More advanced settings (ssl, labels joining, custom tags,...) are documented in the [sample prometheus.d/conf.yaml][5]

Due to the nature of this integration, it's possible to submit a high number of custom metrics to Datadog. Users can control the maximum number of metrics sent for configuration errors or input changes. The check has a default limit of 2000 metrics. If needed, this limit can be increased by setting the option `max_returned_metrics` in the `prometheus.d/conf.yaml` file.

If `send_monotonic_counter: True`, the Agent sends the deltas of the values in question, and the in-app type is set to count (this is the default behavior). If `send_monotonic_counter: False`, the Agent sends the raw, monotonically increasing value, and the in-app type is set to gauge.

### Validation

[Run the Agent's `status` subcommand][6] and look for `prometheus` under the Checks section.

## Data Collected

### Metrics

All metrics collected by the prometheus check are forwarded to Datadog as custom metrics.

Note: Bucket data for a given `<HISTOGRAM_METRIC_NAME>` Prometheus histogram metric are stored in the `<HISTOGRAM_METRIC_NAME>.count` metric within Datadog with the tags `upper_bound` including the name of the buckets. To access the `+Inf` bucket, use `upper_bound:none`.

### Events

Prometheus Alertmanager alerts are automatically sent to your Datadog event stream following the webhook configuration.

### Service Checks

The Prometheus check does not include any service checks.

## Prometheus Alertmanager
Send Prometheus Alertmanager alerts in the event stream. Natively, Alertmanager sends all alerts simultaneously to the configured webhook. To see alerts in Datadog, you must configure your instance of Alertmanager to send alerts one at a time. You can add a group-by parameter under `route` to have alerts grouped by the actual name of the alert rule.

### Setup
1. Edit the Alertmanager configuration file, `alertmanager.yml`, to include the following:
```
receivers:
- name: datadog
  webhook_configs: 
  - send_resolved: true
    url: https://app.datadoghq.com/intake/webhook/prometheus?api_key=<DATADOG_API_KEY>
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 5m
  receiver: datadog
  repeat_interval: 3h
```

**Note**: This endpoint accepts only one event in the payload at a time.

2. Restart the Prometheus and Alertmanager services.
```
sudo systemctl restart prometheus.service alertmanager.service
```

## Troubleshooting

Need help? Contact [Datadog support][7].

## Further Reading

- [Introducing Prometheus support for Datadog Agent 6][8]
- [Configuring a Prometheus Check][9]
- [Writing a custom Prometheus Check][10]

[1]: https://docs.datadoghq.com/integrations/openmetrics/
[2]: https://docs.datadoghq.com/getting_started/integrations/prometheus/
[3]: https://docs.datadoghq.com/getting_started/integrations/prometheus?tab=docker#configuration
[4]: https://app.datadoghq.com/account/settings/agent/latest
[5]: https://github.com/DataDog/integrations-core/blob/master/prometheus/datadog_checks/prometheus/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/help/
[8]: https://www.datadoghq.com/blog/monitor-prometheus-metrics
[9]: https://docs.datadoghq.com/agent/prometheus/
[10]: https://docs.datadoghq.com/developers/prometheus/
