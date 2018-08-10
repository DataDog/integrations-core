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

1. Create a read-only login to connect to your server:

    ```
        CREATE LOGIN datadog WITH PASSWORD = 'YOUR_PASSWORD';
        CREATE USER datadog FOR LOGIN datadog;
        GRANT SELECT on sys.dm_os_performance_counters to datadog;
        GRANT VIEW SERVER STATE to datadog;
    ```

2. Create a file `sqlserver.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][13].
    See the [sample sqlserver.d/conf.yaml][2] for all available configuration options:

    ```yaml
        init_config:

        instances:
          - host: <SQL_HOST>,<SQL_PORT>
            username: datadog
            password: <YOUR_PASSWORD>
            connector: odbc # alternative is 'adodbapi'
            driver: SQL Server
    ```

    See the [example check configuration][2] for a comprehensive description of all options, including how to use custom queries to create your own metrics.

    **Note**: The (default) provider `SQLOLEDB` is being deprecated. To use the newer `MSOLEDBSQL` provider, set the `adoprovider` variable to `MSOLEDBSQL` in your `sqlserver.d/conf.yaml` file after having downloaded the new provider from [Microsoft][17].

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

## Development

Please refer to the [main documentation][14] for more details about how to test and develop Agent based integrations.

### Testing Guidelines

#### Windows

To run the tests on Windows, an instance of MSSQL is expected to run on the host. The name of the database instance and the credentials reflect what we have on the CI environment, so that might not work out of the box on a local development environment.

#### Linux

On Linux, a Docker container running a MSSQL instance is automatically started before running the tests. We use unixODBC and [FreeTDS][15] to talk to the database so, depending on the Linux distribution, you need to install additional dependencies on your local dev environment before running the tests. For example these are the installation steps for Ubuntu 14.04:

```
sudo apt-get install unixodbc unixodbc-dev tdsodbc
```

#### OSX

Same as Linux, MSSQL runs in a Docker container and we talk to the database through unixODBC and [FreeTDS][15]. You can use [homebrew][16] to install the required packages:

```
brew install unixodbc
brew install freetds --with-unixodbc
```

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
[12]: https://raw.githubusercontent.com/DataDog/integrations-core/master/sqlserver/images/sqlserver_dashboard.png
[13]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[14]: https://docs.datadoghq.com/developers/integrations/
[15]: http://www.freetds.org/
[16]: https://brew.sh/
[17]: https://docs.microsoft.com/en-us/sql/connect/oledb/oledb-driver-for-sql-server?view=sql-server-2017 
