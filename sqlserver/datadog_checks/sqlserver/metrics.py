# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Collection of metric classes for specific SQL Server tables.
"""
from __future__ import division

from collections import defaultdict
from functools import partial

from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.time import get_precise_time

from .utils import construct_use_statement

# Queries
ALL_INSTANCES = 'ALL'


class BaseSqlServerMetric(object):
    """Base class for SQL Server metrics collection operations.

    Each subclass defines the TABLE it's associated with, and the default
    query to collect all of the information in one request.  This query gets
    executed as part of the classmethod `fetch_all_values` and the data gets passed
    to the instance method `fetch_metric` which extracts the appropriate metric from
    within the larger collection.

    This approach limits the load on the server during each check run.
    """

    TABLE = None
    DEFAULT_METRIC_TYPE = None
    QUERY_BASE = None

    # Flag to indicate if this subclass/table is available for custom queries
    CUSTOM_QUERIES_AVAILABLE = True

    def __init__(self, cfg_instance, base_name, report_function, column, logger):
        self.cfg_instance = cfg_instance
        self.datadog_name = cfg_instance['name']
        self.sql_name = cfg_instance.get('counter_name', '')
        self.base_name = base_name
        self.report_function = partial(report_function, raw=True)
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
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        raise NotImplementedError

    def fetch_metric(self, rows, columns):
        raise NotImplementedError


# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-performance-counters-transact-sql
class SqlSimpleMetric(BaseSqlServerMetric):
    TABLE = 'sys.dm_os_performance_counters'
    DEFAULT_METRIC_TYPE = None  # can be either rate or gauge
    QUERY_BASE = """select counter_name, instance_name, object_name, cntr_value
                    from {table} where counter_name in ({{placeholders}})""".format(
        table=TABLE
    )

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, counters_list, logger)

    def fetch_metric(self, rows, _):
        for counter_name_long, instance_name_long, object_name, cntr_value in rows:
            counter_name = counter_name_long.strip()
            instance_name = instance_name_long.strip()
            object_name = object_name.strip()
            if counter_name.strip() == self.sql_name:
                matched = False
                metric_tags = list(self.tags)

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


class SqlFractionMetric(BaseSqlServerMetric):
    TABLE = 'sys.dm_os_performance_counters'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """select counter_name, cntr_type, cntr_value, instance_name, object_name
                    from {table}
                    where counter_name in ({{placeholders}})
                    order by cntr_type;""".format(
        table=TABLE
    )

    INSTANCES_QUERY = """select instance_name
                         from {table}
                         where counter_name=? and instance_name!='_Total';""".format(
        table=TABLE
    )

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        placeholders = ', '.join('?' for _ in counters_list)
        query = cls.QUERY_BASE.format(placeholders=placeholders)

        logger.debug("%s: fetch_all executing query: %s, %s", cls.__name__, query, str(counters_list))
        cursor.execute(query, counters_list)
        rows = cursor.fetchall()
        results = defaultdict(list)
        for counter_name, cntr_type, cntr_value, instance_name, object_name in rows:
            rowlist = [cntr_type, cntr_value, instance_name.strip(), object_name.strip()]
            logger.debug("Adding new rowlist %s", str(rowlist))
            results[counter_name.strip()].append(rowlist)
        return results, None

    def set_instances(self, cursor):
        if self.instance == ALL_INSTANCES:
            cursor.execute(self.INSTANCES_QUERY, (self.sql_name,))
            self.instances = [row.instance_name for row in cursor.fetchall()]
        else:
            self.instances = [self.instance]

    def fetch_metric(self, results, _):
        """
        Because we need to query the metrics by matching pairs, we can't query
        all of them together without having to perform some matching based on
        the name afterwards so instead we query instance by instance.
        We cache the list of instance so that we don't have to look it up every time
        """
        if self.sql_name not in results:
            self.log.warning("Couldn't find %s in results", self.sql_name)
            return

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

            metric_tags = list(self.tags)
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


# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-wait-stats-transact-sql
class SqlOsWaitStat(BaseSqlServerMetric):
    TABLE = 'sys.dm_os_wait_stats'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """select * from {table} where wait_type in ({{placeholders}})""".format(table=TABLE)

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, counters_list, logger)

    def fetch_metric(self, rows, columns):
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

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
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

    def fetch_metric(self, rows, columns):
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
                'database_id:{}'.format(str(dbid).strip()),
                'file_id:{}'.format(str(fid).strip()),
            ]
            metric_tags.extend(self.tags)
            metric_name = '{}.{}'.format(self.datadog_name, self.column)
            self.report_function(metric_name, report_value, tags=metric_tags)


# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-memory-clerks-transact-sql
class SqlOsMemoryClerksStat(BaseSqlServerMetric):
    TABLE = 'sys.dm_os_memory_clerks'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """select * from {table} where type in ({{placeholders}})""".format(table=TABLE)

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, counters_list, logger)

    def fetch_metric(self, rows, columns):
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
            metric_name = '{}.{}'.format(self.datadog_name, self.column)
            self.report_function(metric_name, column_val, tags=metric_tags)


# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-schedulers-transact-sql
class SqlOsSchedulers(BaseSqlServerMetric):
    TABLE = 'sys.dm_os_schedulers'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = "select * from {table}".format(table=TABLE)

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, None, logger)

    def fetch_metric(self, rows, columns):
        value_column_index = columns.index(self.column)
        scheduler_index = columns.index("scheduler_id")
        parent_node_index = columns.index("parent_node_id")

        for row in rows:
            column_val = row[value_column_index]
            scheduler_id = row[scheduler_index]
            parent_node_id = row[parent_node_index]

            metric_tags = ['scheduler_id:{}'.format(str(scheduler_id)), 'parent_node_id:{}'.format(str(parent_node_id))]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)


# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-tasks-transact-sql
class SqlOsTasks(BaseSqlServerMetric):
    CUSTOM_QUERIES_AVAILABLE = False
    TABLE = 'sys.dm_os_tasks'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """
    select scheduler_id,
           SUM(CAST(context_switches_count AS BIGINT)) as context_switches_count,
           SUM(CAST(pending_io_count AS BIGINT)) as pending_io_count,
           SUM(pending_io_byte_count) as pending_io_byte_count,
           AVG(pending_io_byte_average) as pending_io_byte_average
    from {table} group by scheduler_id;
    """.format(
        table=TABLE
    )

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, None, logger)

    def fetch_metric(self, rows, columns):
        scheduler_id_column_index = columns.index("scheduler_id")
        value_column_index = columns.index(self.column)

        for row in rows:
            column_val = row[value_column_index]
            scheduler_id = row[scheduler_id_column_index]

            metric_tags = ['scheduler_id:{}'.format(str(scheduler_id))]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)


# https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-master-files-transact-sql
class SqlMasterDatabaseFileStats(BaseSqlServerMetric):
    CUSTOM_QUERIES_AVAILABLE = False
    TABLE = 'sys.master_files'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """
        select sys.databases.name as name, file_id, type, physical_name, size, max_size,
        sys.master_files.state as state, sys.master_files.state_desc as state_desc from {table}
        right outer join sys.databases on sys.master_files.database_id = sys.databases.database_id;
    """.format(
        table=TABLE
    )
    DB_TYPE_MAP = {0: 'data', 1: 'transaction_log', 2: 'filestream', 3: 'unknown', 4: 'full_text'}

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, None, logger)

    def fetch_metric(self, rows, columns):
        db_name = columns.index("name")
        file_id = columns.index("file_id")
        file_type = columns.index("type")
        file_location = columns.index("physical_name")
        db_files_state_desc_index = columns.index("state_desc")
        value_column_index = columns.index(self.column)

        for row in rows:
            column_val = row[value_column_index]
            if column_val is None:
                continue
            if self.column in ('size', 'max_size'):
                column_val *= 8  # size reported in 8 KB pages

            fileid = row[file_id]
            filetype = self.DB_TYPE_MAP[row[file_type]]
            location = row[file_location]
            db_files_state_desc = row[db_files_state_desc_index]
            dbname = row[db_name]

            metric_tags = [
                'database:{}'.format(str(dbname)),
                'file_id:{}'.format(str(fileid)),
                'file_type:{}'.format(str(filetype)),
                'file_location:{}'.format(str(location)),
                'database_files_state_desc:{}'.format(str(db_files_state_desc)),
            ]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)


# https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-database-files-transact-sql
class SqlDatabaseFileStats(BaseSqlServerMetric):
    CUSTOM_QUERIES_AVAILABLE = False
    TABLE = 'sys.database_files'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = "select * from {table}".format(table=TABLE)

    DB_TYPE_MAP = {0: 'data', 1: 'transaction_log', 2: 'filestream', 3: 'unknown', 4: 'full_text'}

    def __init__(self, cfg_instance, base_name, report_function, column, logger):
        super(SqlDatabaseFileStats, self).__init__(cfg_instance, base_name, report_function, column, logger)

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        # special case since this table is specific to databases, need to run query for each database instance
        rows = []
        columns = []

        if databases is None:
            databases = []

        cursor.execute('select DB_NAME()')  # This can return None in some implementations so it cannot be chained
        data = cursor.fetchall()
        current_db = data[0][0]
        logger.debug("%s: current db is %s", cls.__name__, current_db)

        for db in databases:
            # use statements need to be executed separate from select queries
            ctx = construct_use_statement(db)
            try:
                logger.debug("%s: changing cursor context via use statement: %s", cls.__name__, ctx)
                cursor.execute(ctx)
                logger.debug("%s: fetch_all executing query: %s", cls.__name__, cls.QUERY_BASE)
                cursor.execute(cls.QUERY_BASE)
                data = cursor.fetchall()
            except Exception as e:
                logger.warning("Error when trying to query db %s - skipping.  Error: %s", db, e)
                continue

            query_columns = ['database'] + [i[0] for i in cursor.description]
            if columns:
                if columns != query_columns:
                    raise CheckException('Assertion error: {} != {}'.format(columns, query_columns))
            else:
                columns = query_columns

            results = []
            # insert database name as new column for each row
            for row in data:
                r = list(row)
                r.insert(0, db)
                results.append(r)

            rows.extend(results)

            logger.debug("%s: received %d rows and %d columns for db %s", cls.__name__, len(data), len(columns), db)

        # reset back to previous db
        logger.debug("%s: reverting cursor context via use statement to %s", cls.__name__, current_db)
        cursor.execute(construct_use_statement(current_db))

        return rows, columns

    def fetch_metric(self, rows, columns):
        try:
            db_name = columns.index('database')
            file_id = columns.index("file_id")
            file_type = columns.index("type")
            file_location = columns.index("physical_name")
            db_files_state_desc_index = columns.index("state_desc")
            value_column_index = columns.index(self.column)
        except ValueError as e:
            raise CheckException(
                "Could not fetch all required information from columns {}:\n\t{}".format(str(columns), str(e))
            )

        for row in rows:
            if row[db_name] != self.instance:
                continue
            column_val = row[value_column_index]
            if self.column in ('size', 'max_size'):
                column_val *= 8  # size reported in 8 KB pages

            fileid = row[file_id]
            filetype = self.DB_TYPE_MAP[row[file_type]]
            location = row[file_location]
            db_files_state_desc = row[db_files_state_desc_index]

            metric_tags = [
                'database:{}'.format(str(self.instance)),
                'file_id:{}'.format(str(fileid)),
                'file_type:{}'.format(str(filetype)),
                'file_location:{}'.format(str(location)),
                'database_files_state_desc:{}'.format(str(db_files_state_desc)),
            ]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)


class SqlVirtualFileIOStats(BaseSqlServerMetric):
    CUSTOM_QUERIES_AVAILABLE = False
    QUERY_BASE = """
        SELECT
            DB_NAME(fs.database_id) AS database_name,
            mf.state_desc AS state_desc,
            mf.name AS logical_name,
            mf.physical_name AS physical_name,
            fs.num_of_reads AS num_of_reads,
            fs.num_of_bytes_read AS num_of_bytes_read,
            fs.io_stall_read_ms AS io_stall_read_ms,
            fs.io_stall_queued_read_ms AS io_stall_queued_read_ms,
            fs.num_of_writes AS num_of_writes,
            fs.num_of_bytes_written AS num_of_bytes_written,
            fs.io_stall_write_ms AS io_stall_write_ms,
            fs.io_stall_queued_write_ms AS io_stall_queued_write_ms,
            fs.io_stall AS io_stall,
            fs.size_on_disk_bytes AS size_on_disk_bytes
        FROM sys.dm_io_virtual_file_stats(NULL, NULL) fs
            LEFT JOIN sys.master_files mf
                ON mf.database_id = fs.database_id
                AND mf.file_id = fs.file_id;
    """

    def __init__(self, cfg_instance, base_name, report_function, column, logger):
        super(SqlVirtualFileIOStats, self).__init__(cfg_instance, base_name, report_function, column, logger)

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, None, logger)

    def fetch_metric(self, rows, columns):
        db_name = columns.index('database_name')
        state_desc = columns.index('state_desc')
        logical_name = columns.index('logical_name')
        physical_name = columns.index('physical_name')
        column_val = columns.index(self.column)

        for row in rows:
            val = row[column_val]
            if column_val is None:
                continue

            metric_tags = [
                'database:{}'.format(row[db_name]),
                'state:{}'.format(row[state_desc].lower()),
                'logical_name:{}'.format(row[logical_name]),
                'file_location:{}'.format(row[physical_name]),
            ]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, val, tags=metric_tags)


# https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-databases-transact-sql?view=sql-server-ver15
class SqlDatabaseStats(BaseSqlServerMetric):
    CUSTOM_QUERIES_AVAILABLE = False
    TABLE = 'sys.databases'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = "select * from {table}".format(table=TABLE)

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, None, logger)

    def fetch_metric(self, rows, columns):
        database_name = columns.index("name")
        db_state_desc_index = columns.index("state_desc")
        value_column_index = columns.index(self.column)

        for row in rows:
            if row[database_name] != self.instance:
                continue

            column_val = row[value_column_index]
            db_state_desc = row[db_state_desc_index]
            metric_tags = [
                'database:{}'.format(str(self.instance)),
                'database_state_desc:{}'.format(str(db_state_desc)),
            ]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)


# msdb.dbo.backupset
#
# Contains a row for each backup set. A backup set
# contains the backup from a single, successful backup operation.
# https://docs.microsoft.com/en-us/sql/relational-databases/system-tables/backupset-transact-sql?view=sql-server-ver15
class SqlDatabaseBackup(BaseSqlServerMetric):
    CUSTOM_QUERIES_AVAILABLE = False
    TABLE = 'msdb.dbo.backupset'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """
        select sys.databases.name as database_name, count(backup_set_id) as backup_set_id_count
        from {table} right outer join sys.databases
        on sys.databases.name = msdb.dbo.backupset.database_name
        group by sys.databases.name""".format(
        table=TABLE
    )

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, None, logger)

    def fetch_metric(self, rows, columns):
        database_name = columns.index("database_name")
        value_column_index = columns.index(self.column)

        for row in rows:
            if row[database_name] != self.instance:
                continue

            column_val = row[value_column_index]
            metric_tags = [
                'database:{}'.format(str(self.instance)),
            ]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)


# sys.dm_os_cluster_nodes
#
# Returns one row for each node in the failover cluster instance configuration.
# If the current server instance is not a failover clustered instance, it
# returns an empty rowset.
# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-cluster-nodes-transact-sql?view=sql-server-ver15
class SqlFailoverClusteringInstance(BaseSqlServerMetric):
    CUSTOM_QUERIES_AVAILABLE = False
    TABLE = 'sys.dm_os_cluster_nodes'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """select * from {table}""".format(table=TABLE)

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, None, logger)

    def fetch_metric(self, rows, columns):
        value_column_index = columns.index(self.column)
        node_name_index = columns.index("NodeName")

        for row in rows:
            column_val = row[value_column_index]
            node_name = row[node_name_index]
            metric_tags = ['node_name:{}'.format(str(node_name))]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)


# sys.dm_db_index_physical_stats
#
# Returns size and fragmentation information for the data and
# indexes of the specified table or view in SQL Server.
#
# There are reports of this query being very slow for large datasets,
# so debug query timing are included to help monitor it.
# https://dba.stackexchange.com/q/76374
#
# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-db-index-physical-stats-transact-sql?view=sql-server-ver15
class SqlDbFragmentation(BaseSqlServerMetric):
    CUSTOM_QUERIES_AVAILABLE = False
    TABLE = 'sys.dm_db_index_physical_stats'
    DEFAULT_METRIC_TYPE = 'gauge'

    QUERY_BASE = (
        "select DB_NAME(database_id) as database_name, OBJECT_NAME(object_id) as object_name, "
        "index_id, partition_number, fragment_count, avg_fragment_size_in_pages, "
        "avg_fragmentation_in_percent "
        "from {table} (DB_ID('{{db}}'),null,null,null,null) "
        "where fragment_count is not null".format(table=TABLE)
    )

    def __init__(self, cfg_instance, base_name, report_function, column, logger):
        super(SqlDbFragmentation, self).__init__(cfg_instance, base_name, report_function, column, logger)

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        # special case to limit this query to specific databases and monitor performance
        rows = []
        columns = []
        if databases is None:
            databases = []

        logger.debug("%s: gathering fragmentation metrics for these databases: %s", cls.__name__, databases)

        for db in databases:
            query = cls.QUERY_BASE.format(db=db)
            logger.debug("%s: fetch_all executing query: %s", cls.__name__, query)
            start = get_precise_time()
            try:
                cursor.execute(query)
                data = cursor.fetchall()
            except Exception as e:
                logger.warning("Error when trying to query db %s - skipping.  Error: %s", db, e)
                continue
            elapsed = get_precise_time() - start

            query_columns = [i[0] for i in cursor.description]
            if columns:
                if columns != query_columns:
                    raise CheckException('Assertion error: {} != {}'.format(columns, query_columns))
            else:
                columns = query_columns

            rows.extend(data)
            logger.debug("%s: received %d rows for db %s, elapsed time: %.4f sec", cls.__name__, len(data), db, elapsed)

        return rows, columns

    def fetch_metric(self, rows, columns):
        value_column_index = columns.index(self.column)
        database_name = columns.index("database_name")
        object_name_index = columns.index("object_name")
        index_id_index = columns.index("index_id")

        for row in rows:
            if row[database_name] != self.instance:
                continue

            column_val = row[value_column_index]
            object_name = row[object_name_index]
            index_id = row[index_id_index]

            object_list = self.cfg_instance.get('db_fragmentation_object_names')

            if object_list and (object_name not in object_list):
                continue

            metric_tags = [
                'database_name:{}'.format(str(self.instance)),
                'object_name:{}'.format(str(object_name)),
                'index_id:{}'.format(str(index_id)),
            ]

            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)


# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-hadr-database-replica-states-transact-sql?view=sql-server-ver15
class SqlDbReplicaStates(BaseSqlServerMetric):
    TABLE = 'sys.dm_hadr_database_replica_states'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """select * from {table} as dhdrs
                 inner join sys.availability_groups as ag
                 on ag.group_id = dhdrs.group_id
                 inner join sys.availability_replicas as ar
                 on dhdrs.replica_id = ar.replica_id""".format(
        table=TABLE
    )

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, None, logger)

    def fetch_metric(self, rows, columns):
        value_column_index = columns.index(self.column)
        sync_state_desc_index = columns.index('synchronization_state_desc')
        resource_group_id_index = columns.index('resource_group_id')
        resource_group_name_index = columns.index('name')
        replica_server_name_index = columns.index('replica_server_name')
        is_local_index = columns.index('is_local')

        for row in rows:
            is_local = row[is_local_index]
            resource_group_id = row[resource_group_id_index]
            resource_group_name = row[resource_group_name_index]
            selected_ag = self.cfg_instance.get('availability_group')

            if self.cfg_instance.get('only_emit_local') and not is_local:
                continue

            elif selected_ag and selected_ag != resource_group_id:
                continue

            column_val = row[value_column_index]
            sync_state_desc = row[sync_state_desc_index]
            replica_server_name = row[replica_server_name_index]

            metric_tags = [
                'synchronization_state_desc:{}'.format(str(sync_state_desc)),
                'replica_server_name:{}'.format(str(replica_server_name)),
                'availability_group:{}'.format(str(resource_group_id)),
                'availability_group_name:{}'.format(str(resource_group_name)),
            ]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)

            self.report_function(metric_name, column_val, tags=metric_tags)


# sys.dm_hadr_availability_group_states
# Returns a row for each Always On availability group that possesses an availability replica on the local instance of
# SQL Server. Each row displays the states that define the health of a given availability group.
#
# https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-hadr-availability-group-states-transact-sql?view=sql-server-ver15
class SqlAvailabilityGroups(BaseSqlServerMetric):
    TABLE = 'sys.dm_hadr_availability_group_states'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """select * from {table} as dhdrcs
                    inner join sys.availability_groups as ag
                    on ag.group_id = dhdrcs.group_id""".format(
        table=TABLE
    )

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, None, logger)

    def fetch_metric(self, rows, columns):
        value_column_index = columns.index(self.column)

        resource_group_id_index = columns.index('resource_group_id')
        resource_group_name_index = columns.index('name')
        sync_health_desc_index = columns.index('synchronization_health_desc')

        for row in rows:
            resource_group_id = row[resource_group_id_index]
            resource_group_name = row[resource_group_name_index]
            selected_ag = self.cfg_instance.get('availability_group')

            if selected_ag and selected_ag != resource_group_id:
                continue

            column_val = row[value_column_index]
            sync_health_desc = row[sync_health_desc_index]
            metric_tags = [
                'availability_group:{}'.format(str(resource_group_id)),
                'availability_group_name:{}'.format(str(resource_group_name)),
                'synchronization_health_desc:{}'.format(str(sync_health_desc)),
            ]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)

            self.report_function(metric_name, column_val, tags=metric_tags)


# sys.availability_replicas (Transact-SQL)
#
# Returns a row for each of the availability replicas that belong to any Always On availability group in the WSFC
# failover cluster. If the local server instance is unable to talk to the WSFC failover cluster, for example because
# the cluster is down or quorum has been lost, only rows for local availability replicas are returned.
# These rows will contain only the columns of data that are cached locally in metadata.
#
# https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-availability-replicas-transact-sql?view=sql-server-ver15
class SqlAvailabilityReplicas(BaseSqlServerMetric):
    TABLE = 'sys.availability_replicas'
    DEFAULT_METRIC_TYPE = 'gauge'
    QUERY_BASE = """select * from {table} as ar
                    inner join sys.dm_hadr_database_replica_cluster_states as dhdrcs
                    on ar.replica_id = dhdrcs.replica_id
                    inner join sys.dm_hadr_database_replica_states as dhdrs
                    on ar.replica_id = dhdrs.replica_id
                    inner join sys.availability_groups as ag
                    on ag.group_id = ar.group_id""".format(
        table=TABLE
    )

    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger, databases=None):
        return cls._fetch_generic_values(cursor, None, logger)

    def fetch_metric(self, rows, columns):
        value_column_index = columns.index(self.column)

        failover_mode_desc_index = columns.index('failover_mode_desc')
        replica_server_name_index = columns.index('replica_server_name')
        resource_group_id_index = columns.index('resource_group_id')
        resource_group_name_index = columns.index('name')
        is_local_index = columns.index('is_local')
        database_name_index = columns.index('database_name')
        try:
            is_primary_replica_index = columns.index('is_primary_replica')
        except ValueError:
            # This column only supported in SQL Server 2014 and later
            is_primary_replica_index = None

        for row in rows:
            is_local = row[is_local_index]
            resource_group_id = row[resource_group_id_index]
            resource_group_name = row[resource_group_name_index]
            database_name = row[database_name_index]
            selected_ag = self.cfg_instance.get('availability_group')
            selected_database = self.cfg_instance.get('ao_database')
            if self.cfg_instance.get('only_emit_local') and not is_local:
                continue

            elif selected_ag and selected_ag != resource_group_id:
                continue

            elif selected_database and selected_database != database_name:
                continue

            column_val = row[value_column_index]
            failover_mode_desc = row[failover_mode_desc_index]
            replica_server_name = row[replica_server_name_index]
            resource_group_id = row[resource_group_id_index]

            metric_tags = [
                'replica_server_name:{}'.format(str(replica_server_name)),
                'availability_group:{}'.format(str(resource_group_id)),
                'availability_group_name:{}'.format(str(resource_group_name)),
                'failover_mode_desc:{}'.format(str(failover_mode_desc)),
            ]
            if is_primary_replica_index is not None:
                is_primary_replica = row[is_primary_replica_index]
                metric_tags.append('is_primary_replica:{}'.format(str(is_primary_replica)))
            else:
                metric_tags.append('is_primary_replica:unknown')

            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)

            self.report_function(metric_name, column_val, tags=metric_tags)


DEFAULT_PERFORMANCE_TABLE = "sys.dm_os_performance_counters"
VALID_TABLES = set(cls.TABLE for cls in BaseSqlServerMetric.__subclasses__() if cls.CUSTOM_QUERIES_AVAILABLE)
TABLE_MAPPING = {
    cls.TABLE: (cls.DEFAULT_METRIC_TYPE, cls)
    for cls in BaseSqlServerMetric.__subclasses__()
    if cls.TABLE != DEFAULT_PERFORMANCE_TABLE
}
