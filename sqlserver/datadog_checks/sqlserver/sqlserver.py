# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Check the performance counters from SQL Server
For information on how to report the metrics available in the sys.dm_os_performance_counters table see
http://blogs.msdn.com/b/psssql/archive/2013/09/23/interpreting-the-counter-values-from-sys-dm-os-performance-counters.aspx  # noqa: E501
"""
from __future__ import division

from collections import defaultdict

import six

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.config import is_affirmative

from . import metrics
from .connection import Connection, SQLConnectionError
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

EVENT_TYPE = SOURCE_TYPE_NAME = 'sql server'
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

# Performance tables
DEFAULT_PERFORMANCE_TABLE = "sys.dm_os_performance_counters"
DM_OS_WAIT_STATS_TABLE = "sys.dm_os_wait_stats"
DM_OS_MEMORY_CLERKS_TABLE = "sys.dm_os_memory_clerks"
DM_OS_VIRTUAL_FILE_STATS = "sys.dm_io_virtual_file_stats"
DM_OS_SCHEDULERS = "sys.dm_os_schedulers"
DM_OS_TASKS = "sys.dm_os_tasks"


class SQLServer(AgentCheck):

    SERVICE_CHECK_NAME = 'sqlserver.can_connect'

    PERF_METRICS = [
        ('sqlserver.buffer.cache_hit_ratio', 'Buffer cache hit ratio', ''),  # RAW_LARGE_FRACTION
        ('sqlserver.buffer.page_life_expectancy', 'Page life expectancy', ''),  # LARGE_RAWCOUNT
        ('sqlserver.stats.batch_requests', 'Batch Requests/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.sql_compilations', 'SQL Compilations/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.sql_recompilations', 'SQL Re-Compilations/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.connections', 'User Connections', ''),  # LARGE_RAWCOUNT
        ('sqlserver.stats.lock_waits', 'Lock Waits/sec', '_Total'),  # BULK_COUNT
        ('sqlserver.access.page_splits', 'Page Splits/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.procs_blocked', 'Processes blocked', ''),  # LARGE_RAWCOUNT
        ('sqlserver.buffer.checkpoint_pages', 'Checkpoint pages/sec', ''),  # BULK_COUNT
    ]

    TASK_SCHEDULER_METRICS = [
        ('sqlserver.scheduler.current_tasks_count', DM_OS_SCHEDULERS, 'current_tasks_count'),
        ('sqlserver.scheduler.current_workers_count', DM_OS_SCHEDULERS, 'current_workers_count'),
        ('sqlserver.scheduler.active_workers_count', DM_OS_SCHEDULERS, 'active_workers_count'),
        ('sqlserver.scheduler.runnable_tasks_count', DM_OS_SCHEDULERS, 'runnable_tasks_count'),
        ('sqlserver.scheduler.work_queue_count', DM_OS_SCHEDULERS, 'work_queue_count'),
        ('sqlserver.task.context_switches_count', DM_OS_TASKS, 'context_switches_count'),
        ('sqlserver.task.pending_io_count', DM_OS_TASKS, 'pending_io_count'),
        ('sqlserver.task.pending_io_byte_count', DM_OS_TASKS, 'pending_io_byte_count'),
        ('sqlserver.task.pending_io_byte_average', DM_OS_TASKS, 'pending_io_byte_average'),
    ]

    valid_tables = [
        DEFAULT_PERFORMANCE_TABLE,
        DM_OS_WAIT_STATS_TABLE,
        DM_OS_MEMORY_CLERKS_TABLE,
        DM_OS_VIRTUAL_FILE_STATS,
        DM_OS_SCHEDULERS,
        DM_OS_TASKS,
    ]

    def __init__(self, name, init_config, instances):
        super(SQLServer, self).__init__(name, init_config, instances)

        self.failed_connections = {}
        self.instance_metrics = []
        self.instance_per_type_metrics = defaultdict(list)
        self.do_check = True
        self.proc_type_mapping = {'gauge': self.gauge, 'rate': self.rate, 'histogram': self.histogram}

        self.connection = Connection(init_config, self.instance, self.handle_service_check, self.log)

        # Pre-process the list of metrics to collect
        self.custom_metrics = init_config.get('custom_metrics', [])
        try:
            # check to see if the database exists before we try any connections to it
            db_exists, context = self.connection.check_database()

            if db_exists:
                if self.instance.get('stored_procedure') is None:
                    with self.connection.open_managed_default_connection():
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

        # Historically, the check does not raise exceptions on init failures
        # We continue that here for backwards compatibility, aside from the new Config exception
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

        self.service_check(self.SERVICE_CHECK_NAME, status, tags=service_check_tags, message=message)

    def _make_metric_list_to_collect(self, custom_metrics):
        """
        Store the list of metrics to collect by instance_key.
        Will also create and cache cursors to query the db.
        """

        metrics_to_collect = []
        tags = self.instance.get('tags', [])

        for name, counter_name, instance_name in self.PERF_METRICS:
            try:
                sql_type, base_name = self.get_sql_type(counter_name)
                cfg = {}
                cfg['name'] = name
                cfg['counter_name'] = counter_name
                cfg['instance_name'] = instance_name
                cfg['tags'] = tags

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

        # Load metrics from scheduler and task tables, if enabled
        if self.instance.get('include_task_scheduler_metrics', False):
            for name, table, column in self.TASK_SCHEDULER_METRICS:
                cfg = {}
                cfg['name'] = name
                cfg['table'] = table
                cfg['column'] = column
                cfg['tags'] = tags

                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load any custom metrics from conf.d/sqlserver.yaml
        for cfg in custom_metrics:
            sql_type = None
            base_name = None

            custom_tags = tags + cfg.get('tags', [])
            cfg['tags'] = custom_tags

            db_table = cfg.get('table', DEFAULT_PERFORMANCE_TABLE)
            if db_table not in self.valid_tables:
                self.log.error('%s has an invalid table name: %s', cfg['name'], db_table)
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
            name = m.sql_name or m.datadog_name
            self.log.debug("Adding metric class %s named %s", cls, name)

            self.instance_per_type_metrics[cls].append(name)
            if m.base_name:
                self.instance_per_type_metrics[cls].append(m.base_name)

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
        Create the appropriate SqlServerMetric object, each implementing its method to
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
            table_type_mapping = {
                DM_OS_WAIT_STATS_TABLE: (self.gauge, metrics.SqlOsWaitStat),
                DM_OS_MEMORY_CLERKS_TABLE: (self.gauge, metrics.SqlOsMemoryClerksStat),
                DM_OS_VIRTUAL_FILE_STATS: (self.gauge, metrics.SqlIoVirtualFileStat),
                DM_OS_SCHEDULERS: (self.gauge, metrics.SqlOsSchedulers),
                DM_OS_TASKS: (self.gauge, metrics.SqlOsTasks),
            }
            metric_type, cls = table_type_mapping[table]

        return cls(cfg_inst, base_name, metric_type, column, self.log)

    def check(self, _):
        if self.do_check:
            proc = self.instance.get('stored_procedure')
            if proc is None:
                self.do_perf_counter_check()
            else:
                self.do_stored_procedure_check(proc)
        else:
            self.log.debug("Skipping check")

    def do_perf_counter_check(self):
        """
        Fetch the metrics from the sys.dm_os_performance_counters table
        """
        with self.connection.open_managed_default_connection():
            # if the server was down at check __init__ key could be missing.
            if not self.instance_metrics:
                self._make_metric_list_to_collect(self.custom_metrics)
            metrics_to_collect = self.instance_metrics

            with self.connection.get_managed_cursor() as cursor:

                instance_results = {}

                # Execute the `fetch_all` operations first to minimize the database calls
                for cls, metric_names in six.iteritems(self.instance_per_type_metrics):
                    rows, cols = getattr(metrics, cls).fetch_all_values(cursor, metric_names, self.log)
                    instance_results[cls] = rows, cols

                for metric in metrics_to_collect:
                    try:
                        # TODO - check if results are actually there before trying to fetch?

                        if type(metric) is metrics.SqlIncrFractionMetric:
                            # special case, since it uses the same results as SqlFractionMetric
                            rows, cols = instance_results['SqlFractionMetric']
                            metric.fetch_metric(rows, cols)
                        else:
                            rows, cols = instance_results[metric.__class__.__name__]
                            metric.fetch_metric(rows, cols)

                    except Exception as e:
                        self.log.warning("Could not fetch metric %s : %s", metric.datadog_name, e)

    def do_stored_procedure_check(self, proc):
        """
        Fetch the metrics from the stored proc
        """

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
                        self.proc_type_mapping[row.type](row.metric, row.value, tags)
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
