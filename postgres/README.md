# PostgreSQL Integration

![PostgreSQL Graph][1]

## Overview

Get metrics from the PostgreSQL service in real time to:

* Visualize and monitor PostgreSQL states
* Received notifications about PostgreSQL failovers and events

## Setup
### Installation

The PostgreSQL check is packaged with the Agent. To start gathering your PostgreSQL metrics and logs, [install the Agent][2].

### Configuration
#### Prepare Postgres

To get started with the PostgreSQL integration, create a read-only `datadog` user with proper access to your PostgreSQL server. Start `psql` on your PostgreSQL database and run:

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

**Note**: When generating custom metrics that require querying additional tables, you may need to grant the `CONNECT` permission on those tables to the `datadog` user.

To verify the permissions are correct, run the following command:

```
psql -h localhost -U datadog postgres -c \
"select * from pg_stat_database LIMIT(1);" \
&& echo -e "\e[0;32mPostgres connection - OK\e[0m" \
|| echo -e "\e[0;31mCannot connect to Postgres\e[0m"
```

When it prompts for a password, enter the one used in the first command.


**Note**: For PostgreSQL versions 9.6 and below, run the following and create a `SECURITY DEFINER` to read from `pg_stat_activity`.

```
CREATE FUNCTION pg_stat_activity() RETURNS SETOF pg_catalog.pg_stat_activity AS
$$ SELECT * from pg_catalog.pg_stat_activity; $$
LANGUAGE sql VOLATILE SECURITY DEFINER;

CREATE VIEW pg_stat_activity_dd AS SELECT * FROM pg_stat_activity();
grant SELECT ON pg_stat_activity_dd to datadog;
```

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `postgres.d/conf.yaml` file to point to your `host` / `port` and set the masters to monitor. See the [sample postgres.d/conf.yaml][3] for all available configuration options.

    ```yaml
      init_config:

      instances:

          ## @param host - string - required
          ## The hostname to connect to.
          ## NOTE: Even if the server name is "localhost", the agent connects to
          ## PostgreSQL using TCP/IP, unless you also provide a value for the sock key.
          ## If `use_psycopg2` is enabled, use the directory containing
          ## the UNIX socket (ex: `/run/postgresql/`) otherwise, use the full path to
          ##  the socket file (ex: `/run/postgresql/.s.PGSQL.5433`).
          #
        - host: localhost

          ## @param port - integer - required
          ## Port to use when connecting to PostgreSQL.
          #
          port: 5432

          ## @param user - string - required
          ## Datadog Username created to connect to PostgreSQL.
          #
          username: datadog

          ## @param pass - string - required
          ## Password associated with the Datadog user.
          #
          password: "<PASSWORD>"
    ```

2. [Restart the Agent][4].

##### Log collection

**Available for Agent >6.0**

PostgreSQL default logging is to `stderr` and logs do not include detailed information. It is recommended to log into a file with additional details specified in the log line prefix.

1. Edit your PostgreSQL configuration file `/etc/postgresql/<version>/main/postgresql.conf` and uncomment the following parameter in the log section:

    ```conf
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

2. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
      logs_enabled: true
    ```

3.  Add this configuration block to your `postgres.d/conf.yaml` file to start collecting your PostgreSQL logs:

    ```yaml
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

    Change the `service` and `path` parameter values to configure for your environment. See the [sample postgres.d/conf.yaml][3] for all available configuration options.

4. [Restart the Agent][4].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][5] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                           |
|----------------------|---------------------------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `postgres`                                                                      |
| `<INIT_CONFIG>`      | blank or `{}`                                                                   |
| `<INSTANCE_CONFIG>`  | `{"host":"%%host%%", "port":5432,"username":"datadog","password":"<PASSWORD>"}` |

##### Log collection

**Available for Agent v6.5+**

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection documentation][6].

| Parameter      | Value                                               |
|----------------|-----------------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "postgresql", "service": "postgresql"}` |

### Validation

[Run the Agent's status subcommand][7] and look for `postgres` under the Checks section.

## Data Collected

Some of the metrics listed below require additional configuration, see the [sample postgres.d/conf.yaml][3] for all configurable options.

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Events
The PostgreSQL check does not include any events.

### Service Checks

**postgres.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to the monitored PostgreSQL instance, otherwie returns `OK`.

## Further Reading
Additional helpful documentation, links, and articles:

### FAQ

* [PostgreSQL custom metric collection explained][9]

### Blog posts

* [100x faster Postgres performance by changing 1 line][10]
* [Key metrics for PostgreSQL monitoring][11]
* [Collecting metrics with PostgreSQL monitoring tools][12]
* [How to collect and monitor PostgreSQL data with Datadog][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/postgres/images/postgresql_dashboard.png
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/postgres/datadog_checks/postgres/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/autodiscovery/integrations/
[6]: https://docs.datadoghq.com/agent/docker/log/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/postgres/metadata.csv
[9]: https://docs.datadoghq.com/integrations/faq/postgres-custom-metric-collection-explained
[10]: https://www.datadoghq.com/blog/100x-faster-postgres-performance-by-changing-1-line
[11]: https://www.datadoghq.com/blog/postgresql-monitoring
[12]: https://www.datadoghq.com/blog/postgresql-monitoring-tools
[13]: https://www.datadoghq.com/blog/collect-postgresql-data-with-datadog
