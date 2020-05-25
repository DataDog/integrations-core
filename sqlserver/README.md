# Microsoft SQL Server Check

![SQL server Graph][1]

## Overview

This check lets you track the performance of your SQL Server instances. It collects metrics for number of user connections, rate of SQL compilations, and more.

You can also create your own metrics by having the check run custom queries.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The SQL Server check is included in the [Datadog Agent][3] package, so you don't need to install anything else on your SQL Server instances.

Make sure that your SQL Server instance supports SQL Server authentication by enabling "SQL Server and Windows Authentication mode" in the server properties.
**Server Properties** -> **Security** -> **SQL Server and Windows Authentication mode**

### Configuration

1. Create a read-only login to connect to your server:

   ```text
       CREATE LOGIN datadog WITH PASSWORD = '<PASSWORD>';
       CREATE USER datadog FOR LOGIN datadog;
       GRANT SELECT on sys.dm_os_performance_counters to datadog;
       GRANT VIEW SERVER STATE to datadog;
   ```

2. Create a file `sqlserver.d/conf.yaml`, in the `conf.d/` folder at the root of your [Agent's configuration directory][4].
   See the [sample sqlserver.d/conf.yaml][5] for all available configuration options:

   ```yaml
   init_config:

   instances:
     - host: "<SQL_HOST>,<SQL_PORT>"
       username: datadog
       password: "<YOUR_PASSWORD>"
       connector: odbc # alternative is 'adodbapi'
       driver: SQL Server
   ```

    See the [example check configuration][5] for a comprehensive description of all options, including how to use custom queries to create your own metrics.

    **Note**: The (default) provider `SQLOLEDB` is being deprecated. To use the newer `MSOLEDBSQL` provider, set the `adoprovider` variable to `MSOLEDBSQL` in your `sqlserver.d/conf.yaml` file after having downloaded the new provider from [Microsoft][6]. It is also possible to use the Windows Authentication and not specify the username/password with:

      ```yaml
      connection_string: "Trusted_Connection=yes"
      ```

3. [Restart the Agent][7] to start sending SQL Server metrics to Datadog.

#### Linux

Extra configuration steps are required to get the SQL Server integration running on a Linux host:

1. Install an ODBC SQL Server Driver, for example the [Microsoft ODBC Driver][8].
2. Copy the `odbc.ini` and `odbcinst.ini` files into the `/opt/datadog-agent/embedded/etc` folder.
3. Configure the `conf.yaml` file to use the `odbc` connector and specify the proper driver as specified in the `odbcinst.ini file`.

### Validation

[Run the Agent's `status` subcommand][9] and look for `sqlserver` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this check.

Most of these metrics come from your SQL Server's `sys.dm_os_performance_counters` table.

### Events

The SQL server check does not include any events.

### Service Checks

**sqlserver.can_connect**:

Returns CRITICAL if the Agent cannot connect to SQL Server to collect metrics, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog support][11].

## Development

See the [main documentation][12] for more details about how to test and develop Agent based integrations.

### Testing Guidelines

#### Windows

To run the tests on Windows, an instance of MSSQL is expected to run on the host. The name of the database instance and the credentials reflect what we have on the CI environment, so that might not work out of the box on a local development environment.

#### Linux

On Linux, a Docker container running a MSSQL instance is automatically started before running the tests. We use unixODBC and [FreeTDS][13] to talk to the database so, depending on the Linux distribution, you need to install additional dependencies on your local dev environment before running the tests. For example these are the installation steps for Ubuntu 14.04:

```shell
sudo apt-get install unixodbc unixodbc-dev tdsodbc
```

#### OSX

Same as Linux, MSSQL runs in a Docker container and we talk to the database through unixODBC and [FreeTDS][13]. You can use [homebrew][14] to install the required packages:

```shell
brew install unixodbc freetds
```

## Further Reading

- [Monitor your Azure SQL Databases with Datadog][15]
- [Key metrics for SQL Server monitoring][16]
- [SQL Server monitoring tools][17]
- [Monitor SQL Server performance with Datadog][18]
- [Custom SQL Server metrics for detailed monitoring][19]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/sqlserver/images/sqlserver_dashboard.png
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/sqlserver/datadog_checks/sqlserver/data/conf.yaml.example
[6]: https://docs.microsoft.com/en-us/sql/connect/oledb/oledb-driver-for-sql-server?view=sql-server-2017
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-2017
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/sqlserver/metadata.csv
[11]: https://docs.datadoghq.com/help/
[12]: https://docs.datadoghq.com/developers/integrations/
[13]: http://www.freetds.org
[14]: https://brew.sh
[15]: https://www.datadoghq.com/blog/monitor-azure-sql-databases-datadog
[16]: https://www.datadoghq.com/blog/sql-server-monitoring
[17]: https://www.datadoghq.com/blog/sql-server-monitoring-tools
[18]: https://www.datadoghq.com/blog/sql-server-performance
[19]: https://www.datadoghq.com/blog/sql-server-metrics
