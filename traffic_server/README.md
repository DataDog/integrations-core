# Agent Check: Traffic Server

## Overview

This check monitors [Traffic Server][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Traffic Server check is included in the [Datadog Agent][2] package.

To enable monitoring in Traffic Server, enable the [Stats Over HTTP plugin][10] on your Traffic Server by adding the following line to your `plugin.config` file:

```
stats_over_http.so
```

### Configuration

1. Edit the `traffic_server.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Traffic Server performance data. See the [sample traffic_server.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `traffic_server` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The Traffic Server integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://trafficserver.apache.org/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/traffic_server/datadog_checks/traffic_server/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/traffic_server/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/traffic_server/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.trafficserver.apache.org/en/latest/admin-guide/monitoring/statistics/accessing.en.html#stats-over-http
