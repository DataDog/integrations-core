# MySQL check

![MySQL Dashboard][30]

## Overview

The Datadog Agent can collect many metrics from MySQL databases, including (but not limited to):

* Query throughput
* Query performance (e.g. average query run time, slow queries, etc.)
* Connections (e.g. currently open connections, aborted connections, errors, etc.)
* InnoDB (e.g. buffer pool metrics, etc.)

You can also create your own metrics using custom SQL queries.

## Setup

### Installation

The MySQL check is included in the [Datadog Agent][13] package, so you don't need to install anything else on your MySQL servers.

### Configuration

Edit `conf.d/mysql.d/conf.yaml` in the root of your [Agent's configuration directory][31] in order to connect the Agent to your MySQL server. You will begin collecting your MySQL [metrics](#metric-collection) and [logs](#log-collection) right away. See the [sample configuration file][16] for all available configuration options.

#### Prepare MySQL

On each MySQL server, create a database user for the Datadog Agent:

```
mysql> CREATE USER 'datadog'@'localhost' IDENTIFIED BY '<UNIQUEPASSWORD>';
Query OK, 0 rows affected (0.00 sec)
```

For mySQL 8.0+ create the `datadog` user with the native password hashing method:

```
mysql> CREATE USER 'datadog'@'localhost' IDENTIFIED WITH mysql_native_password by '<UNIQUEPASSWORD>';
Query OK, 0 rows affected (0.00 sec)
```

Please note that `@'localhost'` is only for local connections - use the hostname/IP of your Agent for remote connections. For more information, see the [MySQL documentation][14].


Verify that the user was created successfully using the following command - replace ```<UNIQUEPASSWORD>``` with the password you created above:

```
mysql -u datadog --password=<UNIQUEPASSWORD> -e "show status" | \
grep Uptime && echo -e "\033[0;32mMySQL user - OK\033[0m" || \
echo -e "\033[0;31mCannot connect to MySQL\033[0m"
mysql -u datadog --password=<UNIQUEPASSWORD> -e "show slave status" && \
echo -e "\033[0;32mMySQL grant - OK\033[0m" || \
echo -e "\033[0;31mMissing REPLICATION CLIENT grant\033[0m"
```

The Agent needs a few privileges in order to collect metrics. Grant the user the following limited privileges ONLY:

```
mysql> GRANT REPLICATION CLIENT ON *.* TO 'datadog'@'localhost' WITH MAX_USER_CONNECTIONS 5;
Query OK, 0 rows affected, 1 warning (0.00 sec)

mysql> GRANT PROCESS ON *.* TO 'datadog'@'localhost';
Query OK, 0 rows affected (0.00 sec)
```

For mySQL 8.0+ set `max_user_connections` with:

```
mysql> ALTER USER 'datadog'@'localhost' WITH MAX_USER_CONNECTIONS 5;
Query OK, 0 rows affected (0.00 sec)
```

If enabled, metrics can be collected from the `performance_schema` database by granting an additional privilege:

```
mysql> show databases like 'performance_schema';
+-------------------------------+
| Database (performance_schema) |
+-------------------------------+
| performance_schema            |
+-------------------------------+
1 row in set (0.00 sec)

mysql> GRANT SELECT ON performance_schema.* TO 'datadog'@'localhost';
Query OK, 0 rows affected (0.00 sec)
```

#### Metric Collection

* Add this configuration block to your `mysql.d/conf.yaml` in order to start gathering your [MySQL metrics](#metrics):

  ```
  init_config:

  instances:
    - server: 127.0.0.1
      user: datadog
      pass: '<YOUR_CHOSEN_PASSWORD>' # from the CREATE USER step earlier
      port: <YOUR_MYSQL_PORT> # e.g. 3306
      options:
          replication: 0
          galera_cluster: 1
          extra_status_metrics: true
          extra_innodb_metrics: true
          extra_performance_metrics: true
          schema_size_metrics: false
          disable_innodb_metrics: false
  ```

**Note**: Wrap your password in single quotes in case a special character is present.

In order to gather `extra_performance_metrics`, your MySQL server must have `performance_schema` enabled - otherwise set `extra_performance_metrics` to `false`. For more information on `performance_schema`, [see the MySQL documentation][15].

Note that the `datadog` user should be set up in the MySQL integration configuration as `host: 127.0.0.1` instead of `localhost`. Alternatively, you may also use `sock`.

See our [sample mysql.yaml][16] for all available configuration options, including those for custom metrics.

[Restart the Agent][17] to start sending MySQL metrics to Datadog.

#### Log Collection

**Available for Agent >6.0**

1. By default MySQL logs everything in `/var/log/syslog` which requires root access to read. In order to make the logs more accessible, follow these steps:

  - Edit `/etc/mysql/conf.d/mysqld_safe_syslog.cnf` and remove or comment the lines.
  - Edit `/etc/mysql/my.cnf` and add following lines to enable general, error, and slow query logs:

    ```
    [mysqld_safe]
    log_error=/var/log/mysql/mysql_error.log
    [mysqld]
    general_log = on
    general_log_file = /var/log/mysql/mysql.log
    log_error=/var/log/mysql/mysql_error.log
    slow_query_log = on
    slow_query_log_file = /var/log/mysql/mysql-slow.log
    long_query_time = 2
    ```

  - Save the file and restart MySQL using following commands:
    `service mysql restart`
  - Make sure the Agent has read access on the `/var/log/mysql` directory and all of the files within. Double-check your logrotate configuration to make sure those files are taken into account and that the permissions are correctly set there as well.
  - In `/etc/logrotate.d/mysql-server` there should be something similar to:

    ```
    /var/log/mysql.log /var/log/mysql/mysql.log /var/log/mysql/mysql-slow.log {
            daily
            rotate 7
            missingok
            create 644 mysql adm
            Compress
    }
    ```

2. Collecting logs is disabled by default in the Datadog Agent, so you need to enable it in `datadog.yaml`:

    ```
    logs_enabled: true
    ```

3. Add this configuration block to your `mysql.d/conf.yaml` file to start collecting your MySQL logs:

    ```
    logs:
        - type: file
          path: /var/log/mysql/mysql_error.log
          source: mysql
          sourcecategory: database
          service: myapplication

        - type: file
          path: /var/log/mysql/mysql-slow.log
          source: mysql
          sourcecategory: database
          service: myapplication

        - type: file
          path: /var/log/mysql/mysql.log
          source: mysql
          sourcecategory: database
          service: myapplication
          # For multiline logs, if they start by the date with the format yyyy-mm-dd uncomment the following processing rule
          # log_processing_rules:
          #   - type: multi_line
          #     name: new_log_start_with_date
          #     pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
    ```
    See our [sample mysql.yaml][16] for all available configuration options, including those for custom metrics.

4. [Restart the Agent][17].

**Learn more about log collection [in the log documentation][18]**

### Validation

[Run the Agent's `status` subcommand][19] and look for `mysql` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][20] for a list of metrics provided by this integration.

The check does not collect all metrics by default. Set the following boolean configuration options to `true` in order to enable the respective metrics:

`extra_status_metrics` adds the following metrics:

|Metric name| Metric type|
|----------|--------|
| mysql.binlog.cache_disk_use | GAUGE |
| mysql.binlog.cache_use | GAUGE |
| mysql.performance.handler_commit | RATE |
| mysql.performance.handler_delete | RATE |
| mysql.performance.handler_prepare | RATE |
| mysql.performance.handler_read_first | RATE |
| mysql.performance.handler_read_key | RATE |
| mysql.performance.handler_read_next | RATE |
| mysql.performance.handler_read_prev | RATE |
| mysql.performance.handler_read_rnd | RATE |
| mysql.performance.handler_read_rnd_next | RATE |
| mysql.performance.handler_rollback | RATE |
| mysql.performance.handler_update | RATE |
| mysql.performance.handler_write | RATE |
| mysql.performance.opened_tables | RATE |
| mysql.performance.qcache_total_blocks | GAUGE |
| mysql.performance.qcache_free_blocks | GAUGE |
| mysql.performance.qcache_free_memory | GAUGE |
| mysql.performance.qcache_not_cached | RATE |
| mysql.performance.qcache_queries_in_cache | GAUGE |
| mysql.performance.select_full_join | RATE |
| mysql.performance.select_full_range_join | RATE |
| mysql.performance.select_range | RATE |
| mysql.performance.select_range_check | RATE |
| mysql.performance.select_scan | RATE |
| mysql.performance.sort_merge_passes | RATE |
| mysql.performance.sort_range | RATE |
| mysql.performance.sort_rows | RATE |
| mysql.performance.sort_scan | RATE |
| mysql.performance.table_locks_immediate | GAUGE |
| mysql.performance.table_locks_immediate.rate | RATE |
| mysql.performance.threads_cached | GAUGE |
| mysql.performance.threads_created | MONOTONIC |

`extra_innodb_metrics` adds the following metrics:

|Metric name| Metric type|
|----------|--------|
| mysql.innodb.active_transactions | GAUGE |
| mysql.innodb.buffer_pool_data | GAUGE |
| mysql.innodb.buffer_pool_pages_data | GAUGE |
| mysql.innodb.buffer_pool_pages_dirty | GAUGE |
| mysql.innodb.buffer_pool_pages_flushed | RATE |
| mysql.innodb.buffer_pool_pages_free | GAUGE |
| mysql.innodb.buffer_pool_pages_total | GAUGE |
| mysql.innodb.buffer_pool_read_ahead | RATE |
| mysql.innodb.buffer_pool_read_ahead_evicted | RATE |
| mysql.innodb.buffer_pool_read_ahead_rnd | GAUGE |
| mysql.innodb.buffer_pool_wait_free | MONOTONIC |
| mysql.innodb.buffer_pool_write_requests | RATE |
| mysql.innodb.checkpoint_age | GAUGE |
| mysql.innodb.current_transactions | GAUGE |
| mysql.innodb.data_fsyncs | RATE |
| mysql.innodb.data_pending_fsyncs | GAUGE |
| mysql.innodb.data_pending_reads | GAUGE |
| mysql.innodb.data_pending_writes | GAUGE |
| mysql.innodb.data_read | RATE |
| mysql.innodb.data_written | RATE |
| mysql.innodb.dblwr_pages_written | RATE |
| mysql.innodb.dblwr_writes | RATE |
| mysql.innodb.hash_index_cells_total | GAUGE |
| mysql.innodb.hash_index_cells_used | GAUGE |
| mysql.innodb.history_list_length | GAUGE |
| mysql.innodb.ibuf_free_list | GAUGE |
| mysql.innodb.ibuf_merged | RATE |
| mysql.innodb.ibuf_merged_delete_marks | RATE |
| mysql.innodb.ibuf_merged_deletes | RATE |
| mysql.innodb.ibuf_merged_inserts | RATE |
| mysql.innodb.ibuf_merges | RATE |
| mysql.innodb.ibuf_segment_size | GAUGE |
| mysql.innodb.ibuf_size | GAUGE |
| mysql.innodb.lock_structs | RATE |
| mysql.innodb.locked_tables | GAUGE |
| mysql.innodb.locked_transactions | GAUGE |
| mysql.innodb.log_waits | RATE |
| mysql.innodb.log_write_requests | RATE |
| mysql.innodb.log_writes | RATE |
| mysql.innodb.lsn_current | RATE |
| mysql.innodb.lsn_flushed | RATE |
| mysql.innodb.lsn_last_checkpoint | RATE |
| mysql.innodb.mem_adaptive_hash | GAUGE |
| mysql.innodb.mem_additional_pool | GAUGE |
| mysql.innodb.mem_dictionary | GAUGE |
| mysql.innodb.mem_file_system | GAUGE |
| mysql.innodb.mem_lock_system | GAUGE |
| mysql.innodb.mem_page_hash | GAUGE |
| mysql.innodb.mem_recovery_system | GAUGE |
| mysql.innodb.mem_thread_hash | GAUGE |
| mysql.innodb.mem_total | GAUGE |
| mysql.innodb.os_file_fsyncs | RATE |
| mysql.innodb.os_file_reads | RATE |
| mysql.innodb.os_file_writes | RATE |
| mysql.innodb.os_log_pending_fsyncs | GAUGE |
| mysql.innodb.os_log_pending_writes | GAUGE |
| mysql.innodb.os_log_written | RATE |
| mysql.innodb.pages_created | RATE |
| mysql.innodb.pages_read | RATE |
| mysql.innodb.pages_written | RATE |
| mysql.innodb.pending_aio_log_ios | GAUGE |
| mysql.innodb.pending_aio_sync_ios | GAUGE |
| mysql.innodb.pending_buffer_pool_flushes | GAUGE |
| mysql.innodb.pending_checkpoint_writes | GAUGE |
| mysql.innodb.pending_ibuf_aio_reads | GAUGE |
| mysql.innodb.pending_log_flushes | GAUGE |
| mysql.innodb.pending_log_writes | GAUGE |
| mysql.innodb.pending_normal_aio_reads | GAUGE |
| mysql.innodb.pending_normal_aio_writes | GAUGE |
| mysql.innodb.queries_inside | GAUGE |
| mysql.innodb.queries_queued | GAUGE |
| mysql.innodb.read_views | GAUGE |
| mysql.innodb.rows_deleted | RATE |
| mysql.innodb.rows_inserted | RATE |
| mysql.innodb.rows_read | RATE |
| mysql.innodb.rows_updated | RATE |
| mysql.innodb.s_lock_os_waits | RATE |
| mysql.innodb.s_lock_spin_rounds | RATE |
| mysql.innodb.s_lock_spin_waits | RATE |
| mysql.innodb.semaphore_wait_time | GAUGE |
| mysql.innodb.semaphore_waits | GAUGE |
| mysql.innodb.tables_in_use | GAUGE |
| mysql.innodb.x_lock_os_waits | RATE |
| mysql.innodb.x_lock_spin_rounds | RATE |
| mysql.innodb.x_lock_spin_waits | RATE |

`extra_performance_metrics` adds the following metrics:

|Metric name| Metric type|
|----------|--------|
| mysql.performance.query_run_time.avg | GAUGE |
| mysql.performance.digest_95th_percentile.avg_us | GAUGE |

`schema_size_metrics` adds the following metric:

|Metric name| Metric type|
|----------|--------|
| mysql.info.schema.size | GAUGE |

### Events

The MySQL check does not include any events.

### Service Checks

`mysql.replication.slave_running`:

Returns CRITICAL for a slave that's not running, otherwise OK.

`mysql.can_connect`:

Returns CRITICAL if the Agent cannot connect to MySQL to collect metrics, otherwise OK.

## Troubleshooting

* [Connection Issues with the SQL Server Integration][21]
* [MySQL Localhost Error - Localhost VS 127.0.0.1][22]
* [Can I use a named instance in the SQL Server integration?][23]
* [Can I set up the dd-agent MySQL check on my Google CloudSQL?][24]
* [How to collect metrics from custom MySQL queries][25]
* [Can I collect SQL Server performance metrics beyond what is available in the sys.dm_os_performance_counters table? Try WMI][26]
* [How can I collect more metrics from my SQL Server integration?][27]
* [Database user lacks privileges][28]
* [How to collect metrics with a SQL Stored Procedure?][32]

## Further Reading
Read our [series of blog posts][29] about monitoring MySQL with Datadog.


[13]: https://app.datadoghq.com/account/settings#agent
[14]: https://dev.mysql.com/doc/refman/5.7/en/adding-users.html
[15]: https://dev.mysql.com/doc/refman/5.7/en/performance-schema-quick-start.html
[16]: https://github.com/DataDog/integrations-core/blob/master/mysql/datadog_checks/mysql/data/conf.yaml.example
[17]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[18]: https://docs.datadoghq.com/logs
[19]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[20]: https://github.com/DataDog/integrations-core/blob/master/mysql/metadata.csv
[21]: https://docs.datadoghq.com/integrations/faq/connection-issues-with-the-sql-server-integration
[22]: https://docs.datadoghq.com/integrations/faq/mysql-localhost-error-localhost-vs-127-0-0-1
[23]: https://docs.datadoghq.com/integrations/faq/can-i-use-a-named-instance-in-the-sql-server-integration
[24]: https://docs.datadoghq.com/integrations/faq/can-i-set-up-the-dd-agent-mysql-check-on-my-google-cloudsql
[25]: https://docs.datadoghq.com/integrations/faq/how-to-collect-metrics-from-custom-mysql-queries
[26]: https://docs.datadoghq.com/integrations/faq/can-i-collect-sql-server-performance-metrics-beyond-what-is-available-in-the-sys-dm-os-performance-counters-table-try-wmi
[27]: https://docs.datadoghq.com/integrations/faq/how-can-i-collect-more-metrics-from-my-sql-server-integration
[28]: https://docs.datadoghq.com/integrations/faq/database-user-lacks-privileges
[29]: https://www.datadoghq.com/blog/monitoring-mysql-performance-metrics/
[30]: https://raw.githubusercontent.com/DataDog/integrations-core/master/mysql/images/mysql-dash-dd.png
[31]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[32]: https://docs.datadoghq.com/integrations/faq/how-to-collect-metrics-with-sql-stored-procedure/
