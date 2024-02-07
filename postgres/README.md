# PostgreSQL Integration

![PostgreSQL Graph][1]

## Overview

The Postgres integration provides health and performance metrics for your Postgres database in near real-time. Visualize these metrics with the provided dashboard and create monitors to alert your team on PostgreSQL states.

Enable [Database Monitoring][28] (DBM) for enhanced insights into query performance and database health. In addition to the standard integration, Datadog DBM provides query-level metrics, live and historical query snapshots, wait event analysis, database load, query explain plans, and blocking query insights.

## Setup

<div class="alert alert-info">This page describes the standard Postgres Agent integration. If you are looking for the Database Monitoring product for Postgres, see <a href="https://docs.datadoghq.com/database_monitoring" target="_blank">Datadog Database Monitoring</a>.</div>

### Installation

The PostgreSQL check is packaged with the Agent. To start gathering your PostgreSQL metrics and logs, [install the Agent][2].

### Configuration

**Note**: To install Database Monitoring for PostgreSQL, select your hosting solution in the [Database Monitoring documentation][29] for instructions.

Proceed with the following steps in this guide only if you are installing the standard integration alone.

#### Prepare Postgres

To get started with the standard PostgreSQL integration, create a read-only `datadog` user with proper access to your PostgreSQL server. Start `psql` on your PostgreSQL database.

For PostgreSQL version 10 and above, run:

```shell
create user datadog with password '<PASSWORD>';
grant pg_monitor to datadog;
grant SELECT ON pg_stat_database to datadog;
```

For older PostgreSQL versions, run:

```shell
create user datadog with password '<PASSWORD>';
grant SELECT ON pg_stat_database to datadog;
```

To verify the permissions are correct, run the following command:

```shell
psql -h localhost -U datadog postgres -c \
"select * from pg_stat_database LIMIT(1);" \
&& echo -e "\e[0;32mPostgres connection - OK\e[0m" \
|| echo -e "\e[0;31mCannot connect to Postgres\e[0m"
```

When it prompts for a password, enter the one used in the first command.

**Note**: For PostgreSQL versions 9.6 and below, run the following and create a `SECURITY DEFINER` to read from `pg_stat_activity`.

```shell
CREATE FUNCTION pg_stat_activity() RETURNS SETOF pg_catalog.pg_stat_activity AS
$$ SELECT * from pg_catalog.pg_stat_activity; $$
LANGUAGE sql VOLATILE SECURITY DEFINER;

CREATE VIEW pg_stat_activity_dd AS SELECT * FROM pg_stat_activity();
grant SELECT ON pg_stat_activity_dd to datadog;
```

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

**Note**: When generating custom metrics that require querying additional tables, you may need to grant the `SELECT` permission on those tables to the `datadog` user. Example: `grant SELECT on <TABLE_NAME> to datadog;`. Check the [FAQ section][30] for more information.

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `postgres.d/conf.yaml` file to point to your `host` / `port` and set the masters to monitor. See the [sample postgres.d/conf.yaml][3] for all available configuration options.

    ```yaml
    init_config:
 
    instances:
      ## @param host - string - required
      ## The hostname to connect to.
      ## NOTE: Even if the server name is "localhost", the agent connects to
      ## PostgreSQL using TCP/IP, unless you also provide a value for the sock key.
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

        ## @param dbname - string - optional - default: postgres
        ## Name of the PostgresSQL database to monitor.
        ## Note: If omitted, the default system postgres database is queried.
        #
        dbname: "<DB_NAME>"
   
        # @param disable_generic_tags - boolean - optional - default: false
        # The integration will stop sending server tag as is redundant with host tag
        disable_generic_tags: true
    ```

2. To collect relation metrics, connect the Agent to every logical database. These databases can be discovered automatically, or each one can be listed explicitly in the configuration. 
   
    - To discover logical databases automatically on a given instance, enable autodiscovery on that instance:

    ```yaml
    instances:
      - host: localhost
        port: 5432
        database_autodiscovery:
          enabled: true
          # Optionally, set the include field to specify
          # a set of databases you are interested in discovering
          include:
            - mydb.*
            - example.*
        relations:
          - relation_regex: .*
    ```

    - Alternatively, you can list each logical database as an instance in the configuration:
    
    ```yaml
    instances:
      - host: example-service-primary.example-host.com
        port: 5432
        username: datadog
        password: '<PASSWORD>'
        relations:
          - relation_name: products
          - relation_name: external_seller_products
      - host: example-service-replica-1.example-host.com
        port: 5432
        username: datadog
        password: '<PASSWORD>'
        relations:
          - relation_regex: inventory_.*
            relkind:
              - r
              - i
      - host: example-service-replica-2.example-host.com
        port: 5432
        username: datadog
        password: '<PASSWORD>'
        relations:
          - relation_regex: .*
    ```
3. [Restart the Agent][4].

##### Trace collection

Datadog APM integrates with Postgres to see the traces across your distributed system. Trace collection is enabled by default in the Datadog Agent v6+. To start collecting traces:

1. [Enable trace collection in Datadog][5].
2. [Instrument your application that makes requests to Postgres][6].

##### Log collection

_Available for Agent versions >6.0_

PostgreSQL default logging is to `stderr`, and logs do not include detailed information. It is recommended to log into a file with additional details specified in the log line prefix. See the PostgreSQL documentation on[Error Reporting and Logging][7] for more information.

1. Logging is configured within the file `/etc/postgresql/<VERSION>/main/postgresql.conf`. For regular log results, including statement outputs, uncomment the following parameters in the log section:

   ```conf
     logging_collector = on
     log_directory = 'pg_log'  # directory where log files are written,
                               # can be absolute or relative to PGDATA
     log_filename = 'pg.log'   # log file name, can include pattern
     log_statement = 'all'     # log all queries
     #log_duration = on
     log_line_prefix= '%m [%p] %d %a %u %h %c '
     log_file_mode = 0644
     ## For Windows
     #log_destination = 'eventlog'
   ```

2. To gather detailed duration metrics and make them searchable in the Datadog interface, they should be configured inline with the statement themselves. See below for the recommended configuration differences from above. **Note**: Both `log_statement` and `log_duration` options are commented out. See [Logging statement/duration on the same line][8] for discussion on this topic.

    This config logs all statements. To reduce the output based on duration, set the `log_min_duration_statement` value to the desired minimum duration (in milliseconds):

   ```conf
     log_min_duration_statement = 0    # -1 is disabled, 0 logs all statements
                                       # and their durations, > 0 logs only
                                       # statements running at least this number
                                       # of milliseconds
     #log_statement = 'all'
     #log_duration = on
   ```

3. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

4. Add and edit this configuration block to your `postgres.d/conf.yaml` file to start collecting your PostgreSQL logs:

   ```yaml
   logs:
     - type: file
       path: "<LOG_FILE_PATH>"
       source: postgresql
       service: "<SERVICE_NAME>"
       #To handle multi line that starts with yyyy-mm-dd use the following pattern
       #log_processing_rules:
       #  - type: multi_line
       #    pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
       #    name: new_log_start_with_date
   ```

      Change the `service` and `path` parameter values to configure for your environment. See the [sample postgres.d/conf.yaml][3] for all available configuration options.

5. [Restart the Agent][4].

<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integrations Templates][9] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["postgres"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"host":"%%host%%", "port":5432,"username":"datadog","password":"<PASSWORD>"}]'
```

##### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker Log Collection][10].

Then, set [Log Integrations][11] as Docker labels:

```yaml
LABEL "com.datadoghq.ad.logs"='[{"source":"postgresql","service":"postgresql"}]'
```

##### Trace collection

APM for containerized apps is supported on Agent v6+ but requires extra configuration to begin collecting traces.

Required environment variables on the Agent container:

| Parameter            | Value                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| `<DD_API_KEY>` | `api_key`                                                                  |
| `<DD_APM_ENABLED>`      | true                                                              |
| `<DD_APM_NON_LOCAL_TRAFFIC>`  | true |

See [Tracing Docker Applications][12] for a complete list of available environment variables and configuration.

Then, [instrument your application container that makes requests to Postgres][11] and set `DD_AGENT_HOST` to the name of your Agent container.


<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][13] as pod annotations on your application container. Aside from this, templates can also be configured with [a file, a configmap, or a key-value store][14].

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: postgres
  annotations:
    ad.datadoghq.com/postgresql.check_names: '["postgres"]'
    ad.datadoghq.com/postgresql.init_configs: '[{}]'
    ad.datadoghq.com/postgresql.instances: |
      [
        {
          "host": "%%host%%",
          "port":"5432",
          "username":"datadog",
          "password":"<PASSWORD>"
        }
      ]
spec:
  containers:
    - name: postgres
```

**Annotations v2** (for Datadog Agent v7.36+)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: postgres
  annotations:
    ad.datadoghq.com/postgres.checks: |
      {
        "postgres": {
          "init_config": {},
          "instances": [
            {
              "host": "%%host%%",
              "port":"5432",
              "username":"datadog",
              "password":"<PASSWORD>"
            }
          ]
        }
      }
spec:
  containers:
    - name: postgres
```

##### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][15].

Then, set [Log Integrations][11] as pod annotations. This can also be configured with [a file, a configmap, or a key-value store][16].

**Annotations v1/v2**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: postgres
  annotations:
    ad.datadoghq.com/postgres.logs: '[{"source":"postgresql","service":"<SERVICE_NAME>"}]'
spec:
  containers:
    - name: postgres
```

##### Trace collection

APM for containerized apps is supported on hosts running Agent v6+ but requires extra configuration to begin collecting traces.

Required environment variables on the Agent container:

| Parameter            | Value                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| `<DD_API_KEY>` | `api_key`                                                                  |
| `<DD_APM_ENABLED>`      | true                                                              |
| `<DD_APM_NON_LOCAL_TRAFFIC>`  | true |

See [Tracing Kubernetes Applications][17] and the [Kubernetes DaemonSet Setup][18] for a complete list of available environment variables and configuration.

Then, [instrument your application container that makes requests to Postgres][11].

<!-- xxz tab xxx -->
<!-- xxx tab "ECS" xxx -->

#### ECS

To configure this check for an Agent running on ECS:

##### Metric collection

Set [Autodiscovery Integrations Templates][9] as Docker labels on your application container:

```json
{
  "containerDefinitions": [{
    "name": "postgres",
    "image": "postgres:latest",
    "dockerLabels": {
      "com.datadoghq.ad.check_names": "[\"postgres\"]",
      "com.datadoghq.ad.init_configs": "[{}]",
      "com.datadoghq.ad.instances": "[{\"host\":\"%%host%%\", \"port\":5432,\"username\":\"datadog\",\"password\":\"<PASSWORD>\"}]"
    }
  }]
}
```

##### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see [ECS Log Collection][12].

Then, set [Log Integrations][11] as Docker labels:

```json
{
  "containerDefinitions": [{
    "name": "postgres",
    "image": "postgres:latest",
    "dockerLabels": {
      "com.datadoghq.ad.logs": "[{\"source\":\"postgresql\",\"service\":\"postgresql\"}]"
    }
  }]
}
```

##### Trace collection

APM for containerized apps is supported on Agent v6+ but requires extra configuration to begin collecting traces.

Required environment variables on the Agent container:

| Parameter            | Value                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| `<DD_API_KEY>` | `api_key`                                                                  |
| `<DD_APM_ENABLED>`      | true                                                              |
| `<DD_APM_NON_LOCAL_TRAFFIC>`  | true |

See [Tracing Docker Applications][27] for a complete list of available environment variables and configuration.

Then, [instrument your application container that makes requests to Postgres][11] and set `DD_AGENT_HOST` to the [EC2 private IP address][17].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][19] and look for `postgres` under the Checks section.

## Data Collected

Some of the metrics listed below require additional configuration, see the [sample postgres.d/conf.yaml][3] for all configurable options.

### Metrics

See [metadata.csv][20] for a list of metrics provided by this integration.

For Agent version `7.32.0` and later, if you have Database Monitoring enabled, the `postgresql.connections` metric is tagged with `state`, `app`, `db` and `user`.

### Events

The PostgreSQL check does not include any events.

### Service Checks

See [service_checks.json][18] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][21].

## Further Reading

Additional helpful documentation, links, and articles:

### FAQ

- [PostgreSQL custom metric collection explained][22]

### Blog posts

- [100x faster Postgres performance by changing 1 line][23]
- [Key metrics for PostgreSQL monitoring][24]
- [Collecting metrics with PostgreSQL monitoring tools][25]
- [How to collect and monitor PostgreSQL data with Datadog][26]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/postgres/images/postgresql_dashboard.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/integrations-core/blob/master/postgres/datadog_checks/postgres/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/tracing/send_traces/
[6]: https://docs.datadoghq.com/tracing/setup/
[7]: https://www.postgresql.org/docs/11/runtime-config-logging.html
[8]: https://www.postgresql.org/message-id/20100210180532.GA20138@depesz.com
[9]: https://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[10]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#installation
[11]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[12]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux
[13]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[14]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[15]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[16]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=daemonset#configuration
[17]: https://docs.datadoghq.com/agent/amazon_ecs/apm/?tab=ec2metadataendpoint#setup
[18]: https://github.com/DataDog/integrations-core/blob/master/postgres/assets/service_checks.json
[19]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[20]: https://github.com/DataDog/integrations-core/blob/master/postgres/metadata.csv
[21]: https://docs.datadoghq.com/help
[22]: https://docs.datadoghq.com/integrations/faq/postgres-custom-metric-collection-explained/
[23]: https://www.datadoghq.com/blog/100x-faster-postgres-performance-by-changing-1-line
[24]: https://www.datadoghq.com/blog/postgresql-monitoring
[25]: https://www.datadoghq.com/blog/postgresql-monitoring-tools
[26]: https://www.datadoghq.com/blog/collect-postgresql-data-with-datadog
[27]: https://docs.datadoghq.com/agent/docker/apm/
[28]: https://docs.datadoghq.com/database_monitoring/
[29]: https://docs.datadoghq.com/database_monitoring/#postgres
[30]: https://docs.datadoghq.com/integrations/postgres/?tab=host#faq