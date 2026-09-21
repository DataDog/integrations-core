# Agent Check: ClickHouse

## Overview

This check monitors [ClickHouse][1] through the Datadog Agent.

Enable [Database Monitoring][11] (DBM) for enhanced insights into query performance and database health. In addition to the standard integration, Datadog DBM provides query-level metrics, live and historical query snapshots, query explain plans, query errors, and parts and merges observability.

**Note**: Database Monitoring for ClickHouse is in Preview and requires Datadog Agent v7.78 or later. Customers who participate in the preview will not be charged for usage incurred during the preview period.

**Minimum Agent version:** 7.16.0

## Setup

<div class="alert alert-info">This page describes the standard ClickHouse Agent integration. If you are looking for the Database Monitoring product for ClickHouse, see <a href="https://docs.datadoghq.com/database_monitoring/setup_clickhouse/" target="_blank">Database Monitoring for ClickHouse</a>.</div>

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The ClickHouse check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

#### Prepare ClickHouse

As a best practice, Datadog recommends using a read-only user to monitor your ClickHouse instance. This limits the access granted to the Datadog Agent.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

#### Metric collection

1. To start collecting your ClickHouse performance data, edit the `clickhouse.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory. See the [sample clickhouse.d/conf.yaml][4] for all available configuration options.

*Note*: This integration uses the official `clickhouse-connect` client to connect over HTTP.

*Note*: If your ClickHouse Cloud service sits behind a single load-balanced endpoint, set `single_endpoint_mode: true`. This tells the Agent (version 7.83.0 or later) to query system-table metrics across all nodes behind that endpoint using `clusterAllReplicas()`, tagging each resulting series with `clickhouse_node` so you can still distinguish per-node data.

Without this setting, the Agent may hit a different node on each collection cycle. For cumulative per-node counters like `clickhouse.query.failed.count`, that inconsistency produces inaccurate values, since the counter isn't being read from the same source each time.

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

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events

The ClickHouse check does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].


[1]: https://clickhouse.com/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: /account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/datadog_checks/clickhouse/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/kubernetes/log/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/clickhouse/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
[11]: https://docs.datadoghq.com/database_monitoring/setup_clickhouse/
