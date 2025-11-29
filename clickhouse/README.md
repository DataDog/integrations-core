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

## Data Collected

### Metrics

The ClickHouse integration collects a wide range of metrics from ClickHouse system tables. See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/clickhouse/metadata.csv) for a list of metrics provided by this integration.

### Database Monitoring

When Database Monitoring is enabled, the integration collects:

- **Query Metrics**: Aggregated query performance metrics from `system.query_log`
- **Query Samples**: Execution plans for currently running queries from `system.processes`
- **Activity Snapshots**: Real-time view of active sessions and connections

### Events

The ClickHouse check does not include any events.

### Service Checks

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

