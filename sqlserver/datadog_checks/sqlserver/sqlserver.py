# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import re
import time
from collections import defaultdict
from itertools import chain

import six

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.config import is_affirmative
from datadog_checks.base.utils.db import QueryManager

from . import metrics
from .connection import Connection, SQLConnectionError
from .metrics import DEFAULT_PERFORMANCE_TABLE, VALID_TABLES
from .utils import set_default_driver_conf

try:
    import adodbapi
except ImportError:
    adodbapi = None

try:
    import pyodbc
except ImportError:
    pyodbc = None

if adodbapi is None and pyodbc is None:
    raise ImportError('adodbapi or pyodbc must be installed to use this check.')

set_default_driver_conf()

VALID_METRIC_TYPES = ('gauge', 'rate', 'histogram')

# Constant for SQLServer cntr_type
PERF_LARGE_RAW_BASE = 1073939712
PERF_RAW_LARGE_FRACTION = 537003264
PERF_AVERAGE_BULK = 1073874176
PERF_COUNTER_BULK_COUNT = 272696576
PERF_COUNTER_LARGE_RAWCOUNT = 65792

# Metric discovery queries
COUNTER_TYPE_QUERY = """select distinct cntr_type
                        from sys.dm_os_performance_counters
                        where counter_name = ?;"""

BASE_NAME_QUERY = (
    """select distinct counter_name
       from sys.dm_os_performance_counters
       where (counter_name=? or counter_name=?
       or counter_name=?) and cntr_type=%s;"""
    % PERF_LARGE_RAW_BASE
)

DEFAULT_AUTODISCOVERY_INTERVAL = 3600
AUTODISCOVERY_QUERY = "select name from sys.databases"


class SQLServer(AgentCheck):
    __NAMESPACE__ = 'sqlserver'

    SERVICE_CHECK_NAME = 'sqlserver.can_connect'

    # Default performance table metrics - Database Instance level
    # datadog metric name, counter name, instance name
    INSTANCE_METRICS = [
        # SQLServer:General Statistics
        ('sqlserver.stats.connections', 'User Connections', ''),  # LARGE_RAWCOUNT
        ('sqlserver.stats.procs_blocked', 'Processes blocked', ''),  # LARGE_RAWCOUNT
        # SQLServer:Access Methods
        ('sqlserver.access.page_splits', 'Page Splits/sec', ''),  # BULK_COUNT
        # SQLServer:Memory Manager
        ('sqlserver.memory.memory_grants_pending', 'Memory Grants Pending', ''),
        ('sqlserver.memory.total_server_memory', 'Total Server Memory (KB)', ''),
        # SQLServer:Buffer Manager
        ('sqlserver.buffer.cache_hit_ratio', 'Buffer cache hit ratio', ''),  # RAW_LARGE_FRACTION
        ('sqlserver.buffer.page_life_expectancy', 'Page life expectancy', ''),  # LARGE_RAWCOUNT
        ('sqlserver.buffer.page_reads', 'Page reads/sec', ''),  # LARGE_RAWCOUNT
        ('sqlserver.buffer.page_writes', 'Page writes/sec', ''),  # LARGE_RAWCOUNT
        ('sqlserver.buffer.checkpoint_pages', 'Checkpoint pages/sec', ''),  # BULK_COUNT
        # SQLServer:SQL Statistics
        ('sqlserver.stats.auto_param_attempts', 'Auto-Param Attempts/sec', ''),
        ('sqlserver.stats.failed_auto_param_attempts', 'Failed Auto-Params/sec', ''),
        ('sqlserver.stats.safe_auto_param_attempts', 'Safe Auto-Params/sec', ''),
        ('sqlserver.stats.batch_requests', 'Batch Requests/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.sql_compilations', 'SQL Compilations/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.sql_recompilations', 'SQL Re-Compilations/sec', ''),  # BULK_COUNT
    ]

    # Performance table metrics, initially configured to track at instance-level only
    # With auto-discovery enabled, these metrics will be extended accordingly
    # datadog metric name, counter name, instance name
    INSTANCE_METRICS_TOTAL = [
        # SQLServer:Locks
        ('sqlserver.stats.lock_waits', 'Lock Waits/sec', '_Total'),  # BULK_COUNT
        # SQLServer:Plan Cache
        ('sqlserver.cache.object_counts', 'Cache Object Counts', '_Total'),
        ('sqlserver.cache.pages', 'Cache Pages', '_Total'),
        # SQLServer:Databases
        ('sqlserver.database.backup_restore_throughput', 'Backup/Restore Throughput/sec', '_Total'),
        ('sqlserver.database.log_bytes_flushed', 'Log Bytes Flushed/sec', '_Total'),
        ('sqlserver.database.log_flushes', 'Log Flushes/sec', '_Total'),
        ('sqlserver.database.log_flush_wait', 'Log Flush Wait Time', '_Total'),
        ('sqlserver.database.transactions', 'Transactions/sec', '_Total'),  # BULK_COUNT
        ('sqlserver.database.write_transactions', 'Write Transactions/sec', '_Total'),  # BULK_COUNT
        ('sqlserver.database.active_transactions', 'Active Transactions', '_Total'),  # BULK_COUNT
    ]

    # AlwaysOn metrics
    # datadog metric name, sql table, column name, tag
    AO_METRICS = [
        ('sqlserver.ao.ag_sync_health', 'sys.dm_hadr_availability_group_states', 'synchronization_health'),
        ('sqlserver.ao.replica_sync_state', 'sys.dm_hadr_database_replica_states', 'synchronization_state'),
        ('sqlserver.ao.replica_failover_mode', 'sys.availability_replicas', 'failover_mode'),
        ('sqlserver.ao.replica_failover_readiness', 'sys.availability_replicas', 'is_failover_ready'),
    ]

    AO_METRICS_PRIMARY = [
        ('sqlserver.ao.primary_replica_health', 'sys.dm_hadr_availability_group_states', 'primary_recovery_health'),
    ]

    AO_METRICS_SECONDARY = [
        ('sqlserver.ao.secondary_replica_health', 'sys.dm_hadr_availability_group_states', 'secondary_recovery_health'),
    ]

    # AlwaysOn metrics for Failover Cluster Instances (FCI).
    # This is in a separate category than other AlwaysOn metrics
    # because FCI specifies a different SQLServer setup
    # compared to Availability Groups (AG).
    # datadog metric name, sql table, column name
    # FCI status enum:
    #   0 = Up, 1 = Down, 2 = Paused, 3 = Joining, -1 = Unknown
    FCI_METRICS = [
        ('sqlserver.fci.status', 'sys.dm_os_cluster_nodes', 'status'),
        ('sqlserver.fci.is_current_owner', 'sys.dm_os_cluster_nodes', 'is_current_owner'),
    ]

    # Non-performance table metrics - can be database specific
    # datadog metric name, sql table, column name
    TASK_SCHEDULER_METRICS = [
        ('sqlserver.scheduler.current_tasks_count', 'sys.dm_os_schedulers', 'current_tasks_count'),
        ('sqlserver.scheduler.current_workers_count', 'sys.dm_os_schedulers', 'current_workers_count'),
        ('sqlserver.scheduler.active_workers_count', 'sys.dm_os_schedulers', 'active_workers_count'),
        ('sqlserver.scheduler.runnable_tasks_count', 'sys.dm_os_schedulers', 'runnable_tasks_count'),
        ('sqlserver.scheduler.work_queue_count', 'sys.dm_os_schedulers', 'work_queue_count'),
        ('sqlserver.task.context_switches_count', 'sys.dm_os_tasks', 'context_switches_count'),
        ('sqlserver.task.pending_io_count', 'sys.dm_os_tasks', 'pending_io_count'),
        ('sqlserver.task.pending_io_byte_count', 'sys.dm_os_tasks', 'pending_io_byte_count'),
        ('sqlserver.task.pending_io_byte_average', 'sys.dm_os_tasks', 'pending_io_byte_average'),
    ]

    # Non-performance table metrics
    # datadog metric name, sql table, column name
    # Files State enum:
    #   0 = Online, 1 = Restoring, 2 = Recovering, 3 = Recovery_Pending,
    #   4 = Suspect, 5 = Unknown, 6 = Offline, 7 = Defunct
    # Database State enum:
    #   0 = Online, 1 = Restoring, 2 = Recovering, 3 = Recovery_Pending,
    #   4 = Suspect, 5 = Emergency, 6 = Offline, 7 = Copying, 10 = Offline_Secondary
    # Is Sync with Backup enum:
    #   0 = False, 1 = True
    DATABASE_METRICS = [
        ('sqlserver.database.files.size', 'sys.database_files', 'size'),
        ('sqlserver.database.files.state', 'sys.database_files', 'state'),
        ('sqlserver.database.state', 'sys.databases', 'state'),
        ('sqlserver.database.is_sync_with_backup', 'sys.databases', 'is_sync_with_backup'),
        ('sqlserver.database.backup_count', 'msdb.dbo.backupset', 'backup_set_id_count'),
    ]

    DATABASE_FRAGMENTATION_METRICS = [
        (
            'sqlserver.database.avg_fragmentation_in_percent',
            'sys.dm_db_index_physical_stats',
            'avg_fragmentation_in_percent',
        ),
        ('sqlserver.database.fragment_count', 'sys.dm_db_index_physical_stats', 'fragment_count'),
        (
            'sqlserver.database.avg_fragment_size_in_pages',
            'sys.dm_db_index_physical_stats',
            'avg_fragment_size_in_pages',
        ),
    ]

    def __init__(self, name, init_config, instances):
        super(SQLServer, self).__init__(name, init_config, instances)

        self.connection = None
        self.failed_connections = {}
        self.instance_metrics = []
        self.instance_per_type_metrics = defaultdict(list)
        self.do_check = True

        self.autodiscovery = is_affirmative(self.instance.get('database_autodiscovery'))
        if self.autodiscovery and self.instance.get('database'):
            self.log.warning(
                'sqlserver `database_autodiscovery` and `database` options defined in same instance - '
                'autodiscovery will take precedence.'
            )
        self.autodiscovery_include = self.instance.get('autodiscovery_include', ['.*'])
        self.autodiscovery_exclude = self.instance.get('autodiscovery_exclude', [])
        self._compile_patterns()
        self.autodiscovery_interval = self.instance.get('autodiscovery_interval', DEFAULT_AUTODISCOVERY_INTERVAL)
        self.databases = set()
        self.ad_last_check = 0

        self.proc = self.instance.get('stored_procedure')
        self.proc_type_mapping = {'gauge': self.gauge, 'rate': self.rate, 'histogram': self.histogram}
        self.custom_metrics = init_config.get('custom_metrics', [])

        # use QueryManager to process custom queries
        self._query_manager = QueryManager(self, self.execute_query_raw, queries=[], tags=self.instance.get("tags", []))
        self.check_initializations.append(self._query_manager.compile_queries)
        self.check_initializations.append(self.initialize_connection)

    def initialize_connection(self):
        self.connection = Connection(self.init_config, self.instance, self.handle_service_check, self.log)

        # Pre-process the list of metrics to collect
        try:
            # check to see if the database exists before we try any connections to it
            db_exists, context = self.connection.check_database()

            if db_exists:
                if self.instance.get('stored_procedure') is None:
                    with self.connection.open_managed_default_connection():
                        with self.connection.get_managed_cursor() as cursor:
                            self.autodiscover_databases(cursor)
                        self._make_metric_list_to_collect(self.custom_metrics)
            else:
                # How much do we care that the DB doesn't exist?
                ignore = is_affirmative(self.instance.get("ignore_missing_database", False))
                if ignore is not None and ignore:
                    # not much : we expect it. leave checks disabled
                    self.do_check = False
                    self.log.warning("Database %s does not exist. Disabling checks for this instance.", context)
                else:
                    # yes we do. Keep trying
                    msg = "Database {} does not exist. Please resolve invalid database and restart agent".format(
                        context
                    )
                    raise ConfigurationError(msg)

        except SQLConnectionError as e:
            self.log.exception("Error connecting to database: %s", e)
        except ConfigurationError:
            raise
        except Exception as e:
            self.log.exception("Initialization exception %s", e)

    def handle_service_check(self, status, host, database, message=None):
        custom_tags = self.instance.get("tags", [])
        if custom_tags is None:
            custom_tags = []
        service_check_tags = ['host:{}'.format(host), 'db:{}'.format(database)]
        service_check_tags.extend(custom_tags)
        service_check_tags = list(set(service_check_tags))

        self.service_check(self.SERVICE_CHECK_NAME, status, tags=service_check_tags, message=message, raw=True)

    def _compile_patterns(self):
        self._include_patterns = self._compile_valid_patterns(self.autodiscovery_include)
        self._exclude_patterns = self._compile_valid_patterns(self.autodiscovery_exclude)

    def _compile_valid_patterns(self, patterns):
        valid_patterns = []

        for pattern in patterns:
            # Ignore empty patterns as they match everything
            if not pattern:
                continue

            try:
                re.compile(pattern, re.IGNORECASE)
            except Exception:
                self.log.warning('%s is not a valid regular expression and will be ignored', pattern)
            else:
                valid_patterns.append(pattern)

        if valid_patterns:
            return re.compile('|'.join(valid_patterns), re.IGNORECASE)
        else:
            # create unmatchable regex - https://stackoverflow.com/a/1845097/2157429
            return re.compile(r'(?!x)x')

    def autodiscover_databases(self, cursor):
        if not self.autodiscovery:
            return False

        now = time.time()
        if now - self.ad_last_check > self.autodiscovery_interval:
            self.log.info('Performing database autodiscovery')
            cursor.execute(AUTODISCOVERY_QUERY)
            all_dbs = set(row.name for row in cursor.fetchall())
            excluded_dbs = set([d for d in all_dbs if self._exclude_patterns.match(d)])
            included_dbs = set([d for d in all_dbs if self._include_patterns.match(d)])

            self.log.debug(
                'Autodiscovered databases: %s, excluding: %s, including: %s', all_dbs, excluded_dbs, included_dbs
            )

            # keep included dbs but remove any that were explicitly excluded
            filtered_dbs = all_dbs.intersection(included_dbs) - excluded_dbs

            self.log.debug('Resulting filtered databases: %s', filtered_dbs)
            self.ad_last_check = now

            if filtered_dbs != self.databases:
                self.log.debug('Databases updated from previous autodiscovery check.')
                self.databases = filtered_dbs
                return True
        return False

    def _make_metric_list_to_collect(self, custom_metrics):
        """
        Store the list of metrics to collect by instance_key.
        Will also create and cache cursors to query the db.
        """

        metrics_to_collect = []
        tags = self.instance.get('tags', [])

        # Load instance-level (previously Performance) metrics)
        # If several check instances are querying the same server host, it can be wise to turn these off
        # to avoid sending duplicate metrics
        if is_affirmative(self.instance.get('include_instance_metrics', True)):
            self._add_performance_counters(
                chain(self.INSTANCE_METRICS, self.INSTANCE_METRICS_TOTAL), metrics_to_collect, tags, db=None
            )

        # populated through autodiscovery
        if self.databases:
            for db in self.databases:
                self._add_performance_counters(self.INSTANCE_METRICS_TOTAL, metrics_to_collect, tags, db=db)

        # Load database statistics
        for name, table, column in self.DATABASE_METRICS:
            # include database as a filter option
            db_names = self.databases or [self.instance.get('database', self.connection.DEFAULT_DATABASE)]
            for db_name in db_names:
                cfg = {'name': name, 'table': table, 'column': column, 'instance_name': db_name, 'tags': tags}
                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load AlwaysOn metrics
        if is_affirmative(self.instance.get('include_ao_metrics', False)):
            for name, table, column in self.AO_METRICS + self.AO_METRICS_PRIMARY + self.AO_METRICS_SECONDARY:
                db_name = 'master'
                cfg = {
                    'name': name,
                    'table': table,
                    'column': column,
                    'instance_name': db_name,
                    'tags': tags,
                    'ao_database': self.instance.get('ao_database', None),
                    'availability_group': self.instance.get('availability_group', None),
                    'only_emit_local': is_affirmative(self.instance.get('only_emit_local', False)),
                }
                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load FCI metrics
        if is_affirmative(self.instance.get('include_fci_metrics', False)):
            for name, table, column in self.FCI_METRICS:
                cfg = {
                    'name': name,
                    'table': table,
                    'column': column,
                    'tags': tags,
                }
                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load metrics from scheduler and task tables, if enabled
        if is_affirmative(self.instance.get('include_task_scheduler_metrics', False)):
            for name, table, column in self.TASK_SCHEDULER_METRICS:
                cfg = {'name': name, 'table': table, 'column': column, 'tags': tags}
                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load DB Fragmentation metrics
        if is_affirmative(self.instance.get('include_db_fragmentation_metrics', False)):
            db_fragmentation_object_names = self.instance.get('db_fragmentation_object_names', [])
            db_names = self.databases or [self.instance.get('database', self.connection.DEFAULT_DATABASE)]

            if not db_fragmentation_object_names:
                self.log.debug(
                    "No fragmentation object names specified, will return fragmentation metrics for all "
                    "object_ids of current database(s): %s",
                    db_names,
                )

            for db_name in db_names:
                for name, table, column in self.DATABASE_FRAGMENTATION_METRICS:
                    cfg = {
                        'name': name,
                        'table': table,
                        'column': column,
                        'instance_name': db_name,
                        'tags': tags,
                        'db_fragmentation_object_names': db_fragmentation_object_names,
                    }
                    metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load any custom metrics from conf.d/sqlserver.yaml
        for cfg in custom_metrics:
            sql_type = None
            base_name = None

            custom_tags = tags + cfg.get('tags', [])
            cfg['tags'] = custom_tags

            db_table = cfg.get('table', DEFAULT_PERFORMANCE_TABLE)
            if db_table not in VALID_TABLES:
                self.log.error('%s has an invalid table name: %s', cfg['name'], db_table)
                continue

            if cfg.get('database', None) and cfg.get('database') != self.instance.get('database'):
                self.log.debug(
                    'Skipping custom metric %s for database %s, check instance configured for database %s',
                    cfg['name'],
                    cfg.get('database'),
                    self.instance.get('database'),
                )
                continue

            if db_table == DEFAULT_PERFORMANCE_TABLE:
                user_type = cfg.get('type')
                if user_type is not None and user_type not in VALID_METRIC_TYPES:
                    self.log.error('%s has an invalid metric type: %s', cfg['name'], user_type)
                sql_type = None
                try:
                    if user_type is None:
                        sql_type, base_name = self.get_sql_type(cfg['counter_name'])
                except Exception:
                    self.log.warning("Can't load the metric %s, ignoring", cfg['name'], exc_info=True)
                    continue

                metrics_to_collect.append(
                    self.typed_metric(
                        cfg_inst=cfg, table=db_table, base_name=base_name, user_type=user_type, sql_type=sql_type
                    )
                )

            else:
                for column in cfg['columns']:
                    metrics_to_collect.append(
                        self.typed_metric(
                            cfg_inst=cfg, table=db_table, base_name=base_name, sql_type=sql_type, column=column
                        )
                    )

        self.instance_metrics = metrics_to_collect
        self.log.debug("metrics to collect %s", metrics_to_collect)

        # create an organized grouping of metric names to their metric classes
        for m in metrics_to_collect:
            cls = m.__class__.__name__
            name = m.sql_name or m.column
            self.log.debug("Adding metric class %s named %s", cls, name)

            self.instance_per_type_metrics[cls].append(name)
            if m.base_name:
                self.instance_per_type_metrics[cls].append(m.base_name)

    def _add_performance_counters(self, metrics, metrics_to_collect, tags, db=None):
        for name, counter_name, instance_name in metrics:
            try:
                sql_type, base_name = self.get_sql_type(counter_name)
                cfg = {
                    'name': name,
                    'counter_name': counter_name,
                    'instance_name': db or instance_name,
                    'tags': tags,
                }

                metrics_to_collect.append(
                    self.typed_metric(
                        cfg_inst=cfg, table=DEFAULT_PERFORMANCE_TABLE, base_name=base_name, sql_type=sql_type
                    )
                )
            except SQLConnectionError:
                raise
            except Exception:
                self.log.warning("Can't load the metric %s, ignoring", name, exc_info=True)
                continue

    def get_sql_type(self, counter_name):
        """
        Return the type of the performance counter so that we can report it to
        Datadog correctly
        If the sql_type is one that needs a base (PERF_RAW_LARGE_FRACTION and
        PERF_AVERAGE_BULK), the name of the base counter will also be returned
        """
        with self.connection.get_managed_cursor() as cursor:
            cursor.execute(COUNTER_TYPE_QUERY, (counter_name,))
            (sql_type,) = cursor.fetchone()
            if sql_type == PERF_LARGE_RAW_BASE:
                self.log.warning("Metric %s is of type Base and shouldn't be reported this way", counter_name)
            base_name = None
            if sql_type in [PERF_AVERAGE_BULK, PERF_RAW_LARGE_FRACTION]:
                # This is an ugly hack. For certains type of metric (PERF_RAW_LARGE_FRACTION
                # and PERF_AVERAGE_BULK), we need two metrics: the metrics specified and
                # a base metrics to get the ratio. There is no unique schema so we generate
                # the possible candidates and we look at which ones exist in the db.
                candidates = (
                    counter_name + " base",
                    counter_name.replace("(ms)", "base"),
                    counter_name.replace("Avg ", "") + " base",
                )
                try:
                    cursor.execute(BASE_NAME_QUERY, candidates)
                    base_name = cursor.fetchone().counter_name.strip()
                    self.log.debug("Got base metric: %s for metric: %s", base_name, counter_name)
                except Exception as e:
                    self.log.warning("Could not get counter_name of base for metric: %s", e)

        return sql_type, base_name

    def typed_metric(self, cfg_inst, table, base_name=None, user_type=None, sql_type=None, column=None):
        """
        Create the appropriate BaseSqlServerMetric object, each implementing its method to
        fetch the metrics properly.
        If a `type` was specified in the config, it is used to report the value
        directly fetched from SQLServer. Otherwise, it is decided based on the
        sql_type, according to microsoft's documentation.
        """
        if table == DEFAULT_PERFORMANCE_TABLE:
            metric_type_mapping = {
                PERF_COUNTER_BULK_COUNT: (self.rate, metrics.SqlSimpleMetric),
                PERF_COUNTER_LARGE_RAWCOUNT: (self.gauge, metrics.SqlSimpleMetric),
                PERF_LARGE_RAW_BASE: (self.gauge, metrics.SqlSimpleMetric),
                PERF_RAW_LARGE_FRACTION: (self.gauge, metrics.SqlFractionMetric),
                PERF_AVERAGE_BULK: (self.gauge, metrics.SqlIncrFractionMetric),
            }
            if user_type is not None:
                # user type overrides any other value
                metric_type = getattr(self, user_type)
                cls = metrics.SqlSimpleMetric

            else:
                metric_type, cls = metric_type_mapping[sql_type]
        else:
            # Lookup metrics classes by their associated table
            metric_type_str, cls = metrics.TABLE_MAPPING[table]
            metric_type = getattr(self, metric_type_str)

        return cls(cfg_inst, base_name, metric_type, column, self.log)

    def check(self, _):
        if self.do_check:
            if self.proc:
                self.do_stored_procedure_check()
            else:
                self.collect_metrics()
        else:
            self.log.debug("Skipping check")

    def collect_metrics(self):
        """Fetch the metrics from all of the associated database tables."""

        with self.connection.open_managed_default_connection():
            with self.connection.get_managed_cursor() as cursor:
                # initiate autodiscovery or if the server was down at check __init__ key could be missing.
                if self.autodiscover_databases(cursor) or not self.instance_metrics:
                    self._make_metric_list_to_collect(self.custom_metrics)

                instance_results = {}

                # Execute the `fetch_all` operations first to minimize the database calls
                for cls, metric_names in six.iteritems(self.instance_per_type_metrics):
                    if not metric_names:
                        instance_results[cls] = None, None
                    else:
                        rows, cols = getattr(metrics, cls).fetch_all_values(cursor, metric_names, self.log)
                        instance_results[cls] = rows, cols

                # Using the cached data, extract and report individual metrics
                for metric in self.instance_metrics:
                    if type(metric) is metrics.SqlIncrFractionMetric:
                        # special case, since it uses the same results as SqlFractionMetric
                        rows, cols = instance_results['SqlFractionMetric']
                        metric.fetch_metric(rows, cols)
                    else:
                        rows, cols = instance_results[metric.__class__.__name__]
                        metric.fetch_metric(rows, cols)

            # reuse connection for any custom queries
            self._query_manager.execute()

    def execute_query_raw(self, query):
        with self.connection.get_managed_cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def do_stored_procedure_check(self):
        """
        Fetch the metrics from the stored proc
        """

        proc = self.proc
        guardSql = self.instance.get('proc_only_if')
        custom_tags = self.instance.get("tags", [])

        if (guardSql and self.proc_check_guard(guardSql)) or not guardSql:
            self.connection.open_db_connections(self.connection.DEFAULT_DB_KEY)
            cursor = self.connection.get_cursor(self.connection.DEFAULT_DB_KEY)

            try:
                self.log.debug("Calling Stored Procedure : %s", proc)
                if self.connection.get_connector() == 'adodbapi':
                    cursor.callproc(proc)
                else:
                    # pyodbc does not support callproc; use execute instead.
                    # Reference: https://github.com/mkleehammer/pyodbc/wiki/Calling-Stored-Procedures
                    call_proc = '{{CALL {}}}'.format(proc)
                    cursor.execute(call_proc)

                rows = cursor.fetchall()
                self.log.debug("Row count (%s) : %s", proc, cursor.rowcount)

                for row in rows:
                    tags = [] if row.tags is None or row.tags == '' else row.tags.split(',')
                    tags.extend(custom_tags)

                    if row.type.lower() in self.proc_type_mapping:
                        self.proc_type_mapping[row.type](row.metric, row.value, tags, raw=True)
                    else:
                        self.log.warning(
                            '%s is not a recognised type from procedure %s, metric %s', row.type, proc, row.metric
                        )

            except Exception as e:
                self.log.warning("Could not call procedure %s: %s", proc, e)
                raise e

            self.connection.close_cursor(cursor)
            self.connection.close_db_connections(self.connection.DEFAULT_DB_KEY)
        else:
            self.log.info("Skipping call to %s due to only_if", proc)

    def proc_check_guard(self, sql):
        """
        check to see if the guard SQL returns a single column containing 0 or 1
        We return true if 1, else False
        """
        self.connection.open_db_connections(self.connection.PROC_GUARD_DB_KEY)
        cursor = self.connection.get_cursor(self.connection.PROC_GUARD_DB_KEY)

        should_run = False
        try:
            cursor.execute(sql, ())
            result = cursor.fetchone()
            should_run = result[0] == 1
        except Exception as e:
            self.log.error("Failed to run proc_only_if sql %s : %s", sql, e)

        self.connection.close_cursor(cursor)
        self.connection.close_db_connections(self.connection.PROC_GUARD_DB_KEY)
        return should_run
