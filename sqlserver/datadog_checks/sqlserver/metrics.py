# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Collection of metric classes for specific SQL Server tables.
"""
from __future__ import division

from collections import defaultdict

# Queries
ALL_INSTANCES = 'ALL'

INSTANCES_QUERY = """select instance_name
                     from sys.dm_os_performance_counters
                     where counter_name=? and instance_name!='_Total';"""

VALUE_AND_BASE_QUERY = """select counter_name, cntr_type, cntr_value, instance_name, object_name
                          from sys.dm_os_performance_counters
                          where counter_name in (%s)
                          order by cntr_type;"""


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

    def fetch_metric(self, rows, columns):
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
        return rows, None

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


class SqlFractionMetric(SqlServerMetric):
    @classmethod
    def fetch_all_values(cls, cursor, counters_list, logger):
        # TODO - check if counters has anything before actually running query?
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
        return results, None

    def set_instances(self, cursor):
        if self.instance == ALL_INSTANCES:
            cursor.execute(INSTANCES_QUERY, (self.sql_name,))
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

    def fetch_metric(self, rows, columns):
        # TODO - fix this function
        #  this function actually processes the change in value between two checks,
        #  but doesn't account for time differences.  This can work for some columns like `num_of_writes`, but is
        #  inaccurate for others like `io_stall_write_ms` which are not monotonically increasing.
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
            metric_tags.extend(self.tags)
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

    def fetch_metric(self, rows, columns):
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
            metric_tags.extend(self.tags)
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

    def fetch_metric(self, rows, columns):
        session_id_column_index = columns.index("session_id")
        scheduler_id_column_index = columns.index("scheduler_id")
        value_column_index = columns.index(self.column)

        for row in rows:
            column_val = row[value_column_index]
            session_id = row[session_id_column_index]
            scheduler_id = row[scheduler_id_column_index]

            metric_tags = ['session_id:{}'.format(str(session_id)), 'scheduler_id:{}'.format(str(scheduler_id))]
            metric_tags.extend(self.tags)
            metric_name = '{}'.format(self.datadog_name)
            self.report_function(metric_name, column_val, tags=metric_tags)
