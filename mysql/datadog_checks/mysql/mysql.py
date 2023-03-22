# (C) Datadog, Inc. 2013-present
# (C) Patrick Galbraith <patg@patg.net> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

import copy
import traceback
from collections import defaultdict
from contextlib import closing, contextmanager
from typing import Any, Dict, List, Optional  # noqa: F401

import pymysql
from six import PY3, iteritems, itervalues

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.db import QueryExecutor, QueryManager
from datadog_checks.base.utils.db.utils import resolve_db_host as agent_host_resolver

from .activity import MySQLActivity
from .collection_utils import collect_all_scalars, collect_scalar, collect_string, collect_type
from .config import MySQLConfig
from .const import (
    BINLOG_VARS,
    COUNT,
    GALERA_VARS,
    GAUGE,
    GROUP_REPLICATION_VARS,
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
    TABLE_ROWS_STATS_VARS,
    TABLE_VARS,
    VARIABLES_VARS,
)
from .innodb_metrics import InnoDBMetrics
from .queries import (
    QUERY_USER_CONNECTIONS,
    SQL_95TH_PERCENTILE,
    SQL_AVG_QUERY_RUN_TIME,
    SQL_GROUP_REPLICATION_MEMBER,
    SQL_GROUP_REPLICATION_METRICS,
    SQL_GROUP_REPLICATION_PLUGIN_STATUS,
    SQL_INNODB_ENGINES,
    SQL_PROCESS_LIST,
    SQL_QUERY_SCHEMA_SIZE,
    SQL_QUERY_SYSTEM_TABLE_SIZE,
    SQL_QUERY_TABLE_ROWS_STATS,
    SQL_QUERY_TABLE_SIZE,
    SQL_REPLICATION_ROLE_AWS_AURORA,
    SQL_SERVER_ID_AWS_AURORA,
    SQL_WORKER_THREADS,
    show_replica_status_query,
)
from .statement_samples import MySQLStatementSamples
from .statements import MySQLStatementMetrics
from .util import DatabaseConfigurationError  # noqa: F401
from .version_utils import get_version

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


if PY3:
    long = int


class MySql(AgentCheck):
    SERVICE_CHECK_NAME = 'mysql.can_connect'
    SLAVE_SERVICE_CHECK_NAME = 'mysql.replication.slave_running'
    REPLICA_SERVICE_CHECK_NAME = 'mysql.replication.replica_running'
    GROUP_REPLICATION_SERVICE_CHECK_NAME = 'mysql.replication.group.status'
    DEFAULT_MAX_CUSTOM_QUERIES = 20

    def __init__(self, name, init_config, instances):
        super(MySql, self).__init__(name, init_config, instances)
        self.qcache_stats = {}
        self.version = None
        self.is_mariadb = None
        self._resolved_hostname = None
        self._agent_hostname = None
        self._is_aurora = None
        self._config = MySQLConfig(self.instance)

        # Create a new connection on every check run
        self._conn = None

        self._query_manager = QueryManager(self, self.execute_query_raw, queries=[])
        self.check_initializations.append(self._query_manager.compile_queries)
        self.innodb_stats = InnoDBMetrics()
        self.check_initializations.append(self._config.configuration_checks)
        self.performance_schema_enabled = None
        self.userstat_enabled = None
        self.events_wait_current_enabled = None
        self._warnings_by_code = {}
        self._statement_metrics = MySQLStatementMetrics(self, self._config, self._get_connection_args())
        self._statement_samples = MySQLStatementSamples(self, self._config, self._get_connection_args())
        self._query_activity = MySQLActivity(self, self._config, self._get_connection_args())

        self._runtime_queries = None

    def execute_query_raw(self, query):
        with closing(self._conn.cursor(pymysql.cursors.SSCursor)) as cursor:
            cursor.execute(query)
            for row in cursor.fetchall_unbuffered():
                yield row

    @AgentCheck.metadata_entrypoint
    def _send_metadata(self):
        self.set_metadata('version', self.version.version + '+' + self.version.build)
        self.set_metadata('flavor', self.version.flavor)
        self.set_metadata('resolved_hostname', self.resolved_hostname)

    @property
    def resolved_hostname(self):
        if self._resolved_hostname is None:
            if self._config.reported_hostname:
                self._resolved_hostname = self._config.reported_hostname
            elif self._config.dbm_enabled or self.disable_generic_tags:
                self._resolved_hostname = self.resolve_db_host()
            else:
                self._resolved_hostname = self.agent_hostname
        return self._resolved_hostname

    @property
    def agent_hostname(self):
        # type: () -> str
        if self._agent_hostname is None:
            self._agent_hostname = datadog_agent.get_hostname()
        return self._agent_hostname

    def _check_database_configuration(self, db):
        self._check_performance_schema_enabled(db)
        self._check_events_wait_current_enabled(db)

    def _check_performance_schema_enabled(self, db):
        if self.performance_schema_enabled is None:
            with closing(db.cursor()) as cursor:
                cursor.execute("SHOW VARIABLES LIKE 'performance_schema'")
                results = dict(cursor.fetchall())
                self.performance_schema_enabled = self._get_variable_enabled(results, 'performance_schema')

        return self.performance_schema_enabled

    def check_userstat_enabled(self, db):
        if self.userstat_enabled is None:
            with closing(db.cursor()) as cursor:
                cursor.execute("SHOW VARIABLES LIKE 'userstat'")
                results = dict(cursor.fetchall())
                self.userstat_enabled = self._get_variable_enabled(results, 'userstat')

        return self.userstat_enabled

    def _check_events_wait_current_enabled(self, db):
        if not self._config.dbm_enabled or not self._config.activity_config.get("enabled", True):
            self.log.debug("skipping _check_events_wait_current_enabled because dbm activity collection is not enabled")
            return
        if not self._check_performance_schema_enabled(db):
            self.log.debug('`performance_schema` is required to enable `events_waits_current`')
            return
        if self.events_wait_current_enabled is None:
            with closing(db.cursor()) as cursor:
                cursor.execute(
                    """\
                    SELECT
                        NAME,
                        ENABLED
                    FROM performance_schema.setup_consumers WHERE NAME = 'events_waits_current'
                    """
                )
                results = dict(cursor.fetchall())
                self.events_wait_current_enabled = self._get_variable_enabled(results, 'events_waits_current')
        return self.events_wait_current_enabled

    def resolve_db_host(self):
        return agent_host_resolver(self._config.host)

    def _get_debug_tags(self):
        return ['agent_hostname:{}'.format(datadog_agent.get_hostname())]

    @classmethod
    def get_library_versions(cls):
        return {'pymysql': pymysql.__version__}

    def check(self, _):
        if self.instance.get('user'):
            self._log_deprecation('_config_renamed', 'user', 'username')

        if self.instance.get('pass'):
            self._log_deprecation('_config_renamed', 'pass', 'password')

        tags = list(self._config.tags)
        self._set_qcache_stats()
        with self._connect() as db:
            try:
                self._conn = db

                # version collection
                self.version = get_version(db)
                self._send_metadata()

                self.is_mariadb = self.version.flavor == "MariaDB"
                if self._get_is_aurora(db):
                    tags = tags + self._get_runtime_aurora_tags(db)

                self._check_database_configuration(db)

                if self._config.table_rows_stats_enabled:
                    self.check_userstat_enabled(db)

                # Metric collection
                if not self._config.only_custom_queries:
                    self._collect_metrics(db, tags=tags)
                    self._collect_system_metrics(self._config.host, db, tags)
                    if self.runtime_queries:
                        self.runtime_queries.execute(extra_tags=tags)

                if self._config.dbm_enabled:
                    dbm_tags = list(set(self.service_check_tags) | set(tags))
                    self._statement_metrics.run_job_loop(dbm_tags)
                    self._statement_samples.run_job_loop(dbm_tags)
                    self._query_activity.run_job_loop(dbm_tags)

                # keeping track of these:
                self._put_qcache_stats()

                # Custom queries
                self._query_manager.execute(extra_tags=tags)

            except Exception as e:
                self.log.exception("error!")
                raise e
            finally:
                self._conn = None
                self._report_warnings()

    def cancel(self):
        self._statement_samples.cancel()
        self._statement_metrics.cancel()
        self._query_activity.cancel()

    def _new_query_executor(self, queries):
        return QueryExecutor(
            self.execute_query_raw,
            self,
            queries=queries,
            hostname=self.resolved_hostname,
        )

    @property
    def runtime_queries(self):
        """
        Initializes runtime queries which depend on outside factors (e.g. permission checks) to load first.
        """
        if self._runtime_queries:
            return self._runtime_queries

        queries = []

        if self.performance_schema_enabled:
            queries.extend([QUERY_USER_CONNECTIONS])

        self._runtime_queries = self._new_query_executor(queries)
        self._runtime_queries.compile_queries()
        self.log.debug("initialized runtime queries")
        return self._runtime_queries

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
        if self._config.defaults_file:
            return self._config.defaults_file

        hostkey = self._config.host
        if self._config.mysql_sock:
            hostkey = "{0}:{1}".format(hostkey, self._config.mysql_sock)
        elif self._config.port:
            hostkey = "{0}:{1}".format(hostkey, self._config.port)

        return hostkey

    def _get_connection_args(self):
        ssl = dict(self._config.ssl) if self._config.ssl else None
        connection_args = {
            'ssl': ssl,
            'connect_timeout': self._config.connect_timeout,
            'autocommit': True,
        }
        if self._config.charset:
            connection_args['charset'] = self._config.charset

        if self._config.defaults_file != '':
            connection_args['read_default_file'] = self._config.defaults_file
            return connection_args

        connection_args.update({'user': self._config.user, 'passwd': self._config.password})
        if self._config.mysql_sock != '':
            self.service_check_tags = self._service_check_tags(self._config.mysql_sock)
            connection_args.update({'unix_socket': self._config.mysql_sock})
        else:
            connection_args.update({'host': self._config.host})

        if self._config.port:
            connection_args.update({'port': self._config.port})
        return connection_args

    def _service_check_tags(self, server=None):
        # type: (Optional[str]) -> List[str]
        if server is None:
            server = self._config.mysql_sock if self._config.mysql_sock != '' else self._config.host
        service_check_tags = [
            'port:{}'.format(self._config.port if self._config.port else 'unix_socket'),
        ] + self._config.tags
        if not self.disable_generic_tags:
            service_check_tags.append('server:{0}'.format(server))
        return service_check_tags

    @contextmanager
    def _connect(self):
        service_check_tags = self._service_check_tags()
        db = None
        try:
            connect_args = self._get_connection_args()
            db = pymysql.connect(**connect_args)
            self.log.debug("Connected to MySQL")
            self.service_check_tags = list(set(service_check_tags))
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags, hostname=self.resolved_hostname
            )
            yield db
        except Exception:
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, hostname=self.resolved_hostname
            )
            raise
        finally:
            if db:
                db.close()

    def _collect_metrics(self, db, tags):

        # Get aggregate of all VARS we want to collect
        metrics = copy.deepcopy(STATUS_VARS)

        # collect results from db
        results = self._get_stats_from_status(db)
        results.update(self._get_stats_from_variables(db))

        if not is_affirmative(
            self._config.options.get('disable_innodb_metrics', False)
        ) and self._is_innodb_engine_enabled(db):
            results.update(self.innodb_stats.get_stats_from_innodb_status(db))
            self.innodb_stats.process_innodb_stats(results, self._config.options, metrics)

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

        if is_affirmative(self._config.options.get('extra_status_metrics', self._config.dbm_enabled)):
            self.log.debug("Collecting Extra Status Metrics")
            metrics.update(OPTIONAL_STATUS_VARS)

            if self.version.version_compatible((5, 6, 6)):
                metrics.update(OPTIONAL_STATUS_VARS_5_6_6)

        if is_affirmative(self._config.options.get('galera_cluster', False)):
            # already in result-set after 'SHOW STATUS' just add vars to collect
            self.log.debug("Collecting Galera Metrics.")
            metrics.update(GALERA_VARS)

        above_560 = self.version.version_compatible((5, 6, 0))
        if (
            is_affirmative(self._config.options.get('extra_performance_metrics', False))
            and above_560
            and self.performance_schema_enabled
        ):
            self.warning(
                "[Deprecated] The `extra_performance_metrics` option will be removed in a future release. "
                "Utilize the `custom_queries` feature if the functionality is needed.",
            )
            results['perf_digest_95th_percentile_avg_us'] = self._get_query_exec_time_95th_us(db)
            results['query_run_time_avg'] = self._query_exec_time_per_schema(db)
            metrics.update(PERFORMANCE_VARS)

        if is_affirmative(self._config.options.get('schema_size_metrics', False)):
            # report avg query response time per schema to Datadog
            results['information_schema_size'] = self._query_size_per_schema(db)
            metrics.update(SCHEMA_VARS)

        if is_affirmative(self._config.options.get('table_rows_stats_metrics', False)) and self.userstat_enabled:
            # report size of tables in MiB to Datadog
            self.log.debug("Collecting Table Row Stats Metrics.")
            (rows_read_total, rows_changed_total) = self._query_rows_stats_per_table(db)
            results['information_table_rows_read_total'] = rows_read_total
            results['information_table_rows_changed_total'] = rows_changed_total
            metrics.update(TABLE_ROWS_STATS_VARS)

        if is_affirmative(self._config.options.get('table_size_metrics', False)):
            # report size of tables in MiB to Datadog
            (table_index_size, table_data_size) = self._query_size_per_table(db)
            results['information_table_index_size'] = table_index_size
            results['information_table_data_size'] = table_data_size
            metrics.update(TABLE_VARS)

        if is_affirmative(self._config.options.get('system_table_size_metrics', False)):
            # report size of tables in MiB to Datadog
            (table_index_size, table_data_size) = self._query_size_per_table(db, system_tables=True)
            results['information_table_index_size'] = table_index_size
            results['information_table_data_size'] = table_data_size
            metrics.update(TABLE_VARS)

        if is_affirmative(self._config.options.get('replication', self._config.dbm_enabled)):
            if self.performance_schema_enabled and self._is_group_replication_active(db):
                self.log.debug('Collecting group replication metrics.')
                self._collect_group_replica_metrics(db, results)
            else:
                replication_metrics = self._collect_replication_metrics(db, results, above_560)
                metrics.update(replication_metrics)
                self._check_replication_status(results)

        if len(self._config.additional_status) > 0:
            additional_status_dict = {}
            for status_dict in self._config.additional_status:
                status_name = status_dict["name"]
                status_metric = status_dict["metric_name"]
                if status_name in metrics.keys():
                    collected_metric = metrics.get(status_name)[0]
                    self.log.debug(
                        "Skipping status variable %s for metric %s as it is already collected by %s",
                        status_name,
                        status_metric,
                        collected_metric,
                    )
                else:
                    additional_status_dict[status_dict["name"]] = (status_dict["metric_name"], status_dict["type"])
            metrics.update(additional_status_dict)

        if len(self._config.additional_variable) > 0:
            additional_variable_dict = {}
            for variable_dict in self._config.additional_variable:
                variable_name = variable_dict["name"]
                variable_metric = variable_dict["metric_name"]
                if variable_name in metrics.keys():
                    collected_metric = metrics.get(variable_name)[0]
                    self.log.debug(
                        "Skipping variable %s for metric %s as it is already collected by %s",
                        variable_name,
                        variable_metric,
                        collected_metric,
                    )
                else:
                    additional_variable_dict[variable_name] = (variable_metric, variable_dict["type"])

            metrics.update(additional_variable_dict)

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

        self._submit_metrics(metrics, results, tags)

        # Collect custom query metrics
        # Max of 20 queries allowed
        if isinstance(self._config.queries, list):
            for check in self._config.queries[: self._config.max_custom_queries]:
                total_tags = tags + check.get('tags', [])
                self._collect_dict(
                    check['type'], {check['field']: check['metric']}, check['query'], db, tags=total_tags
                )

            if len(self._config.queries) > self._config.max_custom_queries:
                self.warning(
                    "Maximum number (%s) of custom queries reached. Skipping the rest.", self._config.max_custom_queries
                )

    def _collect_replication_metrics(self, db, results, above_560):
        # Get replica stats
        replication_channel = self._config.options.get('replication_channel')
        results.update(self._get_replica_stats(db, self.is_mariadb, replication_channel))
        nonblocking = is_affirmative(self._config.options.get('replication_non_blocking_status', False))
        results.update(self._get_replica_status(db, above_560, nonblocking))
        return REPLICA_VARS

    def _collect_group_replica_metrics(self, db, results):
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(SQL_GROUP_REPLICATION_MEMBER)
                replica_results = cursor.fetchone()
                status = self.OK
                additional_tags = []
                if replica_results is None or len(replica_results) < 3:
                    self.log.warning(
                        'Unable to get group replica status, setting mysql.replication.group.status as CRITICAL'
                    )
                    status = self.CRITICAL
                else:
                    status = self.OK if replica_results[1] == 'ONLINE' else self.CRITICAL
                    additional_tags = [
                        'channel_name:{}'.format(replica_results[0]),
                        'member_state:{}'.format(replica_results[1]),
                        'member_role:{}'.format(replica_results[2]),
                    ]
                    self.gauge('mysql.replication.group.member_status', 1, tags=additional_tags + self._config.tags)

                self.service_check(
                    self.GROUP_REPLICATION_SERVICE_CHECK_NAME,
                    status=status,
                    tags=self._service_check_tags() + additional_tags,
                )

                cursor.execute(SQL_GROUP_REPLICATION_METRICS)
                r = cursor.fetchone()

                if r is None:
                    self.log.warning('Unable to get group replication metrics')
                    return {}

                results = {
                    'Transactions_count': r[1],
                    'Transactions_check': r[2],
                    'Conflict_detected': r[3],
                    'Transactions_row_validating': r[4],
                    'Transactions_remote_applier_queue': r[5],
                    'Transactions_remote_applied': r[6],
                    'Transactions_local_proposed': r[7],
                    'Transactions_local_rollback': r[8],
                }
                # Submit metrics now so it's possible to attach `channel_name` tag
                self._submit_metrics(
                    GROUP_REPLICATION_VARS, results, self._config.tags + ['channel_name:{}'.format(r[0])]
                )

                return GROUP_REPLICATION_VARS
        except Exception as e:
            self.warning("Internal error happened during the group replication check: %s", e)
            return {}

    def _check_replication_status(self, results):
        # Replica_IO_Running: Whether the I/O thread for reading the source's binary log is running.
        # You want this to be Yes unless you have not yet started replication or have explicitly stopped it.
        replica_io_running = collect_type('Slave_IO_Running', results, dict)
        if replica_io_running is None:
            replica_io_running = collect_type('Replica_IO_Running', results, dict)
        # Replica_SQL_Running: Whether the SQL thread for executing events in the relay log is running.
        replica_sql_running = collect_type('Slave_SQL_Running', results, dict)
        if replica_sql_running is None:
            replica_sql_running = collect_type('Replica_SQL_Running', results, dict)
        if replica_io_running:
            replica_io_running = any(v.lower().strip() == 'yes' for v in itervalues(replica_io_running))
        if replica_sql_running:
            replica_sql_running = any(v.lower().strip() == 'yes' for v in itervalues(replica_sql_running))
        binlog_running = results.get('Binlog_enabled', False)

        # replicas will only be collected if user has PROCESS privileges.
        replicas = collect_scalar('Slaves_connected', results)
        if replicas is None:
            replicas = collect_scalar('Replicas_connected', results)

        # If the host act as a source
        source_repl_running_status = AgentCheck.UNKNOWN
        if self._is_source_host(replicas, results):
            if replicas > 0 and binlog_running:
                self.log.debug("Host is master, there are replicas and binlog is running")
                source_repl_running_status = AgentCheck.OK
            else:
                source_repl_running_status = AgentCheck.WARNING

            self._submit_replication_status(source_repl_running_status, ['replication_mode:source'])

        # If the host act as a replica
        # A host can be both a source and a replica
        # See https://dev.mysql.com/doc/refman/8.0/en/replication-solutions-performance.html
        # get replica running form global status page
        replica_running_status = AgentCheck.UNKNOWN
        if self._is_replica_host(replicas, results):
            if not (replica_io_running is None and replica_sql_running is None):
                if not replica_io_running and not replica_sql_running:
                    self.log.debug("Replica_IO_Running and Replica_SQL_Running are not ok")
                    replica_running_status = AgentCheck.CRITICAL
                elif not replica_io_running or not replica_sql_running:
                    self.log.debug("Either Replica_IO_Running or Replica_SQL_Running are not ok")
                    replica_running_status = AgentCheck.WARNING
                else:
                    self.log.debug("Replica_IO_Running and Replica_SQL_Running are ok")
                    replica_running_status = AgentCheck.OK

                self._submit_replication_status(replica_running_status, ['replication_mode:replica'])

    def _submit_replication_status(self, status, additional_tags):
        # deprecated in favor of service_check("mysql.replication.slave_running")
        self.gauge(
            name=self.SLAVE_SERVICE_CHECK_NAME,
            value=1 if status == AgentCheck.OK else 0,
            tags=self._config.tags + additional_tags,
            hostname=self.resolved_hostname,
        )
        # deprecated in favor of service_check("mysql.replication.replica_running")
        self.service_check(
            self.SLAVE_SERVICE_CHECK_NAME,
            status,
            tags=self.service_check_tags + additional_tags,
            hostname=self.resolved_hostname,
        )
        self.service_check(
            self.REPLICA_SERVICE_CHECK_NAME,
            status,
            tags=self.service_check_tags + additional_tags,
            hostname=self.resolved_hostname,
        )

    def _is_source_host(self, replicas, results):
        # type: (float, Dict[str, Any]) -> bool
        # master uuid only collected in replicas
        source_host = collect_string('Master_Host', results) or collect_string('Source_Host', results)
        if replicas > 0 or not source_host:
            return True

        return False

    def _is_replica_host(self, replicas, results):
        return collect_string('Master_Host', results) or collect_string('Source_Host', results)

    def _is_group_replication_active(self, db):
        with closing(db.cursor()) as cursor:
            cursor.execute(SQL_GROUP_REPLICATION_PLUGIN_STATUS)
            r = cursor.fetchone()

            # Plugin is installed
            if r is not None and r[0].lower() == 'active':
                self.log.debug('Group replication plugin is detected and active')
                return True
        self.log.debug('Group replication plugin not detected')
        return False

    def _submit_metrics(self, variables, db_results, tags):
        for variable, metric in iteritems(variables):
            if isinstance(metric, list):
                for m in metric:
                    metric_name, metric_type = m
                    self.__submit_metric(metric_name, metric_type, variable, db_results, tags)
            else:
                metric_name, metric_type = metric
                self.__submit_metric(metric_name, metric_type, variable, db_results, tags)

    def __submit_metric(self, metric_name, metric_type, variable, db_results, tags):
        for tag, value in collect_all_scalars(variable, db_results):
            metric_tags = list(tags)
            if tag:
                if "," in tag:
                    t_split = tag.split(",")
                    for t in t_split:
                        metric_tags.append(t)
                else:
                    metric_tags.append(tag)
            if value is not None:
                if metric_type == RATE:
                    self.rate(metric_name, value, tags=metric_tags, hostname=self.resolved_hostname)
                elif metric_type == GAUGE:
                    self.gauge(metric_name, value, tags=metric_tags, hostname=self.resolved_hostname)
                elif metric_type == COUNT:
                    self.count(metric_name, value, tags=metric_tags, hostname=self.resolved_hostname)
                elif metric_type == MONOTONIC:
                    self.monotonic_count(metric_name, value, tags=metric_tags, hostname=self.resolved_hostname)

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
                                    self.gauge(
                                        metric, float(result[col_idx]), tags=tags, hostname=self.resolved_hostname
                                    )
                                elif metric_type == RATE:
                                    self.rate(
                                        metric, float(result[col_idx]), tags=tags, hostname=self.resolved_hostname
                                    )
                                else:
                                    self.gauge(
                                        metric, float(result[col_idx]), tags=tags, hostname=self.resolved_hostname
                                    )
                            else:
                                self.log.debug("Received value is None for index %d", col_idx)
                        except ValueError:
                            self.log.exception("Cannot find %s in the columns %s", field, cursor.description)
        except Exception:
            self.warning("Error while running %s\n%s", query, traceback.format_exc())
            self.log.exception("Error while running %s", query)

    def _get_runtime_aurora_tags(self, db):
        runtime_tags = []

        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(SQL_REPLICATION_ROLE_AWS_AURORA)
                replication_role = cursor.fetchone()[0]

                if replication_role in {'writer', 'reader'}:
                    runtime_tags.append('replication_role:' + replication_role)
        except Exception:
            self.log.warning("Error occurred while fetching Aurora runtime tags: %s", traceback.format_exc())

        return runtime_tags

    def _collect_system_metrics(self, host, db, tags):
        pid = None
        # The server needs to run locally, accessed by TCP or socket
        if host in ["localhost", "127.0.0.1", "0.0.0.0"] or db.port == long(0):
            pid = self._get_server_pid(db)

        if pid:
            self.log.debug("System metrics for mysql w/ pid: %s", pid)
            # At last, get mysql cpu data out of psutil or procfs

            try:
                if PSUTIL_AVAILABLE:
                    self.log.debug("psutil is available, attempting to collect mysql.performance.* metrics")
                    proc = psutil.Process(pid)

                    ucpu = proc.cpu_times()[0]
                    scpu = proc.cpu_times()[1]

                    if ucpu and scpu:
                        self.rate("mysql.performance.user_time", ucpu, tags=tags, hostname=self.resolved_hostname)
                        # should really be system_time
                        self.rate("mysql.performance.kernel_time", scpu, tags=tags, hostname=self.resolved_hostname)
                        self.rate("mysql.performance.cpu_time", ucpu + scpu, tags=tags, hostname=self.resolved_hostname)
                else:
                    self.log.debug("psutil is not available, will not collect mysql.performance.* metrics")
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

        process_name = [PROC_NAME]
        if self.is_mariadb and self.version.version_compatible((10, 5, 0)):
            process_name.append("mariadbd")

        # If pid has not been found, read it from ps
        if pid is None and PSUTIL_AVAILABLE:
            for proc in psutil.process_iter():
                try:
                    if proc.name() in process_name:
                        pid = proc.pid
                except (psutil.AccessDenied, psutil.ZombieProcess, psutil.NoSuchProcess):
                    continue
                except Exception:
                    self.log.exception("Error while fetching mysql pid from psutil")

        return pid

    def _get_is_aurora(self, db):
        """
        Tests if the instance is an AWS Aurora database and caches the result.
        """
        if self._is_aurora is not None:
            return self._is_aurora

        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(SQL_SERVER_ID_AWS_AURORA)
                if len(cursor.fetchall()) > 0:
                    self._is_aurora = True
                else:
                    self._is_aurora = False

        except Exception:
            self.warning(
                "Unable to determine if server is Aurora. If this is an Aurora database, some "
                "information may be unavailable: %s",
                traceback.format_exc(),
            )
            return False

        return self._is_aurora

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
        # table. Later is chosen because that involves no string parsing.
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
                cursor.execute(show_replica_status_query(self.version, is_mariadb, replication_channel))

                results = cursor.fetchall()
                self.log.debug("Getting replication status: %s", results)
                for replica_result in results:
                    # MySQL <5.7 does not have Channel_Name.
                    # For MySQL >=5.7 'Channel_Name' is set to an empty string by default
                    channel = replication_channel or replica_result.get('Channel_Name') or 'default'
                    for key, value in iteritems(replica_result):
                        if value is not None:
                            replica_results[key]['channel:{0}'.format(channel)] = value
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            errno, msg = e.args
            if errno == 1617 and msg == "There is no master connection '{0}'".format(replication_channel):
                # MariaDB complains when you try to get replica status with a
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

    def _get_replica_status(self, db, above_560, nonblocking):
        """
        Retrieve the replicas statuses using:
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
                replica_results = cursor.fetchall()
                replicas = 0
                for _ in replica_results:
                    replicas += 1

                return {'Replicas_connected': replicas}

        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Privileges error accessing the process tables (must grant PROCESS): %s", e)
            return {}

    @classmethod
    def _are_values_numeric(cls, array):
        return all(v.isdigit() for v in array)

    @staticmethod
    def _get_variable_enabled(results, var):
        enabled = collect_string(var, results)
        return enabled and is_affirmative(enabled.lower().strip())

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
            self.warning("Size of schemas metrics unavailable at this time: %s", e)

        return {}

    def _query_size_per_table(self, db, system_tables=False):
        try:
            with closing(db.cursor()) as cursor:
                if system_tables:
                    cursor.execute(SQL_QUERY_SYSTEM_TABLE_SIZE)
                else:
                    cursor.execute(SQL_QUERY_TABLE_SIZE)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the information schema 'tables' table.")
                    return None

                table_index_size = {}
                table_data_size = {}
                for row in cursor.fetchall():
                    table_schema = str(row[0])
                    table_name = str(row[1])
                    index_size = float(row[2])
                    data_size = float(row[3])

                    # set the tag as the dictionary key
                    table_index_size["schema:{},table:{}".format(table_schema, table_name)] = index_size
                    table_data_size["schema:{},table:{}".format(table_schema, table_name)] = data_size

                return table_index_size, table_data_size
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Size of tables metrics unavailable at this time: %s", e)

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

    def _query_rows_stats_per_table(self, db):
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(SQL_QUERY_TABLE_ROWS_STATS)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the tables rows stats 'tables' table.")
                    return None

                table_rows_read_total = {}
                table_rows_changed_total = {}
                for row in cursor.fetchall():
                    table_schema = str(row[0])
                    table_name = str(row[1])
                    rows_read_total = long(row[2])
                    rows_changed_total = long(row[3])

                    # set the tag as the dictionary key
                    table_rows_read_total["schema:{},table:{}".format(table_schema, table_name)] = rows_read_total
                    table_rows_changed_total["schema:{},table:{}".format(table_schema, table_name)] = rows_changed_total
                return table_rows_read_total, table_rows_changed_total
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Tables rows stats metrics unavailable at this time: %s", e)

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

    def record_warning(self, code, message):
        # type: (DatabaseConfigurationError, str) -> None
        self._warnings_by_code[code] = message

    def _report_warnings(self):
        messages = self._warnings_by_code.values()
        # Reset the warnings for the next check run
        self._warnings_by_code = {}

        for warning in messages:
            self.warning(warning)
