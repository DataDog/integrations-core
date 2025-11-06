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

## Overview

The ClickHouse integration provides health and performance metrics for your ClickHouse database in near real-time. Visualize these metrics with the provided dashboard and create monitors to alert your team on ClickHouse states.

Enable Database Monitoring (DBM) for enhanced insights into query performance and database health. In addition to the standard integration, Datadog DBM provides query-level metrics, live and historical query snapshots, and query explain plans.

**Minimum Agent version:** 7.50.0

## Setup

### Installation

The ClickHouse check is packaged with the Agent. To start gathering your ClickHouse metrics and logs, [install the Agent](https://docs.datadoghq.com/agent/).

### Configuration

#### Prepare ClickHouse

To get started with the ClickHouse integration, create a `datadog` user with proper access to your ClickHouse server.

```sql
CREATE USER datadog IDENTIFIED BY '<PASSWORD>';
GRANT SELECT ON system.* TO datadog;
GRANT SELECT ON information_schema.* TO datadog;
GRANT SHOW DATABASES ON *.* TO datadog;
GRANT SHOW TABLES ON *.* TO datadog;
GRANT SHOW COLUMNS ON *.* TO datadog;
```

#### Configure the Agent

Edit the `clickhouse.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your ClickHouse performance data. See the [sample clickhouse.d/conf.yaml](https://github.com/DataDog/integrations-core/blob/master/clickhouse/datadog_checks/clickhouse/data/conf.yaml.example) for all available configuration options.

```yaml
init_config:

instances:
  - server: localhost
    port: 8123
    username: datadog
    password: <PASSWORD>

    # Enable Database Monitoring
    dbm: true

    # Query Metrics Configuration
    query_metrics:
      enabled: true
      collection_interval: 60

    # Query Samples Configuration
    query_samples:
      enabled: true
      collection_interval: 10

      # Activity snapshot configuration
      activity_enabled: true
      activity_collection_interval: 10
      activity_max_rows: 1000
```

#### Enable query_log

For Database Monitoring features, you need to enable ClickHouse's `query_log`. Add this to your ClickHouse server configuration:

```xml
<clickhouse>
    <query_log>
        <database>system</database>
        <table>query_log</table>
        <flush_interval_milliseconds>7500</flush_interval_milliseconds>
    </query_log>
</clickhouse>
```

[Restart the Agent](https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent) to start sending ClickHouse metrics to Datadog.

### Validation

[Run the Agent's status subcommand](https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information) and look for `clickhouse` under the Checks section.
>>>>>>> 0e81c2cdb5 (Update)

## Data Collected

### Metrics

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

### Events

The ClickHouse check does not include any events.

### Service Checks

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

## Troubleshooting

### Connection Issues

If you encounter connection errors:

1. Verify ClickHouse is running and accessible on the configured host and port
2. Use port `8123` (HTTP interface) for the agent connection
3. Ensure the `datadog` user has the required permissions
4. Check firewall rules allow connections from the Agent

### Database Monitoring Not Collecting Data

If DBM features are not working:

1. Verify `dbm: true` is set in the configuration
2. Ensure `query_log` is enabled in ClickHouse server configuration
3. Check that the `datadog` user has SELECT permissions on `system.query_log` and `system.processes`
4. Review Agent logs for any errors

For more troubleshooting help, contact [Datadog support](https://docs.datadoghq.com/help/).

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor ClickHouse with Datadog](https://www.datadoghq.com/blog/monitor-clickhouse/)
- [Database Monitoring](https://docs.datadoghq.com/database_monitoring/)

>>>>>>> 0e81c2cdb5 (Update)
