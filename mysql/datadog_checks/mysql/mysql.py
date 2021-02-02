# (C) Datadog, Inc. 2013-present
# (C) Patrick Galbraith <patg@patg.net> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

import traceback
from collections import defaultdict
from contextlib import closing, contextmanager

import pymysql
from six import PY3, iteritems, itervalues

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.db import QueryManager

from .collection_utils import collect_all_scalars, collect_scalar, collect_string, collect_type
from .config import MySQLConfig
from .const import (
    BINLOG_VARS,
    COUNT,
    GALERA_VARS,
    GAUGE,
    INNODB_VARS,
    MONOTONIC,
    OPTIONAL_STATUS_VARS,
    OPTIONAL_STATUS_VARS_5_6_6,
    PERFORMANCE_VARS,
    PROC_NAME,
    RATE,
    REPLICA_VARS,
    SCHEMA_VARS,
    STATUS_VARS,
    SYNTHETIC_VARS,
    VARIABLES_VARS,
)
from .innodb_metrics import InnoDBMetrics
from .queries import (
    SQL_95TH_PERCENTILE,
    SQL_AVG_QUERY_RUN_TIME,
    SQL_INNODB_ENGINES,
    SQL_PROCESS_LIST,
    SQL_QUERY_SCHEMA_SIZE,
    SQL_WORKER_THREADS,
)
from .statements import MySQLStatementMetrics
from .version_utils import get_version

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


if PY3:
    long = int


class MySql(AgentCheck):
    SERVICE_CHECK_NAME = 'mysql.can_connect'
    SLAVE_SERVICE_CHECK_NAME = 'mysql.replication.slave_running'
    DEFAULT_MAX_CUSTOM_QUERIES = 20

    def __init__(self, name, init_config, instances):
        super(MySql, self).__init__(name, init_config, instances)
        self.qcache_stats = {}
        self.version = None
        self.config = MySQLConfig(self.instance)

        # Create a new connection on every check run
        self._conn = None

        self._query_manager = QueryManager(self, self.execute_query_raw, queries=[], tags=self.config.tags)
        self._statement_metrics = MySQLStatementMetrics(self.config)
        self.check_initializations.append(self._query_manager.compile_queries)
        self.innodb_stats = InnoDBMetrics()
        self.check_initializations.append(self.config.configuration_checks)

    def execute_query_raw(self, query):
        with closing(self._conn.cursor(pymysql.cursors.SSCursor)) as cursor:
            cursor.execute(query)
            for row in cursor.fetchall_unbuffered():
                yield row

    @AgentCheck.metadata_entrypoint
    def _send_metadata(self):
        self.set_metadata('version', self.version.version + '+' + self.version.build)
        self.set_metadata('flavor', self.version.flavor)

    @classmethod
    def get_library_versions(cls):
        return {'pymysql': pymysql.__version__}

    def check(self, _):
        self._set_qcache_stats()
        with self._connect() as db:
            try:
                self._conn = db

                # version collection
                self.version = get_version(db)
                self._send_metadata()

                # Metric collection
                self._collect_metrics(db)
                self._collect_system_metrics(self.config.host, db, self.config.tags)
                if self.config.deep_database_monitoring:
                    self._collect_statement_metrics(db, self.config.tags)

                # keeping track of these:
                self._put_qcache_stats()

                # Custom queries
                self._query_manager.execute()

            except Exception as e:
                self.log.exception("error!")
                raise e
            finally:
                self._conn = None

    def _set_qcache_stats(self):
        host_key = self._get_host_key()
        qcache_st = self.qcache_stats.get(host_key, (None, None, None))

        self._qcache_hits = qcache_st[0]
        self._qcache_inserts = qcache_st[1]
        self._qcache_not_cached = qcache_st[2]

    def _put_qcache_stats(self):
        host_key = self._get_host_key()
        self.qcache_stats[host_key] = (self._qcache_hits, self._qcache_inserts, self._qcache_not_cached)

    def _get_host_key(self):
        if self.config.defaults_file:
            return self.config.defaults_file

        hostkey = self.config.host
        if self.config.mysql_sock:
            hostkey = "{0}:{1}".format(hostkey, self.config.mysql_sock)
        elif self.config.port:
            hostkey = "{0}:{1}".format(hostkey, self.config.port)

        return hostkey

    def _get_connection_args(self):
        ssl = dict(self.config.ssl) if self.config.ssl else None
        connection_args = {
            'ssl': ssl,
            'connect_timeout': self.config.connect_timeout,
        }
        if self.config.charset:
            connection_args['charset'] = self.config.charset

        if self.config.defaults_file != '':
            connection_args['read_default_file'] = self.config.defaults_file
            return connection_args

        connection_args.update({'user': self.config.user, 'passwd': self.config.password})
        if self.config.mysql_sock != '':
            self.service_check_tags = [
                'server:{0}'.format(self.config.mysql_sock),
                'port:unix_socket',
            ] + self.config.tags
            connection_args.update({'unix_socket': self.config.mysql_sock})
        else:
            connection_args.update({'host': self.config.host})

        if self.config.port:
            connection_args.update({'port': self.config.port})
        return connection_args

    @contextmanager
    def _connect(self):
        service_check_tags = [
            'server:{0}'.format((self.config.mysql_sock if self.config.mysql_sock != '' else self.config.host)),
            'port:{}'.format(self.config.port if self.config.port else 'unix_socket'),
        ] + self.config.tags
        db = None
        try:
            connect_args = self._get_connection_args()
            db = pymysql.connect(**connect_args)
            self.log.debug("Connected to MySQL")
            self.service_check_tags = list(set(service_check_tags))
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)
            yield db
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags)
            raise
        finally:
            if db:
                db.close()

    def _collect_metrics(self, db):

        # Get aggregate of all VARS we want to collect
        metrics = STATUS_VARS

        # collect results from db
        results = self._get_stats_from_status(db)
        results.update(self._get_stats_from_variables(db))

        if not is_affirmative(
            self.config.options.get('disable_innodb_metrics', False)
        ) and self._is_innodb_engine_enabled(db):
            results.update(self.innodb_stats.get_stats_from_innodb_status(db))
            self.innodb_stats.process_innodb_stats(results, self.config.options, metrics)

        # Binary log statistics
        if self._get_variable_enabled(results, 'log_bin'):
            results['Binlog_space_usage_bytes'] = self._get_binary_log_stats(db)

        # Compute key cache utilization metric
        key_blocks_unused = collect_scalar('Key_blocks_unused', results)
        key_cache_block_size = collect_scalar('key_cache_block_size', results)
        key_buffer_size = collect_scalar('key_buffer_size', results)
        results['Key_buffer_size'] = key_buffer_size

        try:
            # can be null if the unit is missing in the user config (4 instead of 4G for eg.)
            if key_buffer_size != 0:
                key_cache_utilization = 1 - ((key_blocks_unused * key_cache_block_size) / key_buffer_size)
                results['Key_cache_utilization'] = key_cache_utilization

            results['Key_buffer_bytes_used'] = collect_scalar('Key_blocks_used', results) * key_cache_block_size
            results['Key_buffer_bytes_unflushed'] = (
                collect_scalar('Key_blocks_not_flushed', results) * key_cache_block_size
            )
        except TypeError as e:
            self.log.error("Not all Key metrics are available, unable to compute: %s", e)

        metrics.update(VARIABLES_VARS)
        metrics.update(INNODB_VARS)
        metrics.update(BINLOG_VARS)

        if is_affirmative(self.config.options.get('extra_status_metrics', False)):
            self.log.debug("Collecting Extra Status Metrics")
            metrics.update(OPTIONAL_STATUS_VARS)

            if self.version.version_compatible((5, 6, 6)):
                metrics.update(OPTIONAL_STATUS_VARS_5_6_6)

        if is_affirmative(self.config.options.get('galera_cluster', False)):
            # already in result-set after 'SHOW STATUS' just add vars to collect
            self.log.debug("Collecting Galera Metrics.")
            metrics.update(GALERA_VARS)

        performance_schema_enabled = self._get_variable_enabled(results, 'performance_schema')
        above_560 = self.version.version_compatible((5, 6, 0))
        if (
            is_affirmative(self.config.options.get('extra_performance_metrics', False))
            and above_560
            and performance_schema_enabled
        ):
            # report avg query response time per schema to Datadog
            results['perf_digest_95th_percentile_avg_us'] = self._get_query_exec_time_95th_us(db)
            results['query_run_time_avg'] = self._query_exec_time_per_schema(db)
            metrics.update(PERFORMANCE_VARS)

        if is_affirmative(self.config.options.get('schema_size_metrics', False)):
            # report avg query response time per schema to Datadog
            results['information_schema_size'] = self._query_size_per_schema(db)
            metrics.update(SCHEMA_VARS)

        if is_affirmative(self.config.options.get('replication', False)):
            replication_metrics = self._collect_replication_metrics(db, results, above_560)
            metrics.update(replication_metrics)
            self._check_replication_status(results)

        # "synthetic" metrics
        metrics.update(SYNTHETIC_VARS)
        self._compute_synthetic_results(results)

        # remove uncomputed metrics
        for k in SYNTHETIC_VARS:
            if k not in results:
                metrics.pop(k, None)

        # add duped metrics - reporting some as both rate and gauge
        dupes = [
            ('Table_locks_waited', 'Table_locks_waited_rate'),
            ('Table_locks_immediate', 'Table_locks_immediate_rate'),
        ]
        for src, dst in dupes:
            if src in results:
                results[dst] = results[src]

        self._submit_metrics(metrics, results, self.config.tags)

        # Collect custom query metrics
        # Max of 20 queries allowed
        if isinstance(self.config.queries, list):
            for check in self.config.queries[: self.config.max_custom_queries]:
                total_tags = self.config.tags + check.get('tags', [])
                self._collect_dict(
                    check['type'], {check['field']: check['metric']}, check['query'], db, tags=total_tags
                )

            if len(self.config.queries) > self.config.max_custom_queries:
                self.warning(
                    "Maximum number (%s) of custom queries reached.  Skipping the rest.", self.config.max_custom_queries
                )

    def _collect_replication_metrics(self, db, results, above_560):
        # Get replica stats
        is_mariadb = self.version.flavor == "MariaDB"
        replication_channel = self.config.options.get('replication_channel')
        results.update(self._get_replica_stats(db, is_mariadb, replication_channel))
        nonblocking = is_affirmative(self.config.options.get('replication_non_blocking_status', False))
        results.update(self._get_slave_status(db, above_560, nonblocking))
        return REPLICA_VARS

    def _check_replication_status(self, results):
        # get slave running form global status page
        slave_running_status = AgentCheck.UNKNOWN
        # Slave_IO_Running: Whether the I/O thread for reading the source's binary log is running.
        # You want this to be Yes unless you have not yet started replication or have explicitly stopped it.
        slave_io_running = collect_type('Slave_IO_Running', results, dict)
        # Slave_SQL_Running: Whether the SQL thread for executing events in the relay log is running.
        slave_sql_running = collect_type('Slave_SQL_Running', results, dict)
        if slave_io_running:
            slave_io_running = any(v.lower().strip() == 'yes' for v in itervalues(slave_io_running))
        if slave_sql_running:
            slave_sql_running = any(v.lower().strip() == 'yes' for v in itervalues(slave_sql_running))
        binlog_running = results.get('Binlog_enabled', False)
        # slaves will only be collected iff user has PROCESS privileges.
        slaves = collect_scalar('Slaves_connected', results)

        if not (slave_io_running is None and slave_sql_running is None):
            if not slave_io_running and not slave_sql_running:
                self.log.debug("Slave_IO_Running and Slave_SQL_Running are not ok")
                slave_running_status = AgentCheck.CRITICAL
            elif not slave_io_running or not slave_sql_running:
                self.log.debug("Either Slave_IO_Running or Slave_SQL_Running are not ok")
                slave_running_status = AgentCheck.WARNING

        if slave_running_status == AgentCheck.UNKNOWN:
            if self._is_master(slaves, results):  # master
                if slaves > 0 and binlog_running:
                    self.log.debug("Host is master, there are replicas and binlog is running")
                    slave_running_status = AgentCheck.OK
                else:
                    slave_running_status = AgentCheck.WARNING
            else:  # replica (or standalone)
                if not (slave_io_running is None and slave_sql_running is None):
                    if slave_io_running and slave_sql_running:
                        self.log.debug("Slave_IO_Running and Slave_SQL_Running are ok")
                        slave_running_status = AgentCheck.OK

        # deprecated in favor of service_check("mysql.replication.slave_running")
        self.gauge(
            self.SLAVE_SERVICE_CHECK_NAME, 1 if slave_running_status == AgentCheck.OK else 0, tags=self.config.tags
        )
        self.service_check(self.SLAVE_SERVICE_CHECK_NAME, slave_running_status, tags=self.service_check_tags)

    def _collect_statement_metrics(self, db, tags):
        tags = self.service_check_tags + tags
        metrics = self._statement_metrics.collect_per_statement_metrics(db)
        for metric_name, metric_value, metric_tags in metrics:
            self.count(metric_name, metric_value, tags=list(set(tags + metric_tags)))

    def _is_master(self, slaves, results):
        # master uuid only collected in slaves
        master_host = collect_string('Master_Host', results)
        if slaves > 0 or not master_host:
            return True

        return False

    def _submit_metrics(self, variables, db_results, tags):
        for variable, metric in iteritems(variables):
            metric_name, metric_type = metric
            for tag, value in collect_all_scalars(variable, db_results):
                metric_tags = list(tags)
                if tag:
                    metric_tags.append(tag)
                if value is not None:
                    if metric_type == RATE:
                        self.rate(metric_name, value, tags=metric_tags)
                    elif metric_type == GAUGE:
                        self.gauge(metric_name, value, tags=metric_tags)
                    elif metric_type == COUNT:
                        self.count(metric_name, value, tags=metric_tags)
                    elif metric_type == MONOTONIC:
                        self.monotonic_count(metric_name, value, tags=metric_tags)

    def _collect_dict(self, metric_type, field_metric_map, query, db, tags):
        """
        Query status and get a dictionary back.
        Extract each field out of the dictionary
        and stuff it in the corresponding metric.

        query: show status...
        field_metric_map: {"Seconds_behind_master": "mysqlSecondsBehindMaster"}
        """
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                if result is not None:
                    for field, metric in list(iteritems(field_metric_map)):
                        # Find the column name in the cursor description to identify the column index
                        # http://www.python.org/dev/peps/pep-0249/
                        # cursor.description is a tuple of (column_name, ..., ...)
                        try:
                            col_idx = [d[0].lower() for d in cursor.description].index(field.lower())
                            self.log.debug("Collecting metric: %s", metric)
                            if result[col_idx] is not None:
                                self.log.debug("Collecting done, value %s", result[col_idx])
                                if metric_type == GAUGE:
                                    self.gauge(metric, float(result[col_idx]), tags=tags)
                                elif metric_type == RATE:
                                    self.rate(metric, float(result[col_idx]), tags=tags)
                                else:
                                    self.gauge(metric, float(result[col_idx]), tags=tags)
                            else:
                                self.log.debug("Received value is None for index %d", col_idx)
                        except ValueError:
                            self.log.exception("Cannot find %s in the columns %s", field, cursor.description)
        except Exception:
            self.warning("Error while running %s\n%s", query, traceback.format_exc())
            self.log.exception("Error while running %s", query)

    def _collect_system_metrics(self, host, db, tags):
        pid = None
        # The server needs to run locally, accessed by TCP or socket
        if host in ["localhost", "127.0.0.1", "0.0.0.0"] or db.port == long(0):
            pid = self._get_server_pid(db)

        if pid:
            self.log.debug("System metrics for mysql w/ pid: %s", pid)
            # At last, get mysql cpu data out of psutil or procfs

            try:
                ucpu, scpu = None, None
                if PSUTIL_AVAILABLE:
                    proc = psutil.Process(pid)

                    ucpu = proc.cpu_times()[0]
                    scpu = proc.cpu_times()[1]

                if ucpu and scpu:
                    self.rate("mysql.performance.user_time", ucpu, tags=tags)
                    # should really be system_time
                    self.rate("mysql.performance.kernel_time", scpu, tags=tags)
                    self.rate("mysql.performance.cpu_time", ucpu + scpu, tags=tags)

            except Exception:
                self.warning("Error while reading mysql (pid: %s) procfs data\n%s", pid, traceback.format_exc())

    def _get_pid_file_variable(self, db):
        """
        Get the `pid_file` variable
        """
        pid_file = None
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute("SHOW VARIABLES LIKE 'pid_file'")
                pid_file = cursor.fetchone()[1]
        except Exception:
            self.warning("Error while fetching pid_file variable of MySQL.")

        return pid_file

    def _get_server_pid(self, db):
        pid = None

        # Try to get pid from pid file, it can fail for permission reason
        pid_file = self._get_pid_file_variable(db)
        if pid_file is not None:
            self.log.debug("pid file: %s", str(pid_file))
            try:
                with open(pid_file, 'rb') as f:
                    pid = int(f.readline())
            except IOError:
                self.log.debug("Cannot read mysql pid file %s", pid_file)

        # If pid has not been found, read it from ps
        if pid is None and PSUTIL_AVAILABLE:
            for proc in psutil.process_iter():
                try:
                    if proc.name() == PROC_NAME:
                        pid = proc.pid
                except (psutil.AccessDenied, psutil.ZombieProcess, psutil.NoSuchProcess):
                    continue
                except Exception:
                    self.log.exception("Error while fetching mysql pid from psutil")

        return pid

    @classmethod
    def _get_stats_from_status(cls, db):
        with closing(db.cursor()) as cursor:
            cursor.execute("SHOW /*!50002 GLOBAL */ STATUS;")
            results = dict(cursor.fetchall())

            return results

    @classmethod
    def _get_stats_from_variables(cls, db):
        with closing(db.cursor()) as cursor:
            cursor.execute("SHOW GLOBAL VARIABLES;")
            results = dict(cursor.fetchall())

            return results

    def _get_binary_log_stats(self, db):
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute("SHOW BINARY LOGS;")
                cursor_results = cursor.fetchall()
                master_logs = {result[0]: result[1] for result in cursor_results}

                binary_log_space = 0
                for value in itervalues(master_logs):
                    binary_log_space += value

                return binary_log_space
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Privileges error accessing the BINARY LOGS (must grant REPLICATION CLIENT): %s", e)
            return None

    def _is_innodb_engine_enabled(self, db):
        # Whether InnoDB engine is available or not can be found out either
        # from the output of SHOW ENGINES or from information_schema.ENGINES
        # table. Later is choosen because that involves no string parsing.
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(SQL_INNODB_ENGINES)
                return cursor.rowcount > 0

        except (pymysql.err.InternalError, pymysql.err.OperationalError, pymysql.err.NotSupportedError) as e:
            self.warning("Possibly innodb stats unavailable - error querying engines table: %s", e)
            return False

    def _get_replica_stats(self, db, is_mariadb, replication_channel):
        replica_results = defaultdict(dict)
        try:
            with closing(db.cursor(pymysql.cursors.DictCursor)) as cursor:
                if is_mariadb and replication_channel:
                    cursor.execute("SET @@default_master_connection = '{0}';".format(replication_channel))
                    cursor.execute("SHOW SLAVE STATUS;")
                elif replication_channel:
                    cursor.execute("SHOW SLAVE STATUS FOR CHANNEL '{0}';".format(replication_channel))
                else:
                    cursor.execute("SHOW SLAVE STATUS;")

                results = cursor.fetchall()
                self.log.debug("Getting replication status: %s", results)
                for slave_result in results:
                    # MySQL <5.7 does not have Channel_Name.
                    # For MySQL >=5.7 'Channel_Name' is set to an empty string by default
                    channel = replication_channel or slave_result.get('Channel_Name') or 'default'
                    for key, value in iteritems(slave_result):
                        if value is not None:
                            replica_results[key]['channel:{0}'.format(channel)] = value
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            errno, msg = e.args
            if errno == 1617 and msg == "There is no master connection '{0}'".format(replication_channel):
                # MariaDB complains when you try to get slave status with a
                # connection name on the master, without connection name it
                # responds an empty string as expected.
                # Mysql behaves the same with or without connection name.
                pass
            else:
                self.warning("Privileges error getting replication status (must grant REPLICATION CLIENT): %s", e)

        try:
            with closing(db.cursor(pymysql.cursors.DictCursor)) as cursor:
                cursor.execute("SHOW MASTER STATUS;")
                binlog_results = cursor.fetchone()
                if binlog_results:
                    replica_results.update({'Binlog_enabled': True})
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Privileges error getting binlog information (must grant REPLICATION CLIENT): %s", e)

        return replica_results

    def _get_slave_status(self, db, above_560, nonblocking):
        """
        Retrieve the slaves' statuses using:
        1. The `performance_schema.threads` table. Non-blocking, requires version > 5.6.0
        2. The `information_schema.processlist` table. Blocking
        """
        try:
            with closing(db.cursor()) as cursor:
                if above_560 and nonblocking:
                    # Query `performance_schema.threads` instead of `
                    # information_schema.processlist` to avoid mutex impact on performance.
                    cursor.execute(SQL_WORKER_THREADS)
                else:
                    cursor.execute(SQL_PROCESS_LIST)
                slave_results = cursor.fetchall()
                slaves = 0
                for _ in slave_results:
                    slaves += 1

                return {'Slaves_connected': slaves}

        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Privileges error accessing the process tables (must grant PROCESS): %s", e)
            return {}

    @classmethod
    def _are_values_numeric(cls, array):
        return all(v.isdigit() for v in array)

    def _get_variable_enabled(self, results, var):
        enabled = collect_string(var, results)
        return enabled and enabled.lower().strip() == 'on'

    def _get_query_exec_time_95th_us(self, db):
        # Fetches the 95th percentile query execution time and returns the value
        # in microseconds
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(SQL_95TH_PERCENTILE)

                if cursor.rowcount < 1:
                    self.warning(
                        "Failed to fetch records from the perf schema \
                                 'events_statements_summary_by_digest' table."
                    )
                    return None

                row = cursor.fetchone()
                query_exec_time_95th_per = row[0]

                return query_exec_time_95th_per
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("95th percentile performance metrics unavailable at this time: %s", e)
            return None

    def _query_exec_time_per_schema(self, db):
        # Fetches the avg query execution time per schema and returns the
        # value in microseconds
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(SQL_AVG_QUERY_RUN_TIME)

                if cursor.rowcount < 1:
                    self.warning(
                        "Failed to fetch records from the perf schema \
                                 'events_statements_summary_by_digest' table."
                    )
                    return None

                schema_query_avg_run_time = {}
                for row in cursor.fetchall():
                    schema_name = str(row[0])
                    avg_us = long(row[1])

                    # set the tag as the dictionary key
                    schema_query_avg_run_time["schema:{0}".format(schema_name)] = avg_us

                return schema_query_avg_run_time
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Avg exec time performance metrics unavailable at this time: %s", e)
            return None

    def _query_size_per_schema(self, db):
        # Fetches the avg query execution time per schema and returns the
        # value in microseconds
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(SQL_QUERY_SCHEMA_SIZE)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the information schema 'tables' table.")
                    return None

                schema_size = {}
                for row in cursor.fetchall():
                    schema_name = str(row[0])
                    size = long(row[1])

                    # set the tag as the dictionary key
                    schema_size["schema:{0}".format(schema_name)] = size

                return schema_size
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Avg exec time performance metrics unavailable at this time: %s", e)

        return {}

    def _compute_synthetic_results(self, results):
        if ('Qcache_hits' in results) and ('Qcache_inserts' in results) and ('Qcache_not_cached' in results):
            if not int(results['Qcache_hits']):
                results['Qcache_utilization'] = 0
            else:
                results['Qcache_utilization'] = (
                    float(results['Qcache_hits'])
                    / (int(results['Qcache_inserts']) + int(results['Qcache_not_cached']) + int(results['Qcache_hits']))
                    * 100
                )

            if all(v is not None for v in (self._qcache_hits, self._qcache_inserts, self._qcache_not_cached)):
                if not (int(results['Qcache_hits']) - self._qcache_hits):
                    results['Qcache_instant_utilization'] = 0
                else:
                    top = float(results['Qcache_hits']) - self._qcache_hits
                    bottom = (
                        (int(results['Qcache_inserts']) - self._qcache_inserts)
                        + (int(results['Qcache_not_cached']) - self._qcache_not_cached)
                        + (int(results['Qcache_hits']) - self._qcache_hits)
                    )
                    results['Qcache_instant_utilization'] = (top / bottom) * 100

            # update all three, or none - for consistent samples.
            self._qcache_hits = int(results['Qcache_hits'])
            self._qcache_inserts = int(results['Qcache_inserts'])
            self._qcache_not_cached = int(results['Qcache_not_cached'])
