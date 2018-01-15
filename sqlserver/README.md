# Microsoft SQL Server Check
{{< img src="integrations/sql_server/sql_server_graph.png" alt="sql server graph" responsive="true" popup="true">}}
## Overview

This check lets you track the performance of your SQL Server instances. It collects metrics for number of user connections, rate of SQL compilations, and more.

You can also create your own metrics by having the check run custom queries.

## Setup
### Installation

The SQL Server check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your SQL Server instances.  

If you need the newest version of the SQL Server check, install the `dd-check-sqlserver` package; this package's check overrides the one packaged with the Agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.  

Make sure that your SQL Server instance supports SQL Server authentication by enabling "SQL Server and Windows Authentication mode" in the server properties. 
**Server Properties** -> **Security** -> **SQL Server and Windows Authentication mode**

### Configuration

1. Create a read-only user to connect to your server:

```
CREATE LOGIN datadog WITH PASSWORD = 'YOUR_PASSWORD';
CREATE USER datadog FOR LOGIN datadog;
GRANT SELECT on sys.dm_os_performance_counters to datadog;
GRANT VIEW SERVER STATE to datadog;
```

2. Create a file `sqlserver.yaml` in the Agent's `conf.d` directory. See the [sample sqlserver.yaml](https://github.com/DataDog/integrations-core/blob/master/sqlserver/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - host: <SQL_HOST>,<SQL_PORT>
    username: <SQL_ADMIN_USER>
    password: <SQL_ADMIN_PASSWORD>
    connector: odbc # alternative is 'adodbapi'
    driver: SQL Server
```

See the [example check configuration](https://github.com/DataDog/integrations-core/blob/master/sqlserver/conf.yaml.example) for a comprehensive description of all options, including how to use custom queries to create your own metrics.

3. [Restart the Agent](https://docs.datadoghq.com/agent/faq/start-stop-restart-the-datadog-agent) to start sending SQL Server metrics to Datadog.

### Validation

[Run the Agent's `info` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `sqlserver` under the Checks section:

```
  Checks
  ======
    [...]

    sqlserver
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The sqlserver check is compatible with all Windows and Linux platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/sqlserver/metadata.csv) for a list of metrics provided by this check.

Most of these metrics come from your SQL Server's `sys.dm_os_performance_counters` table.

### Events
The SQL server check does not include any event at this time.

### Service Checks

**sqlserver.can_connect**:

Returns CRITICAL if the Agent cannot connect to SQL Server to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitor your Azure SQL Databases with Datadog](https://www.datadoghq.com/blog/monitor-azure-sql-databases-datadog/)