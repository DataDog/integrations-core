<<<<<<< HEAD
<<<<<<< HEAD
# Agent Check: ClickHouse

## Overview

This check monitors [ClickHouse][1] through the Datadog Agent.

**Minimum Agent version:** 7.16.0

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The ClickHouse check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

#### Metric collection

1. To start collecting your ClickHouse performance data, edit the `clickhouse.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory. See the [sample clickhouse.d/conf.yaml][4] for all available configuration options.

*Note*: This integration uses the official `clickhouse-connect` client to connect over HTTP.

2. [Restart the Agent][5].

##### Log collection

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

3. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

#### Metric collection

| Parameter            | Value                                                      |
|----------------------|------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `clickhouse`                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                              |
| `<INSTANCE_CONFIG>`  | `{"server": "%%host%%", "port": "%%port%%", "username": "<USER>", "password": "<PASSWORD>"}`       |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection][6].

| Parameter      | Value                                     |
|----------------|-------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "clickhouse", "service": "<SERVICE_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][7] and look for `clickhouse` under the **Checks** section.
=======
# ClickHouse Integration
=======
# Agent Check: ClickHouse
>>>>>>> 79f01028df (Update clickhouse implementation)

## Overview

This check monitors [ClickHouse][1] through the Datadog Agent.

**Minimum Agent version:** 7.16.0

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The ClickHouse check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

#### Metric collection

1. To start collecting your ClickHouse performance data, edit the `clickhouse.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory. See the [sample clickhouse.d/conf.yaml][4] for all available configuration options.

*Note*: This integration uses the official `clickhouse-connect` client to connect over HTTP.

2. [Restart the Agent][5].

##### Log collection

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

3. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

#### Metric collection

| Parameter            | Value                                                      |
|----------------------|------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `clickhouse`                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                              |
| `<INSTANCE_CONFIG>`  | `{"server": "%%host%%", "port": "%%port%%", "username": "<USER>", "password": "<PASSWORD>"}`       |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection][6].

| Parameter      | Value                                     |
|----------------|-------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "clickhouse", "service": "<SERVICE_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

<<<<<<< HEAD
[Run the Agent's status subcommand](https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information) and look for `clickhouse` under the Checks section.
>>>>>>> 0e81c2cdb5 (Update)
=======
[Run the Agent's status subcommand][7] and look for `clickhouse` under the **Checks** section.
>>>>>>> 79f01028df (Update clickhouse implementation)

## Data Collected

### Metrics

<<<<<<< HEAD
<<<<<<< HEAD
See [metadata.csv][8] for a list of metrics provided by this integration.
=======
The ClickHouse integration collects a wide range of metrics from ClickHouse system tables. See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/clickhouse/metadata.csv) for a list of metrics provided by this integration.

### Database Monitoring

When Database Monitoring is enabled, the integration collects:

- **Query Metrics**: Aggregated query performance metrics from `system.query_log`
- **Query Samples**: Execution plans for currently running queries from `system.processes`
- **Activity Snapshots**: Real-time view of active sessions and connections
>>>>>>> 0e81c2cdb5 (Update)
=======
See [metadata.csv][8] for a list of metrics provided by this integration.
>>>>>>> 79f01028df (Update clickhouse implementation)

### Events

The ClickHouse check does not include any events.

### Service Checks

<<<<<<< HEAD
<<<<<<< HEAD
See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].


[1]: https://clickhouse.yandex
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: /account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/datadog_checks/clickhouse/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/log/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
=======
**clickhouse.can_connect**:
Returns `CRITICAL` if the Agent cannot connect to ClickHouse, otherwise returns `OK`.
=======
See [service_checks.json][9] for a list of service checks provided by this integration.
>>>>>>> 79f01028df (Update clickhouse implementation)

## Troubleshooting

Need help? Contact [Datadog support][10].


<<<<<<< HEAD
>>>>>>> 0e81c2cdb5 (Update)
=======
[1]: https://clickhouse.yandex
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: /account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/datadog_checks/clickhouse/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/log/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
>>>>>>> 79f01028df (Update clickhouse implementation)
