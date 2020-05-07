# Agent Check: ClickHouse

## Overview

This check monitors [ClickHouse][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The ClickHouse check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

#### Host
1. To start collecting your ClickHouse performance data, edit the `clickhouse.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory. See the [sample clickhouse.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

##### Log Collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add the log files you are interested in to your `clickhouse.d/conf.yaml` file to start collecting your ClickHouse logs:

   ```yaml
     logs:
       - type: file
         path: /var/log/clickhouse-server/clickhouse-server.log
         source: clickhouse
         service: "<SERVICE_NAME>"
   ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample clickhouse.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][6].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

#### Metric Collection

| Parameter            | Value                                                      |
|----------------------|------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `clickhouse`                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                              |
| `<INSTANCE_CONFIG>`  | `{"server": "%%host%%", "port": "%%port%%", "username": "<USER>", "password": "<PASSWORD>"}`       |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][9].

| Parameter      | Value                                     |
|----------------|-------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "clickhouse", "service": "<SERVICE_NAME>"}` |

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
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://docs.datadoghq.com/agent/
[4]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/datadog_checks/clickhouse/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/metadata.csv
[8]: https://docs.datadoghq.com/help/
