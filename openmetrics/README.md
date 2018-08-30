# OpenMetrics Integration

## Overview

Extract custom metrics from any openmetrics endpoints.

**Note:** All the metrics retrieved by this integration will be considered as custom metrics.

## Setup

### Installation

The OpenMetrics check is packaged with the Agent starting version 6.5.0.

### Configuration

Edit the `openmetrics.d/conf.yaml` file to add your different openmetrics instances you want to retrieve metrics from.

Each instance is at least composed of:

* a `prometheus_url` that points to the metric route (**Note:** must be unique)
* a `namespace` that will be prepended to all metrics (to avoid metrics name collision)
* a list of `metrics` that you want to retrieve as custom metrics, for each metric you can either simply add it to the list `- metric_name` or renaming it like `- metric_name: renamed`. It's also possible to use a `*` wildcard such as `- metric*` that would fetch all matching metrics (to use with caution as it can potentially send a lot of custom metrics)

There is also a couple of more advanced settings (ssl, labels joining, custom tags,...) that are documented in the [example configuration][2]

If you are monitoring an off-the-shelf software and you think it would deserve an official integration, have a look at `kube_proxy` for an example, and don't hesitate to contribute.

### Validation

[Run the Agent's `status` subcommand][1] and look for `openmetrics` under the Checks section.

## Data Collected
### Metrics

All metrics collected by the openmetrics check are forwared to Datadog as custom metrics.

### Events
The OpenMetrics check does not include any events at this time.

### Service Checks

The OpenMetrics check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][3].

## Further Reading

* [Configuring a OpenMetrics Check][5]
* [Writing a custom OpenMetrics Check][6]

[1]: https://docs.datadoghq.com/agent/faq/agent-status-and-information/
[2]: https://docs.datadoghq.com/agent/openmetrics/
[3]: https://docs.datadoghq.com/help/
[5]: https://docs.datadoghq.com/agent/openmetrics/
[6]: https://docs.datadoghq.com/developers/openmetrics/
