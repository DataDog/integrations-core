# PostgreSQL Integration

![PostgreSQL Graph][24]

## Overview

Get metrics from PostgreSQL service in real time to:

* Visualize and monitor PostgreSQL states
* Be notified about PostgreSQL failovers and events.

## Setup

### Installation

The PostgreSQL check is packaged with the Agent. To start gathering your PostgreSQL metrics and logs, [install the Agent][13].

### Configuration

Edit the `postgres.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][25] to start collecting your PostgreSQL [metrics](#metric-collection) and [logs](#log-collection). See the [sample postgres.d/conf.yaml][14] for all available configuration options.

#### Prepare Postgres

To get started with the PostgreSQL integration, create at least a read-only Datadog user with proper access to your PostgreSQL server. Start psql on your PostgreSQL database and run:

For PostgreSQL version 10 and above:
```
create user datadog with password '<PASSWORD>';
grant pg_monitor to datadog;
```

For older PostgreSQL versions:
```
create user datadog with password '<PASSWORD>';
grant SELECT ON pg_stat_database to datadog;
```

**Note**: When generating custom metrics that require querying additional tables, you may need to grant the `CONNECT` permission on those tables to the datadog user.

To verify the correct permissions run the following command:

```
psql -h localhost -U datadog postgres -c \
"select * from pg_stat_database LIMIT(1);" \
&& echo -e "\e[0;32mPostgres connection - OK\e[0m" \
|| echo -e "\e[0;31mCannot connect to Postgres\e[0m"
```

When it prompts for a password, enter the one used in the first command.

#### Metric Collection

* Edit the `postgres.d/conf.yaml` file to point to your server and port, set the masters to monitor. See the [sample postgres.d/conf.yaml][14] for all available configuration options. Configuration Options:

  * **`username`** (Optional) - The user account used to collect metrics, set in the [Installation section above](#installation)
  * **`password`** (Optional) - The password for the user account.
  * **`dbname`** (Optional) - The name of the database you want to monitor.
  * **`ssl`** (Optional) - Defaults to False. Indicates whether to use an SSL connection.
  * **`use_psycopg2`** (Optional) - Defaults to False. Setting this option to `True` will force the Datadog Agent to collect PostgreSQL metrics using psycopg2 instead of pg8000. Note that pyscopg2 does not support SSL connections.
  * **`tags`** (Optional) - A list of tags applied to all metrics collected. Tags may be simple strings or key-value pairs.
  * **`relations`** (Optional) - By default, all schemas are included. Add specific schemas here to collect metrics for schema relations. Each relation will generate 10 metrics and an additional 10 metrics per index. Use the following structure to declare relations:

    ```
    relations:
      - relation_name: my_relation
        schemas:
          - my_schema_1
          - my_schema_2
    ```

  * **`collect_function_metrics`** (Optional) - Collect metrics regarding PL/pgSQL functions from pg_stat_user_functions
  * **`collect_count_metrics`** (Optional) - Collect count metrics. The default value is `True` for backward compatibility, but this might be slow. The recommended value is `False`.
  * **`collect_activity_metrics`** (Optional) - Collect metrics regarding transactions from pg_stat_activity, default value is `False`. Please make sure the user has sufficient privileges to read from pg_stat_activity before enabling this option.
  
    For PostgreSQL versions 9.6 and below, run the following and create a `SECURITY DEFINER` to read from pg_stat_activity.
     ```
    CREATE FUNCTION pg_stat_activity() RETURNS SETOF pg_catalog.pg_stat_activity AS 
    $$ SELECT * from pg_catalog.pg_stat_activity; $$
    LANGUAGE sql VOLATILE SECURITY DEFINER;
  
    CREATE VIEW pg_stat_activity_dd AS SELECT * FROM pg_stat_activity();
    grant SELECT ON pg_stat_activity_dd to datadog;
    ```
  * **`collect_database_size_metrics`** Collect database size metrics. Default value is True but they might be slow with large databases.
  * **`collect_default_database`** (Optional) Include statistics from the default database 'postgres' in the check metrics, default to `False`.
* [Restart the Agent][15] to start sending PostgreSQL metrics to Datadog.

#### Log Collection

PostgreSQL default logging is to stderr and logs do not include detailed information. This is why we suggest to log into a file with additional details specified in the log line prefix.

* Edit your PostgreSQL configuration file `/etc/postgresql/<version>/main/postgresql.conf` and uncomment the following parameter in the log section:

  ```
  logging_collector = on
  log_directory = 'pg_log'  # directory where log files are written,
                            # can be absolute or relative to PGDATA
  log_filename = 'pg.log'   #log file name, can include pattern
  log_statement = 'all'     #log all queries
  log_line_prefix= '%m [%p] %d %a %u %h %c '
  log_file_mode = 0644
  ## For Windows
  #log_destination = 'eventlog'
  ```

* Collecting logs is disabled by default in the Datadog Agent, you need to enable it in datadog.yaml:

  ```
  logs_enabled: true
  ```

*  Add this configuration block to your `postgres.d/conf.yaml` file to start collecting your PostgreSQL logs:

  ```
  logs:
      - type: file
        path: /var/log/pg_log/pg.log
        source: postgresql
        sourcecategory: database
        service: myapp
        #To handle multi line that starts with yyyy-mm-dd use the following pattern
        #log_processing_rules:
        #  - type: multi_line
        #    pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
        #    name: new_log_start_with_date
  ```
  Change the `service` and `path` parameter values and configure them for your environment.
  See the [sample postgres.d/conf.yaml][14] for all available configuration options.

* [Restart the Agent][15].

**Learn more about log collection [in the log documentation][16]**
### Validation

[Run the Agent's `status` subcommand][17] and look for `postgres` under the Checks section.

## Data Collected
### Metrics

Some of the metrics listed below require additional configuration, see the [sample postgres.d/conf.yaml][14] for all configurable options.

See [metadata.csv][18] for a list of metrics provided by this integration.

### Events
The PostgreSQL check does not include any events at this time.

### Service Checks

**postgres.can_connect**

Returns `CRITICAL` if the Agent is unable to connect to the monitored PostgreSQL instance. Returns `OK` otherwise.

## Further Reading
### FAQ
* [PostgreSQL custom metric collection explained][19]

### Blog posts
* To get a better idea of how (or why) to have 100x faster PostgreSQL performance by changing 1 line with Datadog, check out our [series of blog posts][20] about it.
* [Key metrics for PostgreSQL monitoring][21]
* [Collecting metrics with PostgreSQL monitoring tools][22]
* [How to collect and monitor PostgreSQL data with Datadog][23]

[13]: https://app.datadoghq.com/account/settings#agent
[14]: https://github.com/DataDog/integrations-core/blob/master/postgres/datadog_checks/postgres/data/conf.yaml.example
[15]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[16]: https://docs.datadoghq.com/logs
[17]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[18]: https://github.com/DataDog/integrations-core/blob/master/postgres/metadata.csv
[19]: https://docs.datadoghq.com/integrations/faq/postgres-custom-metric-collection-explained
[20]: https://www.datadoghq.com/blog/100x-faster-postgres-performance-by-changing-1-line/
[21]: https://www.datadoghq.com/blog/postgresql-monitoring/
[22]: https://www.datadoghq.com/blog/postgresql-monitoring-tools/
[23]: https://www.datadoghq.com/blog/collect-postgresql-data-with-datadog/
[24]: https://raw.githubusercontent.com/DataDog/integrations-core/master/postgres/images/postgresql_dashboard.png
[25]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
