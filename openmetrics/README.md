# OpenMetrics Integration

## Overview

Extract custom metrics from any OpenMetrics endpoints.

<div class="alert alert-warning">All the metrics retrieved by this integration are considered <a href="https://docs.datadoghq.com/developers/metrics/custom_metrics">custom metrics</a>.</div>

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The OpenMetrics check is packaged with the [Datadog Agent starting version 6.6.0][3].

### Configuration

Edit the `openmetrics.d/conf.yaml` file at the root of your [Agent's configuration directory][4]. See the [sample openmetrics.d/conf.yaml][5] for all available configuration options.

For each instance the following parameters are required:

| Parameter        | Description                                                                                                                                                                                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `prometheus_url` | The URL where your application metrics are exposed by Prometheus (must be unique).                                                                                                                                                                                       |
| `namespace`      | The namespace to prepend to all metrics.                                                                                                                                                                                                                                 |
| `metrics`        | A list of metrics to retrieve as custom metrics. Add each metric to the list as `metric_name` or `metric_name: renamed` to rename it. Use `*` as a wildcard (`metric*`) to fetch all matching metrics. **Note**: Wildcards can potentially send a lot of custom metrics. |

For more configurations, see [Prometheus and OpenMetrics Metrics Collection][10].

### Validation

[Run the Agent's status subcommand][6] and look for `openmetrics` under the Checks section.

## Data Collected

### Metrics

All metrics collected by the OpenMetrics check are forwarded to Datadog as custom metrics.

### Events

The OpenMetrics check does not include any events.

### Service Checks

The OpenMetrics check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7].

## Further Reading

- [Configuring a OpenMetrics Check][8]
- [Writing a custom OpenMetrics Check][9]

[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://docs.datadoghq.com/getting_started/integrations/prometheus/?tab=docker#configuration
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/openmetrics/datadog_checks/openmetrics/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.datadoghq.com/agent/openmetrics/
[9]: https://docs.datadoghq.com/developers/openmetrics/
[10]: https://docs.datadoghq.com/getting_started/integrations/prometheus/
