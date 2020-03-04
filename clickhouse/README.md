# Agent Check: ClickHouse

## Overview

This check monitors [ClickHouse][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The ClickHouse check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

1. To start collecting your ClickHouse performance data, edit the `clickhouse.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory. See the [sample clickhouse.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `clickhouse` under the **Checks** section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

**clickhouse.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to the monitored ClickHouse database. Otherwise, returns `OK`.

### Events

The ClickHouse check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://clickhouse.yandex
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://docs.datadoghq.com/agent/
[4]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/datadog_checks/clickhouse/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/metadata.csv
[8]: https://docs.datadoghq.com/help
