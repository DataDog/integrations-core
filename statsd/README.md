# Agent Check: StatsD

## Overview

This check monitors the availability and uptime of non-Datadog StatsD servers. It also tracks the number of metrics, by metric type, received by StatsD.

This check does **NOT** forward application metrics from StatsD servers to Datadog. It collects metrics about StatsD itself.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][10] for guidance on applying these instructions.

### Installation

The StatsD check is included in the [Datadog Agent][1] package, so you don't need to install anything else on any servers that run StatsD.

### Configuration

1. Edit the `statsd.d/conf.yaml` in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample statsd.d/conf.yaml][3] for all available configuration options:

    ```yaml
        init_config:

        instances:
            - host: localhost
            port: 8126 # or wherever your statsd listens
    ```

    Configuration Options

    - `host` (Optional) - Host to be checked. This will be included as a tag: `host:<host>`. Defaults to `localhost`.
    - `port` (Optional) - Port to be checked. This will be included as a tag: `port:<port>`. Defaults to `8126`.
    - `timeout` (Optional) - Timeout for the check. Defaults to 10 seconds.
    - `tags` (Optional) - Tags to be assigned to the metric.

2. [Restart the Agent][4] to start sending StatsD metrics and service checks to Datadog.

### Validation

[Run the Agent's `status` subcommand][5] and look for `statsd` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][6] for a list of metrics provided by this integration.

### Events
The StatsD check does not include any events.

### Service Checks

**statsd.is_up**:

Returns CRITICAL if the StatsD server does not respond to the Agent's health status request, otherwise OK.

**statsd.can_connect**:

Returns CRITICAL if the Agent cannot collect metrics about StatsD, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog support][7].

## Further Reading
If you don't know what StatsD is and how does it work, check out [our blog post about it][8]

To get a better idea of how (or why) to visualize StatsD metrics with Counts Graphing with Datadog, check out our [series of blog posts][9] about it.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/statsd/datadog_checks/statsd/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/statsd/metadata.csv
[7]: https://docs.datadoghq.com/help
[8]: https://www.datadoghq.com/blog/statsd
[9]: https://www.datadoghq.com/blog/visualize-statsd-metrics-counts-graphing
[10]: https://docs.datadoghq.com/agent/autodiscovery/integrations
