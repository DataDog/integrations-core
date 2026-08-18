# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
DEPRECATED:
This module is considered deprecated and will be removed in a future release.
DO NOT add new metrics to this module. Instead, use the `database_metrics` module.

Collection of metric classes for specific SQL Server tables.
"""

from __future__ import division

from collections import defaultdict
from functools import partial

# Queries
ALL_INSTANCES = 'ALL'


class BaseSqlServerMetric(object):
    """Base class for SQL Server metrics collection operations.

    Each subclass defines the TABLE it's associated with, and the default
    query to collect all the information in one request.  This query gets
    executed as part of the classmethod `fetch_all_values` and the data gets passed
    to the instance method `fetch_metric` which extracts the appropriate metric from
    within the larger collection.

    This approach limits the load on the server during each check run.
    """

    TABLE = None
    DEFAULT_METRIC_TYPE = None
    QUERY_BASE = None
    OPERATION_NAME = 'base_metrics'

    # Flag to indicate if this subclass/table is available for custom queries
    CUSTOM_QUERIES_AVAILABLE = True

    def __init__(self, cfg_instance, base_name, report_function, column, logger):
        self.cfg_instance = cfg_instance
        self.metric_name = cfg_instance['name']
        self.sql_name = cfg_instance.get('counter_name', '')
        self.base_name = base_name
        partial_kwargs = {}
        if 'hostname' in cfg_instance:
            partial_kwargs['hostname'] = cfg_instance['hostname']
        self.report_function = partial(report_function, raw=True, **partial_kwargs)
        self.instance = cfg_instance.get('instance_name', '')
        self.physical_db_name = cfg_instance.get('physical_db_name', '')
        self.object_name = cfg_instance.get('object_name', '')
        self.tags = cfg_instance.get('tags', []) or []
        self.tag_by = cfg_instance.get('tag_by', None)
        self.column = column
        self.instances = None
        self.log = logger

    def __repr__(self):
        return '<{} datadog_name={!r}, sql_name={!r}, base_name={!r} column={!r}>'.format(
            self.__class__.__name__, self.metric_name, self.sql_name, self.base_name, self.column
        )

    @classmethod
    def _fetch_generic_values(cls, cursor, counters_list, logger):
        if counters_list:
            placeholders = ', '.join('?' for _ in counters_list)
            query = cls.QUERY_BASE.format(placeholders=placeholders)
            logger.debug("%s: fetch_all executing query: %s, %s", cls.__name__, query, counters_list)
            cursor.execute(query, counters_list)
        else:
            query = cls.QUERY_BASE
            logger.debug("%s: fetch_all executing query: %s", cls.__name__, query)
            cursor.execute(query)

        rows = cursor.fetchall()
        columns = [i[0] for i in cursor.description]
        logger.debug("%s: received %d rows and %d columns", cls.__name__, len(rows), len(columns))
        return rows, columns

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None, engine_edition=None):
        raise NotImplementedError

    def fetch_metric(self, rows, columns, values_cache=None):
        raise NotImplementedError


# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-performance-counters-transact-sql
class SqlPerfCounterMetric(BaseSqlServerMetric):
    """Base class for the metrics read from sys.dm_os_performance_counters.

    Subclasses differ only in how they turn counter values into metrics, so they share a single query and a
    single snapshot of the table: scanning it costs the same whether two rows come back or thousands, so a
    query per subclass is pure overhead.
    """

    TABLE = 'sys.dm_os_performance_counters'
    QUERY_BASE = """select counter_name, instance_name, object_name, cntr_value
                    from {table} where counter_name in ({{placeholders}})""".format(table=TABLE)
    OPERATION_NAME = 'perf_counter_metrics'

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None, engine_edition=None):
        rows, _ = cls._fetch_generic_values(cursor, counters_list, logger)
        # The name columns are nchar(128), so every value arrives blank-padded. Strip once here and index by
        # counter name and instance name so each metric can look its own rows up directly: with autodiscovery
        # both the number of metrics and the number of rows grow with the database count, so scanning rows per
        # metric is quadratic.
        results = defaultdict(lambda: defaultdict(list))
        for counter_name, instance_name, object_name, cntr_value in rows:
            results[counter_name.strip()][instance_name.strip()].append((object_name.strip(), cntr_value))
        return results, None

    def _configured_instance_names(self):
        """The instance names this metric collects from, in precedence order.

        The physical database name is a fallback for the logical one and differs from it only on Azure SQL
        Database; skip it when the two match so the metric is not reported twice.
        """
        if self.physical_db_name and self.physical_db_name != self.instance:
            return (self.instance, self.physical_db_name)
        return (self.instance,)


class SqlSimpleMetric(SqlPerfCounterMetric):
    DEFAULT_METRIC_TYPE = None  # can be either rate or gauge

    def fetch_metric(self, results, columns, values_cache=None):
        counters_by_instance = results.get(self.sql_name)
        if not counters_by_instance:
            return

        if self.instance == ALL_INSTANCES:
            for instance_name, counters in counters_by_instance.items():
                if instance_name == "_Total":
                    continue
                metric_tags = [*self.tags, '{}:{}'.format(self.tag_by, instance_name)]
                for _object_name, cntr_value in counters:
                    self.report_function(self.metric_name, cntr_value, tags=metric_tags)
            return

        for instance_name in self._configured_instance_names():
            for object_name, cntr_value in counters_by_instance.get(instance_name, ()):
                if not self.object_name or object_name == self.object_name:
                    self.report_function(self.metric_name, cntr_value, tags=list(self.tags))
                    return


class SqlFractionMetric(SqlPerfCounterMetric):
    DEFAULT_METRIC_TYPE = 'gauge'

    def fetch_metric(self, results, columns, values_cache=None):
        if not self.base_name:
            self.log.error('Skipping counter. Missing base counter name')
            return
        numerators = results.get(self.sql_name.strip())
        bases = results.get(self.base_name.strip())
        if not numerators or not bases:
            self.log.error(
                'Skipping counter. Missing numerator and/or base counters \nsql_name=%s \nbase_name=%s',
                self.sql_name,
                self.base_name,
            )
            return

        if self.instance == ALL_INSTANCES:
            instance_names = list(numerators)
        else:
            instance_names = self._configured_instance_names()

        for instance_name in instance_names:
            if self.instance == ALL_INSTANCES:
                metric_tags = [*self.tags, '{}:{}'.format(self.tag_by, instance_name)]
            else:
                metric_tags = list(self.tags)

            for object_name, cntr_value in numerators.get(instance_name, ()):
                if self.object_name and self.object_name != object_name:
                    continue
                base_value = self._base_value(bases.get(instance_name), object_name)
                if base_value is None:
                    self.log.warning(
                        'Could not find corresponding base counter for sql_name: %s base_name: %s',
                        self.sql_name,
                        self.base_name,
                    )
                    continue

                self.report_fraction(cntr_value, base_value, metric_tags, previous_values=values_cache)

    @staticmethod
    def _base_value(base_counters, object_name):
        """The value of the base counter recorded under the same object as the numerator, if there is one."""
        for base_object_name, base_value in base_counters or ():
            if base_object_name == object_name:
                return base_value
        return None

    def report_fraction(self, value, base, metric_tags, previous_values):
        try:
            result = value / float(base)
            self.report_function(self.metric_name, result, tags=metric_tags)
        except ZeroDivisionError:
            self.log.debug("Base value is 0, won't report metric %s for tags %s", self.metric_name, metric_tags)


class SqlIncrFractionMetric(SqlFractionMetric):
    """
    Performance counters where the cntr_type column value is 1073874176 display
    how many items are processed on average, as a ratio of the items processed
    to the number of operations. For example, the Locks:Average Wait Time (ms)
    counters compares the lock waits per second with the lock requests per second,
    to display the average amount of wait time (in milliseconds) for each lock request that resulted in a wait.
    As such, to get a snapshot-like reading of the last second only, you must compare the delta between
    the current value and the base value (denominator) between two collection points that are one second apart.
    """

    def report_fraction(self, value, base, metric_tags, previous_values):
        # return if nil is passed as the values cache, as this should be instantiated
        # at check instantiation
        if previous_values is None:
            return
        # key is set to the metric name + the metric tags in order to support
        # per database instance fraction metrics
        key = "{}:{}".format(self.metric_name, "".join(metric_tags))
        if key in previous_values:
            old_value, old_base = previous_values[key]
            diff_value = value - old_value
            diff_base = base - old_base
            try:
                result = diff_value / float(diff_base)
                self.report_function(self.metric_name, result, tags=metric_tags)
            except ZeroDivisionError:
                self.log.debug("Base value is 0, won't report metric %s for tags %s", self.metric_name, metric_tags)
        previous_values[key] = (value, base)


# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-wait-stats-transact-sql
class SqlOsWaitStat(BaseSqlServerMetric):
    TABLE = 'sys.dm_os_wait_stats'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """select * from {table} where wait_type in ({{placeholders}})""".format(table=TABLE)
    OPERATION_NAME = 'os_wait_stat_metric'

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None, engine_edition=None):
        return cls._fetch_generic_values(cursor, counters_list, logger)

    def fetch_metric(self, rows, columns, values_cache=None):
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
        metric_name = '{}.{}'.format(self.metric_name, self.column)
        self.report_function(metric_name, value, tags=self.tags)


# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-io-virtual-file-stats-transact-sql
class SqlIoVirtualFileStat(BaseSqlServerMetric):
    TABLE = 'sys.dm_io_virtual_file_stats'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = (
        "select DB_NAME(database_id) as name, database_id, file_id, {{custom_cols}} from {table}(null, null)".format(
            table=TABLE
        )
    )
    OPERATION_NAME = 'io_virtual_file_stats_metrics'

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None, engine_edition=None):
        # since we want the database name we need to update the SQL query at runtime with our custom columns
        # multiple formats on a string are harmless
        extra_cols = ', '.join(col for col in counters_list)
        cls.QUERY_BASE = cls.QUERY_BASE.format(custom_cols=extra_cols)
        return cls._fetch_generic_values(cursor, None, logger)

    def __init__(self, cfg_instance, base_name, report_function, column, logger):
        super(SqlIoVirtualFileStat, self).__init__(cfg_instance, base_name, report_function, column, logger)
        self.dbid = self.cfg_instance.get('database_id', None)
        self.dbname = self.cfg_instance.get('database', None)
        self.fid = self.cfg_instance.get('file_id', None)
        self.pvs_vals = defaultdict(lambda: None)

    def fetch_metric(self, rows, columns, values_cache=None):
        # TODO - fix this function
        #  this function actually processes the change in value between two checks,
        #  but doesn't account for time differences.  This can work for some columns like `num_of_writes`, but is
        #  inaccurate for others like `io_stall_write_ms` which are not monotonically increasing.
        dbid_ndx = columns.index("database_id")
        dbname_ndx = columns.index("name")
        fileid_ndx = columns.index("file_id")
        column_ndx = columns.index(self.column)
        for row in rows:
            dbid = row[dbid_ndx]
            dbname = row[dbname_ndx]
            fid = row[fileid_ndx]
            value = row[column_ndx]

            if self.dbid and self.dbid != dbid:
                continue
            if self.dbname and self.dbname != dbname:
                continue
            if self.fid and self.fid != fid:
                continue
            if not self.pvs_vals[dbid, fid]:
                self.pvs_vals[dbid, fid] = value
                continue

            report_value = value - self.pvs_vals[dbid, fid]
            self.pvs_vals[dbid, fid] = value
            metric_tags = [
                'database:{}'.format(str(dbname).strip()),
                'db:{}'.format(str(dbname).strip()),
                'database_id:{}'.format(str(dbid).strip()),
                'file_id:{}'.format(str(fid).strip()),
            ]
            metric_tags.extend(self.tags)
            metric_name = '{}.{}'.format(self.metric_name, self.column)
            self.report_function(metric_name, report_value, tags=metric_tags)


# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-memory-clerks-transact-sql
class SqlOsMemoryClerksStat(BaseSqlServerMetric):
    TABLE = 'sys.dm_os_memory_clerks'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """select * from {table} where type in ({{placeholders}})""".format(table=TABLE)
    OPERATION_NAME = 'os_memory_clerks_stat_metrics'

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None, engine_edition=None):
        return cls._fetch_generic_values(cursor, counters_list, logger)

    def fetch_metric(self, rows, columns, values_cache=None):
        type_column_index = columns.index("type")
        value_column_index = columns.index(self.column)
        memnode_index = columns.index("memory_node_id")

        sum_by_memory_node_id = defaultdict(int)
        for row in rows:
            column_val = row[value_column_index]
            node_id = row[memnode_index]
            met_type = row[type_column_index]
            if met_type != self.sql_name:
                continue
            sum_by_memory_node_id[node_id] += column_val

        for memory_node_id, column_val in sum_by_memory_node_id.items():
            metric_tags = ['memory_node_id:{}'.format(memory_node_id)]
            metric_tags.extend(self.tags)
            metric_name = '{}.{}'.format(self.metric_name, self.column)
            self.report_function(metric_name, column_val, tags=metric_tags)


DEFAULT_PERFORMANCE_TABLE = "sys.dm_os_performance_counters"
VALID_TABLES = {cls.TABLE for cls in BaseSqlServerMetric.__subclasses__() if cls.CUSTOM_QUERIES_AVAILABLE}
TABLE_MAPPING = {
    cls.TABLE: (cls.DEFAULT_METRIC_TYPE, cls)
    for cls in BaseSqlServerMetric.__subclasses__()
    if cls.TABLE != DEFAULT_PERFORMANCE_TABLE
}
