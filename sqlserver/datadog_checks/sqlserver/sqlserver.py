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

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.config import is_affirmative

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
ALL_INSTANCES = 'ALL'
VALID_METRIC_TYPES = ('gauge', 'rate', 'histogram')

# Constant for SQLServer cntr_type
PERF_LARGE_RAW_BASE = 1073939712
PERF_RAW_LARGE_FRACTION = 537003264
PERF_AVERAGE_BULK = 1073874176
PERF_COUNTER_BULK_COUNT = 272696576
PERF_COUNTER_LARGE_RAWCOUNT = 65792

# Queries
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

INSTANCES_QUERY = """select instance_name
                     from sys.dm_os_performance_counters
                     where counter_name=? and instance_name!='_Total';"""

VALUE_AND_BASE_QUERY = """select counter_name, cntr_type, cntr_value, instance_name, object_name
                          from sys.dm_os_performance_counters
                          where counter_name in (%s)
                          order by cntr_type;"""


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

        for name, counter_name, instance_name in self.PERF_METRICS:
            try:
                sql_type, base_name = self.get_sql_type(counter_name)
                cfg = {}
                cfg['name'] = name
                cfg['counter_name'] = counter_name
                cfg['instance_name'] = instance_name

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

                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load any custom metrics from conf.d/sqlserver.yaml
        for cfg in custom_metrics:
            sql_type = None
            base_name = None

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
            self.log.debug("Adding metric class %s named %s", m.__class__.__name__, m.sql_name or m.datadog_name)
            self.instance_per_type_metrics[m.__class__.__name__].append(m.sql_name or m.datadog_name)
            if m.base_name:
                self.instance_per_type_metrics[m.__class__.__name__].append(m.base_name)

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
                PERF_COUNTER_BULK_COUNT: (self.rate, SqlSimpleMetric),
                PERF_COUNTER_LARGE_RAWCOUNT: (self.gauge, SqlSimpleMetric),
                PERF_LARGE_RAW_BASE: (self.gauge, SqlSimpleMetric),
                PERF_RAW_LARGE_FRACTION: (self.gauge, SqlFractionMetric),
                PERF_AVERAGE_BULK: (self.gauge, SqlIncrFractionMetric),
            }
            if user_type is not None:
                # user type overrides any other value
                metric_type = getattr(self, user_type)
                cls = SqlSimpleMetric

            else:
                metric_type, cls = metric_type_mapping[sql_type]
        else:
            table_type_mapping = {
                DM_OS_WAIT_STATS_TABLE: (self.gauge, SqlOsWaitStat),
                DM_OS_MEMORY_CLERKS_TABLE: (self.gauge, SqlOsMemoryClerksStat),
                DM_OS_VIRTUAL_FILE_STATS: (self.gauge, SqlIoVirtualFileStat),
                DM_OS_SCHEDULERS: (self.gauge, SqlOsSchedulers),
                DM_OS_TASKS: (self.gauge, SqlOsTasks),
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
        custom_tags = self.instance.get('tags', [])
        if custom_tags is None:
            custom_tags = []
        with self.connection.open_managed_default_connection():
            # if the server was down at check __init__ key could be missing.
            if not self.instance_metrics:
                self._make_metric_list_to_collect(self.custom_metrics)
            metrics_to_collect = self.instance_metrics

            with self.connection.get_managed_cursor() as cursor:
                simple_rows = SqlSimpleMetric.fetch_all_values(
                    cursor, self.instance_per_type_metrics["SqlSimpleMetric"], self.log
                )
                fraction_results = SqlFractionMetric.fetch_all_values(
                    cursor, self.instance_per_type_metrics["SqlFractionMetric"], self.log
                )
                waitstat_rows, waitstat_cols = SqlOsWaitStat.fetch_all_values(
                    cursor, self.instance_per_type_metrics["SqlOsWaitStat"], self.log
                )
                vfs_rows, vfs_cols = SqlIoVirtualFileStat.fetch_all_values(
                    cursor, self.instance_per_type_metrics["SqlIoVirtualFileStat"], self.log
                )
                clerk_rows, clerk_cols = SqlOsMemoryClerksStat.fetch_all_values(
                    cursor, self.instance_per_type_metrics["SqlOsMemoryClerksStat"], self.log  # noqa: E501
                )
                scheduler_rows, scheduler_cols = SqlOsSchedulers.fetch_all_values(
                    cursor, self.instance_per_type_metrics["SqlOsSchedulers"], self.log
                )
                task_rows, task_cols = SqlOsTasks.fetch_all_values(
                    cursor, self.instance_per_type_metrics["SqlOsTasks"], self.log
                )

                for metric in metrics_to_collect:
                    try:
                        if type(metric) is SqlSimpleMetric:
                            metric.fetch_metric(cursor, simple_rows, custom_tags)
                        elif type(metric) is SqlFractionMetric or type(metric) is SqlIncrFractionMetric:
                            metric.fetch_metric(cursor, fraction_results, custom_tags)
                        elif type(metric) is SqlOsWaitStat:
                            metric.fetch_metric(cursor, waitstat_rows, waitstat_cols, custom_tags)
                        elif type(metric) is SqlIoVirtualFileStat:
                            metric.fetch_metric(cursor, vfs_rows, vfs_cols, custom_tags)
                        elif type(metric) is SqlOsMemoryClerksStat:
                            metric.fetch_metric(cursor, clerk_rows, clerk_cols, custom_tags)
                        elif type(metric) is SqlOsSchedulers:
                            metric.fetch_metric(cursor, scheduler_rows, scheduler_cols, custom_tags)
                        elif type(metric) is SqlOsTasks:
                            metric.fetch_metric(cursor, task_rows, task_cols, custom_tags)

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


class SqlServerMetric(object):
    """General class for common methods, should never be instantiated directly"""

    def __init__(self, cfg_instance, base_name, report_function, column, logger):
        self.cfg_instance = cfg_instance
        self.datadog_name = cfg_instance['name']
        self.sql_name = cfg_instance.get('counter_name', '')
        self.base_name = base_name
        self.report_function = report_function
        self.instance = cfg_instance.get('instance_name', '')
        self.object_name = cfg_instance.get('object_name', '')
        self.tags = cfg_instance.get('tags', [])
        self.tag_by = cfg_instance.get('tag_by', None)
        self.column = column
        self.instances = None
        self.past_values = {}
        self.log = logger

    def __repr__(self):
        return '<{} datadog_name={!r}, sql_name={!r}, base_name={!r} column={!r}>'.format(
            self.__class__.__name__, self.datadog_name, self.sql_name, self.base_name, self.column
        )

    def fetch_metrics(self, cursor, tags):
        raise NotImplementedError


class SqlSimpleMetric(SqlServerMetric):
    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        placeholder = '?'
        placeholders = ', '.join(placeholder for unused in counters_list)
        query_base = (
            """
            select counter_name, instance_name, object_name, cntr_value
            from sys.dm_os_performance_counters where counter_name in (%s)
            """
            % placeholders
        )

        logger.debug("query base: %s", query_base)
        cursor.execute(query_base, counters_list)
        rows = cursor.fetchall()
        return rows

    def fetch_metric(self, cursor, rows, tags):
        tags = tags + self.tags

        for counter_name_long, instance_name_long, object_name, cntr_value in rows:
            counter_name = counter_name_long.strip()
            instance_name = instance_name_long.strip()
            object_name = object_name.strip()
            if counter_name.strip() == self.sql_name:
                matched = False
                metric_tags = list(tags)

                if (self.instance == ALL_INSTANCES and instance_name != "_Total") or (
                    instance_name == self.instance and (not self.object_name or object_name == self.object_name)
                ):
                    matched = True

                if matched:
                    if self.instance == ALL_INSTANCES:
                        metric_tags.append('{}:{}'.format(self.tag_by, instance_name.strip()))
                    self.report_function(self.datadog_name, cntr_value, tags=metric_tags)
                    if self.instance != ALL_INSTANCES:
                        break


class SqlFractionMetric(SqlServerMetric):
    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        placeholder = '?'
        placeholders = ', '.join(placeholder for unused in counters_list)
        query_base = VALUE_AND_BASE_QUERY % placeholders

        logger.debug("query base: %s, %s", query_base, str(counters_list))
        cursor.execute(query_base, counters_list)
        rows = cursor.fetchall()
        results = defaultdict(list)
        for counter_name, cntr_type, cntr_value, instance_name, object_name in rows:
            rowlist = [cntr_type, cntr_value, instance_name.strip(), object_name.strip()]
            logger.debug("Adding new rowlist %s", str(rowlist))
            results[counter_name.strip()].append(rowlist)
        return results

    def set_instances(self, cursor):
        if self.instance == ALL_INSTANCES:
            cursor.execute(INSTANCES_QUERY, (self.sql_name,))
            self.instances = [row.instance_name for row in cursor.fetchall()]
        else:
            self.instances = [self.instance]

    def fetch_metric(self, cursor, results, tags):
        """
        Because we need to query the metrics by matching pairs, we can't query
        all of them together without having to perform some matching based on
        the name afterwards so instead we query instance by instance.
        We cache the list of instance so that we don't have to look it up every time
        """
        if self.sql_name not in results:
            self.log.warning("Couldn't find %s in results", self.sql_name)
            return

        tags = tags + self.tags

        results_list = results[self.sql_name]
        done_instances = []
        for ndx, row in enumerate(results_list):
            ctype = row[0]
            cval = row[1]
            inst = row[2]
            object_name = row[3]

            if inst in done_instances:
                continue

            if (self.instance != ALL_INSTANCES and inst != self.instance) or (
                self.object_name and object_name != self.object_name
            ):
                done_instances.append(inst)
                continue

            # find the next row which has the same instance
            cval2 = None
            ctype2 = None
            for second_row in results_list[: ndx + 1]:
                if inst == second_row[2]:
                    cval2 = second_row[1]
                    ctype2 = second_row[0]

            if cval2 is None:
                self.log.warning("Couldn't find second value for %s", self.sql_name)
                continue
            done_instances.append(inst)
            if ctype < ctype2:
                value = cval
                base = cval2
            else:
                value = cval2
                base = cval

            metric_tags = list(tags)
            if self.instance == ALL_INSTANCES:
                metric_tags.append('{}:{}'.format(self.tag_by, inst.strip()))
            self.report_fraction(value, base, metric_tags)

    def report_fraction(self, value, base, metric_tags):
        try:
            result = value / float(base)
            self.report_function(self.datadog_name, result, tags=metric_tags)
        except ZeroDivisionError:
            self.log.debug("Base value is 0, won't report metric %s for tags %s", self.datadog_name, metric_tags)


class SqlIncrFractionMetric(SqlFractionMetric):
    def report_fraction(self, value, base, metric_tags):
        key = "key:" + "".join(metric_tags)
        if key in self.past_values:
            old_value, old_base = self.past_values[key]
            diff_value = value - old_value
            diff_base = base - old_base
            try:
                result = diff_value / float(diff_base)
                self.report_function(self.datadog_name, result, tags=metric_tags)
            except ZeroDivisionError:
                self.log.debug("Base value is 0, won't report metric %s for tags %s", self.datadog_name, metric_tags)
        self.past_values[key] = (value, base)


class SqlOsWaitStat(SqlServerMetric):
    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        if not counters_list:
            return None, None

        placeholder = '?'
        placeholders = ', '.join(placeholder for unused in counters_list)
        query_base = """
            select * from sys.dm_os_wait_stats where wait_type in ({})
            """.format(
            placeholders
        )
        logger.debug("query base: %s", query_base)
        cursor.execute(query_base, counters_list)
        rows = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        return rows, columns

    def fetch_metric(self, cursor, rows, columns, tags):
        name_column_index = columns.index("wait_type")
        value_column_index = columns.index(self.column)
        value = None
        for row in rows:
            if row[name_column_index] == self.sql_name:
                value = row[value_column_index]
                break
        if value is None:
            self.log.debug("Didn't find %s %s", self.sql_name, self.column)
            return

        self.log.debug("Value for %s %s is %s", self.sql_name, self.column, value)
        metric_name = '{}.{}'.format(self.datadog_name, self.column)
        self.report_function(metric_name, value, tags=tags + self.tags)


class SqlIoVirtualFileStat(SqlServerMetric):
    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        if not counters_list:
            return None, None

        query_base = "select * from sys.dm_io_virtual_file_stats(null, null)"
        logger.debug("query base: %s", query_base)
        cursor.execute(query_base)
        rows = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        return rows, columns

    def __init__(self, cfg_instance, base_name, report_function, column, logger):
        super(SqlIoVirtualFileStat, self).__init__(cfg_instance, base_name, report_function, column, logger)
        self.dbid = self.cfg_instance.get('database_id', None)
        self.fid = self.cfg_instance.get('file_id', None)
        self.pvs_vals = defaultdict(lambda: None)

    def fetch_metric(self, cursor, rows, columns, tags):
        # TODO - fix this function
        #  this function actually processes the change in value between two checks,
        #  but doesn't account for time differences.  This can work for some columns like `num_of_writes`, but is
        #  inaccurate for others like `io_stall_write_ms` which are not monotonically increasing.
        tags = tags + self.tags
        dbid_ndx = columns.index("database_id")
        fileid_ndx = columns.index("file_id")
        column_ndx = columns.index(self.column)
        for row in rows:
            dbid = row[dbid_ndx]
            fid = row[fileid_ndx]
            value = row[column_ndx]

            if self.dbid and self.dbid != dbid:
                continue
            if self.fid and self.fid != fid:
                continue
            if not self.pvs_vals[dbid, fid]:
                self.pvs_vals[dbid, fid] = value
                continue

            report_value = value - self.pvs_vals[dbid, fid]
            self.pvs_vals[dbid, fid] = value
            metric_tags = ['database_id:{}'.format(str(dbid).strip()), 'file_id:{}'.format(str(fid).strip())]
            metric_tags.extend(tags)
            metric_name = '{}.{}'.format(self.datadog_name, self.column)
            self.report_function(metric_name, report_value, tags=metric_tags)


class SqlOsMemoryClerksStat(SqlServerMetric):
    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        if not counters_list:
            return None, None

        placeholder = '?'
        placeholders = ', '.join(placeholder for _ in counters_list)
        query_base = """
            select * from sys.dm_os_memory_clerks where type in ({})
            """.format(
            placeholders
        )
        logger.debug("query base: %s", query_base)
        cursor.execute(query_base, counters_list)
        rows = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        return rows, columns

    def fetch_metric(self, cursor, rows, columns, tags):
        tags = tags + self.tags
        type_column_index = columns.index("type")
        value_column_index = columns.index(self.column)
        memnode_index = columns.index("memory_node_id")

        for row in rows:
            column_val = row[value_column_index]
            node_id = row[memnode_index]
            met_type = row[type_column_index]
            if met_type != self.sql_name:
                continue

            metric_tags = ['memory_node_id:{}'.format(str(node_id))]
            metric_tags.extend(tags)
            metric_name = '{}.{}'.format(self.datadog_name, self.column)
            self.report_function(metric_name, column_val, tags=metric_tags)


class SqlOsSchedulers(SqlServerMetric):
    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        if not counters_list:
            return None, None

        query_base = "select * from sys.dm_os_schedulers"
        logger.debug("query base: %s", query_base)
        cursor.execute(query_base)
        rows = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        return rows, columns

    def fetch_metric(self, cursor, rows, columns, tags):
        tags = tags + self.tags
        value_column_index = columns.index(self.column)
        scheduler_index = columns.index("scheduler_id")
        parent_node_index = columns.index("parent_node_id")

        for row in rows:
            column_val = row[value_column_index]
            scheduler_id = row[scheduler_index]
            parent_node_id = row[parent_node_index]

            metric_tags = ['scheduler_id:{}'.format(str(scheduler_id)), 'parent_node_id:{}'.format(str(parent_node_id))]
            metric_tags.extend(tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)


class SqlOsTasks(SqlServerMetric):
    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        if not counters_list:
            return None, None

        query_base = "select * from sys.dm_os_tasks"
        logger.debug("query base: %s", query_base)
        cursor.execute(query_base)
        rows = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        return rows, columns

    def fetch_metric(self, cursor, rows, columns, tags):
        tags = tags + self.tags
        session_id_column_index = columns.index("session_id")
        scheduler_id_column_index = columns.index("scheduler_id")
        value_column_index = columns.index(self.column)

        for row in rows:
            column_val = row[value_column_index]
            session_id = row[session_id_column_index]
            scheduler_id = row[scheduler_id_column_index]

            metric_tags = ['session_id:{}'.format(str(session_id)), 'scheduler_id:{}'.format(str(scheduler_id))]
            metric_tags.extend(tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)
