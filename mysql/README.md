# MySQL check

![MySQL Dashboard][1]

## Overview

The MySQL integration tracks the performance of your MySQL instances. It collects metrics related to throughput, connections, errors, and InnoDB metrics.

Enable [Database Monitoring][32] (DBM) for enhanced insights into query performance and database health. In addition to the standard integration, Datadog DBM provides query-level metrics, live and historical query snapshots, wait event analysis, database load, and query explain plans.

## Setup

<div class="alert alert-info">This page describes the MySQL Agent standard integration. If you are looking for the Database Monitoring product for MySQL, see <a href="https://docs.datadoghq.com/database_monitoring" target="_blank">Datadog Database Monitoring</a>.</div>

### Installation

The MySQL check is included in the [Datadog Agent][4] package. No additional installation is needed on your MySQL server.

#### Prepare MySQL

**Note**: To install Database Monitoring for MySQL, select your hosting solution in the [Database Monitoring documentation][33] for instructions.

Proceed with the following steps in this guide only if you are installing the standard integration alone.

On each MySQL server, create a database user for the Datadog Agent.

The following instructions grant the Agent permission to login from any host using `datadog@'%'`. You can restrict the `datadog` user to be allowed to login only from localhost by using `datadog@'localhost'`. See [MySQL Adding Accounts, Assigning Privileges, and Dropping Accounts][5] for more info.

Create the `datadog` user with the following command:

```shell
mysql> CREATE USER 'datadog'@'%' IDENTIFIED BY '<UNIQUEPASSWORD>';
Query OK, 0 rows affected (0.00 sec)
```

Verify the user was created successfully using the following commands - replace `<UNIQUEPASSWORD>` with the password you created above:

```shell
mysql -u datadog --password=<UNIQUEPASSWORD> -e "show status" | \
grep Uptime && echo -e "\033[0;32mMySQL user - OK\033[0m" || \
echo -e "\033[0;31mCannot connect to MySQL\033[0m"
```

The Agent needs a few privileges to collect metrics. Grant the `datadog` user only the following limited privileges.

For MySQL versions 5.6 and 5.7, grant `replication client` and set `max_user_connections` with the following command:

```shell
mysql> GRANT REPLICATION CLIENT ON *.* TO 'datadog'@'%' WITH MAX_USER_CONNECTIONS 5;
Query OK, 0 rows affected, 1 warning (0.00 sec)
```

For MySQL 8.0 or greater, grant `replication client` and set `max_user_connections` with the following commands:

```shell
mysql> GRANT REPLICATION CLIENT ON *.* TO 'datadog'@'%'
Query OK, 0 rows affected (0.00 sec)
mysql> ALTER USER 'datadog'@'%' WITH MAX_USER_CONNECTIONS 5;
Query OK, 0 rows affected (0.00 sec)
```

Grant the `datadog` user the process privilege:

```shell
mysql> GRANT PROCESS ON *.* TO 'datadog'@'%';
Query OK, 0 rows affected (0.00 sec)
```

Verify the replication client. Replace `<UNIQUEPASSWORD>` with the password you created above:

```shell
mysql -u datadog --password=<UNIQUEPASSWORD> -e "show slave status" && \
echo -e "\033[0;32mMySQL grant - OK\033[0m" || \
echo -e "\033[0;31mMissing REPLICATION CLIENT grant\033[0m"
```

If enabled, metrics can be collected from the `performance_schema` database by granting an additional privilege:

```shell
mysql> show databases like 'performance_schema';
+-------------------------------+
| Database (performance_schema) |
+-------------------------------+
| performance_schema            |
+-------------------------------+
1 row in set (0.00 sec)

mysql> GRANT SELECT ON performance_schema.* TO 'datadog'@'%';
Query OK, 0 rows affected (0.00 sec)
```

### Configuration

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Docker](?tab=docker#docker), [Kubernetes](?tab=kubernetes#kubernetes), or [ECS](?tab=ecs#ecs) sections.

**Note**: For a full list of available configuration options, see the [sample mysql.d/conf.yaml][8].

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

Edit the `mysql.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][7] to start collecting your MySQL [metrics](#metric-collection) and [logs](#log-collection).

For a full list of available configuration options, see the [sample `mysql.d/conf.yaml`][8].

##### Metric collection

- Add this configuration block to your `mysql.d/conf.yaml` to collect your [MySQL metrics](#metrics):

  ```yaml
  init_config:

  instances:
    - host: 127.0.0.1
      username: datadog
      password: "<YOUR_CHOSEN_PASSWORD>" # from the CREATE USER step earlier
      port: "<YOUR_MYSQL_PORT>" # e.g. 3306
      options:
        replication: false
        galera_cluster: true
        extra_status_metrics: true
        extra_innodb_metrics: true
        schema_size_metrics: false
        disable_innodb_metrics: false
  ```

**Note**: Wrap your password in single quotes in case a special character is present.

To collect `extra_performance_metrics`, your MySQL server must have `performance_schema` enabled - otherwise set `extra_performance_metrics` to `false`. For more information on `performance_schema`, see [MySQL Performance Schema Quick Start][9].

**Note**: The `datadog` user should be set up in the MySQL integration configuration as `host: 127.0.0.1` instead of `localhost`. Alternatively, you may also use `sock`.

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

    See the [sample mysql.yaml][8] for all available configuration options, including those for custom metrics.

4. [Restart the Agent][10].

<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->
#### Docker

To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integration Templates][11] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["mysql"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"server": "%%host%%", "username": "datadog","password": "<UNIQUEPASSWORD>"}]'
```

See [Autodiscovery template variables][12] for details on using `<UNIQUEPASSWORD>` as an environment variable instead of a label.

#### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker Log Collection][13].

Then, set [Log Integrations][14] as Docker labels:

```yaml
LABEL "com.datadoghq.ad.logs"='[{"source":"mysql","service":"mysql"}]'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][15] as pod annotations on your application container. Alternatively, you can configure templates with a [file, configmap, or key-value store][16].

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mysql
  annotations:
    ad.datadoghq.com/mysql.check_names: '["mysql"]'
    ad.datadoghq.com/mysql.init_configs: '[{}]'
    ad.datadoghq.com/mysql.instances: |
      [
        {
          "server": "%%host%%", 
          "username": "datadog",
          "password": "<UNIQUEPASSWORD>"
        }
      ]
  labels:
    name: mysql
spec:
  containers:
    - name: mysql
```

**Annotations v2** (for Datadog Agent v7.36+)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mysql
  annotations:
    ad.datadoghq.com/mysql.checks: |
      {
        "mysql": {
          "instances": [
            {
              "server": "%%host%%", 
              "username": "datadog",
              "password": "<UNIQUEPASSWORD>"
            }
          ]
        }
      }
  labels:
    name: mysql
spec:
  containers:
    - name: mysql
```

See [Autodiscovery template variables][12] for details on using `<UNIQUEPASSWORD>` as an environment variable instead of a label.

#### Log collection


Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][17].

Then, set [Log Integrations][14] as pod annotations. Alternatively, you can configure this with a [file, configmap, or key-value store][18].

**Annotations v1/v2**

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

Set [Autodiscovery Integrations Templates][11] as Docker labels on your application container:

```json
{
  "containerDefinitions": [{
    "name": "mysql",
    "image": "mysql:latest",
    "dockerLabels": {
      "com.datadoghq.ad.check_names": "[\"mysql\"]",
      "com.datadoghq.ad.init_configs": "[{}]",
      "com.datadoghq.ad.instances": "[{\"server\": \"%%host%%\", \"username\": \"datadog\",\"password\": \"<UNIQUEPASSWORD>\"}]"
    }
  }]
}
```

See [Autodiscovery template variables][12] for details on using `<UNIQUEPASSWORD>` as an environment variable instead of a label.

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [ECS Log Collection][19].

Then, set [Log Integrations][14] as Docker labels:

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

[Run the Agent's status subcommand][20] and look for `mysql` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][21] for a list of metrics provided by this integration.

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
| mysql.innodb.lock_structs                   | GAUGE       |
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

See [service_checks.json][22] for a list of service checks provided by this integration.

## Troubleshooting

- [Connection Issues with the SQL Server Integration][23]
- [MySQL Localhost Error - Localhost VS 127.0.0.1][6]
- [Can I use a named instance in the SQL Server integration?][24]
- [Can I set up the dd-agent MySQL check on my Google CloudSQL?][25]
- [MySQL Custom Queries][26]
- [Use WMI to collect more SQL Server performance metrics][27]
- [How can I collect more metrics from my SQL Server integration?][28]
- [Database user lacks privileges][29]
- [How to collect metrics with a SQL Stored Procedure?][30]

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitoring MySQL performance metrics][31]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mysql/images/mysql-dash-dd.png
[4]: https://app.datadoghq.com/account/settings/agent/latest
[5]: https://dev.mysql.com/doc/refman/8.0/en/creating-accounts.html
[6]: https://docs.datadoghq.com/integrations/faq/mysql-localhost-error-localhost-vs-127-0-0-1/
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[8]: https://github.com/DataDog/integrations-core/blob/master/mysql/datadog_checks/mysql/data/conf.yaml.example
[9]: https://dev.mysql.com/doc/refman/5.7/en/performance-schema-quick-start.html
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[11]: https://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[12]: https://docs.datadoghq.com/agent/faq/template_variables/
[13]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#installation
[14]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#log-integrations
[15]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[16]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[17]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[18]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=daemonset#configuration
[19]: https://docs.datadoghq.com/agent/amazon_ecs/logs/?tab=linux
[20]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[21]: https://github.com/DataDog/integrations-core/blob/master/mysql/metadata.csv
[22]: https://github.com/DataDog/integrations-core/blob/master/mysql/assets/service_checks.json
[23]: https://docs.datadoghq.com/integrations/guide/connection-issues-with-the-sql-server-integration/
[24]: https://docs.datadoghq.com/integrations/faq/can-i-use-a-named-instance-in-the-sql-server-integration/
[25]: https://docs.datadoghq.com/integrations/faq/can-i-set-up-the-dd-agent-mysql-check-on-my-google-cloudsql/
[26]: https://docs.datadoghq.com/integrations/faq/how-to-collect-metrics-from-custom-mysql-queries/
[27]: https://docs.datadoghq.com/integrations/guide/use-wmi-to-collect-more-sql-server-performance-metrics/
[28]: https://docs.datadoghq.com/integrations/faq/how-can-i-collect-more-metrics-from-my-sql-server-integration/
[29]: https://docs.datadoghq.com/integrations/faq/database-user-lacks-privileges/
[30]: https://docs.datadoghq.com/integrations/guide/collect-sql-server-custom-metrics/#collecting-metrics-from-a-custom-procedure
[31]: https://www.datadoghq.com/blog/monitoring-mysql-performance-metrics
[32]: https://docs.datadoghq.com/database_monitoring/
[33]: https://docs.datadoghq.com/database_monitoring/#mysql
