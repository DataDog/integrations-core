# MySQL check

![MySQL Dashboard][1]

## Overview

The Datadog Agent can collect a variety of telemetry from MySQL databases, including (but not limited to):

- Query throughput
- Query performance (e.g. average query run time, slow queries, etc.)
- Connections (e.g. currently open connections, aborted connections, errors, etc.)
- InnoDB (e.g. buffer pool metrics, etc.)
- Query metrics, samples & execution plans (with [Deep Database Monitoring](#deep-database-monitoring))

You can also create your own metrics using custom SQL queries.

**Note:** This integration is also compatible with [MariaDB][2], as it serves as a ["drop-in replacement"][3] for MySQL.

## Setup

The Datadog Agent collects telemetry directly from the database by logging in as a read-only user.

Some setup is required to begin using the MySQL integration:

1. [Configure database parameters](#database-configuration)
1. [Grant the Datadog Agent access to the database](#agent-database-access)
1. [Install the Datadog Agent](#agent-installation)
1. [Configure the Datadog Agent](#agent-configuration)

### Database configuration

#### Performance schema

In order to collect query metrics, samples, and execution plans for [Deep Database Monitoring](#deep-database-monitoring), the [MySQL Performance Schema][28] needs to be enabled.   

<!-- xxx tabs xxx -->
<!-- xxx tab "Self-hosted" xxx -->

Configure the following [Performance Schema Options][29]. They can be configured on the command-line or in option files (for example,`mysql.conf`).  

| Parameter | Value | Description |
| --- | --- | --- |
| `performance_schema` | `ON` | Required. Enables the [Performance Schema][30]. |
| `performance-schema-consumer-events-statements-current` | `ON` | Required. Enables monitoring of currently running queries. |
| `performance-schema-consumer-events-statements-history` | `ON` | Optional. Enables tracking recent query history per thread. If enabled it increases the likelihood of capturing execution details from infrequent queries. |
| `performance-schema-consumer-events-statements-history-long` | `ON` | Optional. Enables tracking of a larger number of recent queries across all threads. If enabled it increases the likelihood of capturing execution details from infrequent queries. |
| `max_digest_length` | `4096` | Required for collection of larger queries. If left at the default value then queries longer than `1024` characters will not be collected. |
| <code style="word-break:break-all;">`performance_schema_max_digest_length`</code> | `4096` | Must match `max_digest_length`. |
| <code style="word-break:break-all;">`performance_schema_max_sql_text_length`</code> | `4096` | Must match `max_digest_length`. |

**Note**: an alternative method to configuring the `performance-schema-consumer-*` settings is to configure them dynamically at runtime. See [Runtime Setup Consumers](#runtime-setup-consumers).

<!-- xxz tab xxx -->
<!-- xxx tab "Amazon RDS MySQL" xxx -->

Configure the following in the [DB Parameter Group][31]:

| Parameter | Value | Description |
| --- | --- | --- |
| `performance_schema` | `1` | Required. Enables the [Performance Schema][30]. |
| `max_digest_length` | `4096` | Required for collection of larger queries. Increases the size of SQL digest text in `events_statements_*` tables. If left at the default value then queries longer than `1024` characters will not be collected. |
| `performance_schema_max_digest_length` | `4096` | Must match `max_digest_length`. |
| `performance_schema_max_sql_text_length` | `4096` | Must match `max_digest_length`. |

**Note**: For Amazon RDS MySQL, there is no way to configure the `events-statements_*` consumers in the [DB Parameter Group][31] so they must enabled dynamically at runtime. See [Runtime Setup Consumers](#runtime-setup-consumers).

<!-- xxz tab xxx -->
<!-- xxx tab "Amazon RDS Aurora MySQL" xxx -->

Configure the following in the [DB Parameter Group][32]:

| Parameter | Value | Description |
| --- | --- | --- |
| `performance_schema` | `ON` | Required. Enables the [Performance Schema][30]. |
| <code style="word-break:break-all;">performance_schema_consumer_events_statements_current</code> | `ON` | Required. Enables monitoring of currently running queries. |
| <code style="word-break:break-all;">performance_schema_consumer_events_statements_history</code> | `ON` | Optional. Enables tracking recent query history per thread. If enabled it increases the likelihood of capturing execution details from infrequent queries. |
| <code style="word-break:break-all;">performance_schema_consumer_events_statements_history_long</code> | `ON` | Optional. Enables tracking of a larger number of recent queries across all threads. If enabled it increases the likelihood of capturing execution details from infrequent queries. |
| `max_digest_length` | `4096` | Required for collection of larger queries. Increases the size of SQL digest text in `events_statements_*` tables. If left at the default value then queries longer than `1024` characters will not be collected. |
| <code style="word-break:break-all;">`performance_schema_max_digest_length`</code> | `4096` | Must match `max_digest_length`. |
| <code style="word-break:break-all;">`performance_schema_max_sql_text_length`</code> | `4096` | Must match `max_digest_length`. |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Agent Database Access

The Datadog Agent requires read-only access to the database in order to collect statistics and queries.

The following instructions grant the agent permission to login from any host using `datadog@'%'`. This is required for managed databases like `Amazon RDS` or `Google CloudSQL` as it's not possible to install the datadog agent directly on the host. For self-hosted databases the datadog user can be restricted to be allowed to login only from localhost by using `datadog@'localhost'`. See the [MySQL documentation][5] for more info.

<!-- xxx tabs xxx -->
<!-- xxx tab "MySQL ≥ 8.0" xxx -->

```SQL
CREATE USER datadog@'%' IDENTIFIED WITH mysql_native_password by '<UNIQUEPASSWORD>';
ALTER USER datadog@'%' WITH MAX_USER_CONNECTIONS 5;
GRANT REPLICATION CLIENT ON *.* TO datadog@'%'
GRANT PROCESS ON *.* TO datadog@'%';
GRANT SELECT ON performance_schema.* TO datadog@'%';
```

<!-- xxz tab xxx -->
<!-- xxx tab "MySQL 5.6 & 5.7" xxx -->

```SQL
CREATE USER datadog@'%' IDENTIFIED BY '<UNIQUEPASSWORD>';
GRANT REPLICATION CLIENT ON *.* TO datadog@'%' WITH MAX_USER_CONNECTIONS 5;
GRANT PROCESS ON *.* TO datadog@'%';
GRANT SELECT ON performance_schema.* TO datadog@'%';
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

The following schema and procedures are required for [Deep Database Monitoring](#deep-database-monitoring).

```SQL
CREATE SCHEMA IF NOT EXISTS datadog;
GRANT EXECUTE ON datadog.* to datadog@'%'
GRANT CREATE TEMPORARY TABLES ON `datadog`.* TO datadog@'%';
```

Create the procedures to enable the agent to collect execution plans. The `explain_statement` procedure must be created in every schema from which you want to collect execution plans.   

```SQL
DELIMITER $$

CREATE PROCEDURE datadog.explain_statement(IN query TEXT)
    SQL SECURITY DEFINER
BEGIN
    SET @explain := CONCAT('EXPLAIN FORMAT=json ', query);
    PREPARE stmt FROM @explain;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
END $$

-- repeat for every application schema 
CREATE PROCEDURE {schema}.explain_statement(IN query TEXT)
    SQL SECURITY DEFINER
BEGIN
    SET @explain := CONCAT('EXPLAIN FORMAT=json ', query);
    PREPARE stmt FROM @explain;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
END $$

DELIMITER ;
GRANT EXECUTE ON PROCEDURE {schema}.explain_statement TO datadog@'%';
```

##### Runtime Setup Consumers
Create the following procedure to give the agent the ability to enable `performance_schema.events_statements_*` consumers at runtime. This is necessary on databases where the performance schema consumers can't be enabled permanently in the configuration (like Amazon RDS). Required only for [Deep Database Monitoring](#deep-database-monitoring).

```SQL
DELIMITER $$
CREATE PROCEDURE datadog.enable_events_statements_consumers()
    SQL SECURITY DEFINER
BEGIN
    UPDATE performance_schema.setup_consumers SET enabled='YES' WHERE name LIKE 'events_statements_%';
END $$
DELIMITER ;
GRANT EXECUTE ON PROCEDURE datadog.enable_events_statements_consumers TO datadog@'%';
```

Verify the user was created successfully using the following commands - replace `<UNIQUEPASSWORD>` with the password you created above:

```shell
mysql -u datadog --password=<UNIQUEPASSWORD> -e "show status" | \
grep Uptime && echo -e "\033[0;32mMySQL user - OK\033[0m" || \
echo -e "\033[0;31mCannot connect to MySQL\033[0m"
```

```shell
mysql -u datadog --password=<UNIQUEPASSWORD> -e "show slave status" && \
echo -e "\033[0;32mMySQL grant - OK\033[0m" || \
echo -e "\033[0;31mMissing REPLICATION CLIENT grant\033[0m"
```

### Agent Installation

The MySQL check is packaged with the Agent. To start gathering your MySQL metrics and logs, [install the Agent][4].

### Agent Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

Edit the `mysql.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][6] to start collecting your MySQL [metrics](#metric-collection) and [logs](#log-collection). See the [sample mysql.d/conf.yaml][7] for all available configuration options.

##### Metric collection

- Add this configuration block to your `mysql.d/conf.yaml` to collect your [MySQL metrics](#metrics):

  ```yaml
  init_config:

  instances:
    - server: 127.0.0.1
      user: datadog
      pass: "<YOUR_CHOSEN_PASSWORD>" # from the CREATE USER step earlier
      port: "<YOUR_MYSQL_PORT>" # e.g. 3306
      options:
        replication: false
        galera_cluster: true
        extra_status_metrics: true
        extra_innodb_metrics: true
        extra_performance_metrics: true
        schema_size_metrics: false
        disable_innodb_metrics: false
  ```

**Note**: Wrap your password in single quotes in case a special character is present.

To collect `extra_performance_metrics`, your MySQL server must have `performance_schema` enabled - otherwise set `extra_performance_metrics` to `false`. For more information on `performance_schema`, [see the MySQL documentation][8].

Note that the `datadog` user should be set up in the MySQL integration configuration as `host: 127.0.0.1` instead of `localhost`. Alternatively, you may also use `sock`.

See our [sample mysql.yaml][9] for all available configuration options, including those for custom metrics.

[Restart the Agent][10] to start sending MySQL metrics to Datadog.

##### Log collection

_Available for Agent versions >6.0_

1. By default MySQL logs everything in `/var/log/syslog` which requires root access to read. To make the logs more accessible, follow these steps:

   - Edit `/etc/mysql/conf.d/mysqld_safe_syslog.cnf` and remove or comment the lines.
   - Edit `/etc/mysql/my.cnf` and add following lines to enable general, error, and slow query logs:

     ```conf
       [mysqld_safe]
       log_error = /var/log/mysql/mysql_error.log

       [mysqld]
       general_log = on
       general_log_file = /var/log/mysql/mysql.log
       log_error = /var/log/mysql/mysql_error.log
       slow_query_log = on
       slow_query_log_file = /var/log/mysql/mysql_slow.log
       long_query_time = 2
     ```

   - Save the file and restart MySQL using following commands:
     `service mysql restart`
   - Make sure the Agent has read access on the `/var/log/mysql` directory and all of the files within. Double-check your logrotate configuration to make sure those files are taken into account and that the permissions are correctly set there as well.
   - In `/etc/logrotate.d/mysql-server` there should be something similar to:

     ```text
       /var/log/mysql.log /var/log/mysql/mysql.log /var/log/mysql/mysql_slow.log {
               daily
               rotate 7
               missingok
               create 644 mysql adm
               Compress
       }
     ```

2. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

3. Add this configuration block to your `mysql.d/conf.yaml` file to start collecting your MySQL logs:

   ```yaml
   logs:
     - type: file
       path: "<ERROR_LOG_FILE_PATH>"
       source: mysql
       service: "<SERVICE_NAME>"

     - type: file
       path: "<SLOW_QUERY_LOG_FILE_PATH>"
       source: mysql
       service: "<SERVICE_NAME>"
       log_processing_rules:
         - type: multi_line
           name: new_slow_query_log_entry
           pattern: "# Time:"
           # If mysqld was started with `--log-short-format`, use:
           # pattern: "# Query_time:"
           # If using mysql version <5.7, use the following rules instead:
           # - type: multi_line
           #   name: new_slow_query_log_entry
           #   pattern: "# Time|# User@Host"
           # - type: exclude_at_match
           #   name: exclude_timestamp_only_line
           #   pattern: "# Time:"

     - type: file
       path: "<GENERAL_LOG_FILE_PATH>"
       source: mysql
       service: "<SERVICE_NAME>"
       # For multiline logs, if they start by the date with the format yyyy-mm-dd uncomment the following processing rule
       # log_processing_rules:
       #   - type: multi_line
       #     name: new_log_start_with_date
       #     pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
       # If the logs start with a date with the format yymmdd but include a timestamp with each new second, rather than with each log, uncomment the following processing rule
       # log_processing_rules:
       #   - type: multi_line
       #     name: new_logs_do_not_always_start_with_timestamp
       #     pattern: \t\t\s*\d+\s+|\d{6}\s+\d{,2}:\d{2}:\d{2}\t\s*\d+\s+
   ```

    See our [sample mysql.yaml][9] for all available configuration options, including those for custom metrics.

4. [Restart the Agent][10].

<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->
#### Docker

To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integration Templates][27] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["mysql"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"server": "%%host%%", "user": "datadog","pass": "<UNIQUEPASSWORD>"}]'
```

See the [Autodiscovery template variables documentation][28] to learn how to pass `<UNIQUEPASSWORD>` as an environment variable instead of a label.

#### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see the [Docker log collection documentation][29].

Then, set [Log Integrations][30] as Docker labels:

```yaml
LABEL "com.datadoghq.ad.logs"='[{"source":"mysql","service":"mysql"}]'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][31] as pod annotations on your application container. Alternatively, you can configure templates with a [file, configmap, or key-value store][32].

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mysql
  annotations:
    ad.datadoghq.com/nginx.check_names: '["mysql"]'
    ad.datadoghq.com/nginx.init_configs: '[{}]'
    ad.datadoghq.com/nginx.instances: |
      [
        {
          "server": "%%host%%", 
          "user": "datadog",
          "pass": "<UNIQUEPASSWORD>"
        }
      ]
  labels:
    name: mysql
spec:
  containers:
    - name: mysql
```

See the [Autodiscovery template variables documentation][28] to learn how to pass `<UNIQUEPASSWORD>` as an environment variable instead of a label.

#### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see the [Kubernetes log collection documentation][33].

Then, set [Log Integrations][34] as pod annotations. Alternatively, you can configure this with a [file, configmap, or key-value store][35].

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mysql
  annotations:
    ad.datadoghq.com/mysql.logs: '[{"source": "mysql", "service": "mysql"}]'
  labels:
    name: mysql
```

<!-- xxz tab xxx -->
<!-- xxx tab "ECS" xxx -->

#### ECS

To configure this check for an Agent running on ECS:

##### Metric collection

Set [Autodiscovery Integrations Templates][36] as Docker labels on your application container:

```json
{
  "containerDefinitions": [{
    "name": "mysql",
    "image": "mysql:latest",
    "dockerLabels": {
      "com.datadoghq.ad.check_names": "[\"mysql\"]",
      "com.datadoghq.ad.init_configs": "[{}]",
      "com.datadoghq.ad.instances": "[{\"server\": \"%%host%%\", \"user\": \"datadog\",\"pass\": \"<UNIQUEPASSWORD>\"}]"
    }
  }]
}
```

See the [Autodiscovery template variables documentation][28] to learn how to pass `<UNIQUEPASSWORD>` as an environment variable instead of a label.

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see the [ECS log collection documentation][37].

Then, set [Log Integrations][34] as Docker labels:

```yaml
{
  "containerDefinitions": [{
    "name": "mysql",
    "image": "mysql:latest",
    "dockerLabels": {
      "com.datadoghq.ad.logs": "[{\"source\":\"mysql\",\"service\":\"mysql\"}]"
    }
  }]
}
```
<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][14] and look for `mysql` under the Checks section.

## Deep Database Monitoring

<div class="alert alert-warning">
Deep Database Monitoring is currently in beta.
</div>

Datadog **Deep Database Monitoring** provides deeper visibility into what is running on your database by collecting per-query Metrics, Query Samples, and Execution Plans. To get started, add the `deep_database_monitoring` and `statement_samples` settings to your instance configuration:

```yaml
instances:
  - server: ""
    deep_database_monitoring: true
    statement_samples:
      enabled: true
```

Once enabled, visit the [Databases][27] page to get started!

## Data Collected

### Metrics

See [metadata.csv][15] for a list of metrics provided by this integration.

The check does not collect all metrics by default. Set the following boolean configuration options to `true` to enable the respective metrics:

`extra_status_metrics` adds the following metrics:

| Metric name                                  | Metric type |
| -------------------------------------------- | ----------- |
| mysql.binlog.cache_disk_use                  | GAUGE       |
| mysql.binlog.cache_use                       | GAUGE       |
| mysql.performance.handler_commit             | RATE        |
| mysql.performance.handler_delete             | RATE        |
| mysql.performance.handler_prepare            | RATE        |
| mysql.performance.handler_read_first         | RATE        |
| mysql.performance.handler_read_key           | RATE        |
| mysql.performance.handler_read_next          | RATE        |
| mysql.performance.handler_read_prev          | RATE        |
| mysql.performance.handler_read_rnd           | RATE        |
| mysql.performance.handler_read_rnd_next      | RATE        |
| mysql.performance.handler_rollback           | RATE        |
| mysql.performance.handler_update             | RATE        |
| mysql.performance.handler_write              | RATE        |
| mysql.performance.opened_tables              | RATE        |
| mysql.performance.qcache_total_blocks        | GAUGE       |
| mysql.performance.qcache_free_blocks         | GAUGE       |
| mysql.performance.qcache_free_memory         | GAUGE       |
| mysql.performance.qcache_not_cached          | RATE        |
| mysql.performance.qcache_queries_in_cache    | GAUGE       |
| mysql.performance.select_full_join           | RATE        |
| mysql.performance.select_full_range_join     | RATE        |
| mysql.performance.select_range               | RATE        |
| mysql.performance.select_range_check         | RATE        |
| mysql.performance.select_scan                | RATE        |
| mysql.performance.sort_merge_passes          | RATE        |
| mysql.performance.sort_range                 | RATE        |
| mysql.performance.sort_rows                  | RATE        |
| mysql.performance.sort_scan                  | RATE        |
| mysql.performance.table_locks_immediate      | GAUGE       |
| mysql.performance.table_locks_immediate.rate | RATE        |
| mysql.performance.threads_cached             | GAUGE       |
| mysql.performance.threads_created            | MONOTONIC   |

`extra_innodb_metrics` adds the following metrics:

| Metric name                                 | Metric type |
| ------------------------------------------- | ----------- |
| mysql.innodb.active_transactions            | GAUGE       |
| mysql.innodb.buffer_pool_data               | GAUGE       |
| mysql.innodb.buffer_pool_pages_data         | GAUGE       |
| mysql.innodb.buffer_pool_pages_dirty        | GAUGE       |
| mysql.innodb.buffer_pool_pages_flushed      | RATE        |
| mysql.innodb.buffer_pool_pages_free         | GAUGE       |
| mysql.innodb.buffer_pool_pages_total        | GAUGE       |
| mysql.innodb.buffer_pool_read_ahead         | RATE        |
| mysql.innodb.buffer_pool_read_ahead_evicted | RATE        |
| mysql.innodb.buffer_pool_read_ahead_rnd     | GAUGE       |
| mysql.innodb.buffer_pool_wait_free          | MONOTONIC   |
| mysql.innodb.buffer_pool_write_requests     | RATE        |
| mysql.innodb.checkpoint_age                 | GAUGE       |
| mysql.innodb.current_transactions           | GAUGE       |
| mysql.innodb.data_fsyncs                    | RATE        |
| mysql.innodb.data_pending_fsyncs            | GAUGE       |
| mysql.innodb.data_pending_reads             | GAUGE       |
| mysql.innodb.data_pending_writes            | GAUGE       |
| mysql.innodb.data_read                      | RATE        |
| mysql.innodb.data_written                   | RATE        |
| mysql.innodb.dblwr_pages_written            | RATE        |
| mysql.innodb.dblwr_writes                   | RATE        |
| mysql.innodb.hash_index_cells_total         | GAUGE       |
| mysql.innodb.hash_index_cells_used          | GAUGE       |
| mysql.innodb.history_list_length            | GAUGE       |
| mysql.innodb.ibuf_free_list                 | GAUGE       |
| mysql.innodb.ibuf_merged                    | RATE        |
| mysql.innodb.ibuf_merged_delete_marks       | RATE        |
| mysql.innodb.ibuf_merged_deletes            | RATE        |
| mysql.innodb.ibuf_merged_inserts            | RATE        |
| mysql.innodb.ibuf_merges                    | RATE        |
| mysql.innodb.ibuf_segment_size              | GAUGE       |
| mysql.innodb.ibuf_size                      | GAUGE       |
| mysql.innodb.lock_structs                   | RATE        |
| mysql.innodb.locked_tables                  | GAUGE       |
| mysql.innodb.locked_transactions            | GAUGE       |
| mysql.innodb.log_waits                      | RATE        |
| mysql.innodb.log_write_requests             | RATE        |
| mysql.innodb.log_writes                     | RATE        |
| mysql.innodb.lsn_current                    | RATE        |
| mysql.innodb.lsn_flushed                    | RATE        |
| mysql.innodb.lsn_last_checkpoint            | RATE        |
| mysql.innodb.mem_adaptive_hash              | GAUGE       |
| mysql.innodb.mem_additional_pool            | GAUGE       |
| mysql.innodb.mem_dictionary                 | GAUGE       |
| mysql.innodb.mem_file_system                | GAUGE       |
| mysql.innodb.mem_lock_system                | GAUGE       |
| mysql.innodb.mem_page_hash                  | GAUGE       |
| mysql.innodb.mem_recovery_system            | GAUGE       |
| mysql.innodb.mem_thread_hash                | GAUGE       |
| mysql.innodb.mem_total                      | GAUGE       |
| mysql.innodb.os_file_fsyncs                 | RATE        |
| mysql.innodb.os_file_reads                  | RATE        |
| mysql.innodb.os_file_writes                 | RATE        |
| mysql.innodb.os_log_pending_fsyncs          | GAUGE       |
| mysql.innodb.os_log_pending_writes          | GAUGE       |
| mysql.innodb.os_log_written                 | RATE        |
| mysql.innodb.pages_created                  | RATE        |
| mysql.innodb.pages_read                     | RATE        |
| mysql.innodb.pages_written                  | RATE        |
| mysql.innodb.pending_aio_log_ios            | GAUGE       |
| mysql.innodb.pending_aio_sync_ios           | GAUGE       |
| mysql.innodb.pending_buffer_pool_flushes    | GAUGE       |
| mysql.innodb.pending_checkpoint_writes      | GAUGE       |
| mysql.innodb.pending_ibuf_aio_reads         | GAUGE       |
| mysql.innodb.pending_log_flushes            | GAUGE       |
| mysql.innodb.pending_log_writes             | GAUGE       |
| mysql.innodb.pending_normal_aio_reads       | GAUGE       |
| mysql.innodb.pending_normal_aio_writes      | GAUGE       |
| mysql.innodb.queries_inside                 | GAUGE       |
| mysql.innodb.queries_queued                 | GAUGE       |
| mysql.innodb.read_views                     | GAUGE       |
| mysql.innodb.rows_deleted                   | RATE        |
| mysql.innodb.rows_inserted                  | RATE        |
| mysql.innodb.rows_read                      | RATE        |
| mysql.innodb.rows_updated                   | RATE        |
| mysql.innodb.s_lock_os_waits                | RATE        |
| mysql.innodb.s_lock_spin_rounds             | RATE        |
| mysql.innodb.s_lock_spin_waits              | RATE        |
| mysql.innodb.semaphore_wait_time            | GAUGE       |
| mysql.innodb.semaphore_waits                | GAUGE       |
| mysql.innodb.tables_in_use                  | GAUGE       |
| mysql.innodb.x_lock_os_waits                | RATE        |
| mysql.innodb.x_lock_spin_rounds             | RATE        |
| mysql.innodb.x_lock_spin_waits              | RATE        |

`extra_performance_metrics` adds the following metrics:

| Metric name                                     | Metric type |
| ----------------------------------------------- | ----------- |
| mysql.performance.query_run_time.avg            | GAUGE       |
| mysql.performance.digest_95th_percentile.avg_us | GAUGE       |

`schema_size_metrics` adds the following metric:

| Metric name            | Metric type |
| ---------------------- | ----------- |
| mysql.info.schema.size | GAUGE       |

### Events

The MySQL check does not include any events.

### Service Checks

**mysql.replication.replica_running**:<br>
Returns `CRITICAL` for a replica that's not running both `Replica_IO_Running` and `Replica_SQL_Running`; `WARNING` if one of the two is not running; Returns `OK` otherwise. See [this][16] for more details.

**mysql.replication.slave_running**:<br>
Deprecated in favor of `mysql.replication.replica_running`. Returns `CRITICAL` for a replica that's not running both `Replica_IO_Running` and `Replica_SQL_Running`; `WARNING` if one of the two is not running; Returns `OK` otherwise. See [this][16] for more details.

**mysql.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to MySQL to collect metrics, otherwise returns `OK`.

## Troubleshooting

- [Connection Issues with the SQL Server Integration][17]
- [MySQL Localhost Error - Localhost VS 127.0.0.1][18]
- [Can I use a named instance in the SQL Server integration?][19]
- [Can I set up the dd-agent MySQL check on my Google CloudSQL?][20]
- [How to collect metrics from custom MySQL queries][21]
- [Can I collect SQL Server performance metrics beyond what is available in the sys.dm_os_performance_counters table? Try WMI][22]
- [How can I collect more metrics from my SQL Server integration?][23]
- [Database user lacks privileges][24]
- [How to collect metrics with a SQL Stored Procedure?][25]

## Further Reading

Read our [series of blog posts][26] about monitoring MySQL with Datadog.

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mysql/images/mysql-dash-dd.png
[2]: https://mariadb.org
[3]: https://mariadb.com/kb/en/library/mariadb-vs-mysql-compatibility
[4]: https://app.datadoghq.com/account/settings#agent
[5]: https://dev.mysql.com/doc/refman/8.0/en/creating-accounts.html
[6]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[7]: https://github.com/DataDog/integrations-core/blob/master/mysql/datadog_checks/mysql/data/conf.yaml.example
[8]: https://dev.mysql.com/doc/refman/5.7/en/performance-schema-quick-start.html
[9]: https://github.com/DataDog/integrations-core/blob/master/mysql/datadog_checks/mysql/data/conf.yaml.example
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[11]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[12]: https://docs.datadoghq.com/agent/faq/template_variables/
[13]: https://docs.datadoghq.com/agent/kubernetes/log/
[14]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[15]: https://github.com/DataDog/integrations-core/blob/master/mysql/metadata.csv
[16]: https://github.com/DataDog/integrations-core/blob/master/mysql/assets/SERVICE_CHECK_CLARIFICATION.md
[17]: https://docs.datadoghq.com/integrations/faq/connection-issues-with-the-sql-server-integration/
[18]: https://docs.datadoghq.com/integrations/faq/mysql-localhost-error-localhost-vs-127-0-0-1/
[19]: https://docs.datadoghq.com/integrations/faq/can-i-use-a-named-instance-in-the-sql-server-integration/
[20]: https://docs.datadoghq.com/integrations/faq/can-i-set-up-the-dd-agent-mysql-check-on-my-google-cloudsql/
[21]: https://docs.datadoghq.com/integrations/faq/how-to-collect-metrics-from-custom-mysql-queries/
[22]: https://docs.datadoghq.com/integrations/faq/can-i-collect-sql-server-performance-metrics-beyond-what-is-available-in-the-sys-dm-os-performance-counters-table-try-wmi/
[23]: https://docs.datadoghq.com/integrations/faq/how-can-i-collect-more-metrics-from-my-sql-server-integration/
[24]: https://docs.datadoghq.com/integrations/faq/database-user-lacks-privileges/
[25]: https://docs.datadoghq.com/integrations/guide/collect-sql-server-custom-metrics/#collecting-metrics-from-a-custom-procedure
[26]: https://www.datadoghq.com/blog/monitoring-mysql-performance-metrics
[27]: https://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[28]: https://docs.datadoghq.com/agent/faq/template_variables/
[29]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#installation
[30]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[31]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[32]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[33]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[34]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[35]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=daemonset#configuration
[36]: https://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[37]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux
# TODO: fix
[27]: https://app.datadoghq.com/databases
[28]: https://dev.mysql.com/doc/refman/8.0/en/performance-schema-quick-start.html
[29]: https://dev.mysql.com/doc/refman/8.0/en/performance-schema-options.html
[30]: https://dev.mysql.com/doc/refman/8.0/en/performance-schema.html
[31]: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithParamGroups.html
[32]: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_WorkingWithParamGroups.html
