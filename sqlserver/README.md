# Microsoft SQL Server Check

![SQL server Graph][12]

## Overview

This check lets you track the performance of your SQL Server instances. It collects metrics for number of user connections, rate of SQL compilations, and more.

You can also create your own metrics by having the check run custom queries.

## Setup
### Installation

The SQL Server check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your SQL Server instances.

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

2. Create a file `sqlserver.d/conf.yaml`, in the `conf.d/` folder at the root of your Agent's configuration directory.
    See the [sample sqlserver.d/conf.yaml][2] for all available configuration options:

    ```yaml
        init_config:

        instances:
          - host: <SQL_HOST>,<SQL_PORT>
            username: <SQL_ADMIN_USER>
            password: <SQL_ADMIN_PASSWORD>
            connector: odbc # alternative is 'adodbapi'
            driver: SQL Server
    ```

    See the [example check configuration][2] for a comprehensive description of all options, including how to use custom queries to create your own metrics.

    **Note**: The (default) provider `SQLOLEDB` is being deprecated. To use the newer `MSOLEDBSQL` provider, set the `adoprovider` variable to `MSOLEDBSQL` in your `sqlserver.d/conf.yaml` file after having downloaded the new provider from [Microsoft][13].

3. [Restart the Agent][3] to start sending SQL Server metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `sqlserver` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

Most of these metrics come from your SQL Server's `sys.dm_os_performance_counters` table.

### Events
The SQL server check does not include any events at this time.

### Service Checks

**sqlserver.can_connect**:

Returns CRITICAL if the Agent cannot connect to SQL Server to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [Monitor your Azure SQL Databases with Datadog][7]
* [Key metrics for SQL Server monitoring][8]
* [SQL Server monitoring tools][9]
* [Monitor SQL Server performance with Datadog][10]
* [Custom SQL Server metrics for detailed monitoring][11]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/sqlserver/datadog_checks/sqlserver/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/sqlserver/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/monitor-azure-sql-databases-datadog/
[8]: https://www.datadoghq.com/blog/sql-server-monitoring/
[9]: https://www.datadoghq.com/blog/sql-server-monitoring-tools/
[10]: https://www.datadoghq.com/blog/sql-server-performance/
[11]: https://www.datadoghq.com/blog/sql-server-metrics/
[12]: https://raw.githubusercontent.com/DataDog/documentation/master/src/images/integrations/sql_server/sql_server_graph.png
[13]: https://docs.microsoft.com/en-us/sql/connect/oledb/oledb-driver-for-sql-server?view=sql-server-2017 
