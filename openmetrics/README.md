# OpenMetrics Integration

## Overview

Extract custom metrics from any OpenMetrics endpoints.

**Note:** All the metrics retrieved by this integration are considered as [custom metrics][1].

## Setup

### Installation

The OpenMetrics check is packaged with the [Datadog Agent starting version 6.6.0][2].

### Configuration

Edit the `openmetrics.d/conf.yaml` file at the root of your [Agent's configuration directory][3] to add the different OpenMetrics instances you want to retrieve metrics from.

Each instance is at least composed of the following parameters:

* `prometheus_url`: Points to the metric route (**Note:** it must be unique)
* `namespace`: Namespace to be prepended to all metrics (allows to avoid metrics name collision)
* `metrics`: A list of metrics that you want to retrieve as custom metrics, for each metric you can either simply add it to the list `- metric_name` or renaming it like `- metric_name: renamed`. It's also possible to use a `*` wildcard such as `- metric*` that fetches all matching metrics (to use with caution as it can potentially send a lot of custom metrics).

There is also a couple of more advanced settings (`ssl`, `labels joining`, `tags`,...) that are documented in the [`conf.yaml` example configuration][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `openmetrics` under the Checks section.

## Data Collected
### Metrics

All metrics collected by the OpenMetrics check are forwarded to Datadog as custom metrics.

### Events

The OpenMetrics check does not include any events.

### Service Checks

The OpenMetrics check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][6].

## Further Reading

* [Configuring a OpenMetrics Check][7]
* [Writing a custom OpenMetrics Check][8]

[1]: https://docs.datadoghq.com/developers/metrics/custom_metrics
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[4]: https://docs.datadoghq.com/agent/openmetrics
[5]: https://docs.datadoghq.com/agent/faq/agent-status-and-information
[6]: https://docs.datadoghq.com/help
[7]: https://docs.datadoghq.com/agent/openmetrics
[8]: https://docs.datadoghq.com/developers/openmetrics
