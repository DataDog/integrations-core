# OpenMetrics Integration

## Overview

Extract custom metrics from any OpenMetrics endpoints.

<div class="alert alert-warning">All the metrics retrieved by this integration are considered <a href="https://docs.datadoghq.com/developers/metrics/custom_metrics">custom metrics</a>.</div>

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these instructions.

### Installation

The OpenMetrics check is packaged with the [Datadog Agent starting version 6.6.0][2].

### Configuration

Edit the `openmetrics.d/conf.yaml` file at the root of your [Agent's configuration directory][3]. See the [sample openmetrics.d/conf.yaml][4] for all available configuration options.

For each instance the following parameters are required:

| Parameter        | Description                                                                                                                                                                                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `openmetrics_endpoint` | The URL where your application metrics are exposed by Prometheus (must be unique).                                                                                                                         |
| `namespace`      | The namespace to prepend to all metrics.                                                                                                                                                                                                                                 |
| `metrics`        | A list of metrics to retrieve as custom metrics. Add each metric to the list as `metric_name` or `metric_name: renamed` to rename it. The metrics are interpreted as regular expressions. Use `.*` as a wildcard (`metric.*`) to fetch all matching metrics. **Note**: Regular expressions can potentially send a lot of custom metrics. |

**Note**: This is a new default OpenMetrics check example. If you previously implemented this integration, see the [legacy example][5].

**Note**: This check has a limit of 2000 metrics per instance. The number of returned metrics is indicated when running the Datadog Agent [status command][6]. You can specify the metrics you are interested in by editing the configuration. To learn how to customize the metrics to collect, visit the [Prometheus and OpenMetrics Metrics Collection][7] for more detailed instructions. If you need to monitor more metrics, contact [Datadog support][8].

For more configurations, see [Prometheus and OpenMetrics Metrics Collection][7].

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

### High custom metrics billing

OpenMetrics configurations with generic wildcard values for the `metrics` option have significant impact on custom metrics billing.

Datadog recommends that you use specific metric names or partial metric name matches for more precise collection.

Need help? Contact [Datadog support][8].

## Further Reading

- [Configuring a OpenMetrics Check][9]
- [Writing a custom OpenMetrics Check][10]

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[2]: https://docs.datadoghq.com/getting_started/integrations/prometheus/?tab=docker#configuration
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/openmetrics/datadog_checks/openmetrics/data/conf.yaml.example
[5]: https://github.com/DataDog/integrations-core/blob/7.30.x/openmetrics/datadog_checks/openmetrics/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://docs.datadoghq.com/getting_started/integrations/prometheus/
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/agent/openmetrics/
[10]: https://docs.datadoghq.com/developers/openmetrics/
