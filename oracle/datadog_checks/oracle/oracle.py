# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import OrderedDict
from contextlib import closing

import cx_Oracle
import jaydebeapi as jdb
import jpype

from datadog_checks.checks import AgentCheck
from datadog_checks.config import is_affirmative

from . import queries

EVENT_TYPE = SOURCE_TYPE_NAME = 'oracle'
MAX_CUSTOM_RESULTS = 100


class OracleConfigError(Exception):
    pass


class Oracle(AgentCheck):

    ORACLE_DRIVER_CLASS = "oracle.jdbc.OracleDriver"
    JDBC_CONNECT_STRING = "jdbc:oracle:thin:@//{}/{}"
    CX_CONNECT_STRING = "{}/{}@//{}/{}"

    SERVICE_CHECK_NAME = 'oracle.can_connect'
    SYS_METRICS = {
        'Buffer Cache Hit Ratio': 'oracle.buffer_cachehit_ratio',
        'Cursor Cache Hit Ratio': 'oracle.cursor_cachehit_ratio',
        'Library Cache Hit Ratio': 'oracle.library_cachehit_ratio',
        'Shared Pool Free %': 'oracle.shared_pool_free',
        'Physical Reads Per Sec': 'oracle.physical_reads',
        'Physical Writes Per Sec': 'oracle.physical_writes',
        'Enqueue Timeouts Per Sec': 'oracle.enqueue_timeouts',
        'GC CR Block Received Per Second': 'oracle.gc_cr_block_received',
        'Global Cache Blocks Corrupted': 'oracle.cache_blocks_corrupt',
        'Global Cache Blocks Lost': 'oracle.cache_blocks_lost',
        'Logons Per Sec': 'oracle.logons',
        'Average Active Sessions': 'oracle.active_sessions',
        'Long Table Scans Per Sec': 'oracle.long_table_scans',
        'SQL Service Response Time': 'oracle.service_response_time',
        'User Rollbacks Per Sec': 'oracle.user_rollbacks',
        'Total Sorts Per User Call': 'oracle.sorts_per_user_call',
        'Rows Per Sort': 'oracle.rows_per_sort',
        'Disk Sort Per Sec': 'oracle.disk_sorts',
        'Memory Sorts Ratio': 'oracle.memory_sorts_ratio',
        'Database Wait Time Ratio': 'oracle.database_wait_time_ratio',
        'Session Limit %': 'oracle.session_limit_usage',
        'Session Count': 'oracle.session_count',
        'Temp Space Used': 'oracle.temp_space_used',
    }

    PROCESS_METRICS = OrderedDict(
        [
            ('PGA_USED_MEM', 'oracle.process.pga_used_memory'),
            ('PGA_ALLOC_MEM', 'oracle.process.pga_allocated_memory'),
            ('PGA_FREEABLE_MEM', 'oracle.process.pga_freeable_memory'),
            ('PGA_MAX_MEM', 'oracle.process.pga_maximum_memory'),
        ]
    )

    def check(self, instance):
        server, user, password, service, jdbc_driver, tags, custom_queries = self._get_config(instance)

        if not server or not user:
            raise OracleConfigError("Oracle host and user are needed")

        service_check_tags = ['server:%s' % server]
        service_check_tags.extend(tags)

        with closing(self._get_connection(server, user, password, service, jdbc_driver, service_check_tags)) as con:
            self._get_sys_metrics(con, tags)
            self._get_process_metrics(con, tags)
            self._get_tablespace_metrics(con, tags)
            self._get_custom_metrics(con, custom_queries, tags)

    def _get_config(self, instance):
        server = instance.get('server')
        user = instance.get('user')
        password = instance.get('password')
        service = instance.get('service_name')
        jdbc_driver = instance.get('jdbc_driver_path')
        tags = instance.get('tags') or []
        custom_queries = instance.get('custom_queries', [])
        if is_affirmative(instance.get('use_global_custom_queries', True)):
            custom_queries.extend(self.init_config.get('global_custom_queries', []))

        return server, user, password, service, jdbc_driver, tags, custom_queries

    def _get_connection(self, server, user, password, service, jdbc_driver, tags):
        try:
            # Check if the instantclient is available
            cx_Oracle.clientversion()
        except cx_Oracle.DatabaseError as e:
            # Fallback to JDBC
            use_oracle_client = False
            self.log.debug('Oracle instant client unavailable, falling back to JDBC: {}'.format(e))
            connect_string = self.JDBC_CONNECT_STRING.format(server, service)
        else:
            use_oracle_client = True
            self.log.debug('Running cx_Oracle version {0}'.format(cx_Oracle.version))
            connect_string = self.CX_CONNECT_STRING.format(user, password, server, service)

        try:
            if use_oracle_client:
                con = cx_Oracle.connect(connect_string)
            else:
                try:
                    if jpype.isJVMStarted() and not jpype.isThreadAttachedToJVM():
                        jpype.attachThreadToJVM()
                        jpype.java.lang.Thread.currentThread().setContextClassLoader(
                            jpype.java.lang.ClassLoader.getSystemClassLoader()
                        )
                    con = jdb.connect(self.ORACLE_DRIVER_CLASS, connect_string, [user, password], jdbc_driver)
                except Exception as e:
                    if "Class {} not found".format(self.ORACLE_DRIVER_CLASS) in str(e):
                        msg = """Cannot run the Oracle check until either the Oracle instant client or the JDBC Driver
                        is available.
                        For the Oracle instant client, see:
                        http://www.oracle.com/technetwork/database/features/instant-client/index.html
                        You will also need to ensure the `LD_LIBRARY_PATH` is also updated so the libs are reachable.

                        For the JDBC Driver, see:
                        http://www.oracle.com/technetwork/database/application-development/jdbc/downloads/index.html
                        You will also need to ensure the jar is either listed in your $CLASSPATH or in the yaml
                        configuration file of the check.
                        """
                        self.log.error(msg)
                    raise

            self.log.debug("Connected to Oracle DB")
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=tags)
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=tags)
            self.log.error(e)
            raise
        return con

    def _get_custom_metrics(self, con, custom_queries, global_tags):
        for custom_query in custom_queries:
            metric_prefix = custom_query.get('metric_prefix')
            if not metric_prefix:
                self.log.error('custom query field `metric_prefix` is required')
                continue
            metric_prefix = metric_prefix.rstrip('.')

            query = custom_query.get('query')
            if not query:
                self.log.error('custom query field `query` is required for metric_prefix `{}`'.format(metric_prefix))
                continue

            columns = custom_query.get('columns')
            if not columns:
                self.log.error('custom query field `columns` is required for metric_prefix `{}`'.format(metric_prefix))
                continue

            with closing(con.cursor()) as cursor:
                cursor.execute(query)
                for row in cursor.fetchall():
                    if len(columns) != len(row):
                        self.log.error(
                            'query result for metric_prefix {}: expected {} columns, got {}'.format(
                                metric_prefix, len(columns), len(row)
                            )
                        )
                        break

                    metric_info = []
                    query_tags = list(custom_query.get('tags', []))
                    query_tags.extend(global_tags)

                    errored = True
                    for column, value in zip(columns, row):
                        # Columns can be ignored via configuration.
                        if column:
                            name = column.get('name')
                            if not name:
                                self.log.error(
                                    'column field `name` is required for metric_prefix `{}`'.format(metric_prefix)
                                )
                                break

                            column_type = column.get('type')
                            if not column_type:
                                self.log.error(
                                    'column field `type` is required for column `{}` '
                                    'of metric_prefix `{}`'.format(name, metric_prefix)
                                )
                                break

                            if column_type == 'tag':
                                query_tags.append('{}:{}'.format(name, value))
                            else:
                                if not hasattr(self, column_type):
                                    self.log.error(
                                        'invalid submission method `{}` for column `{}` of '
                                        'metric_prefix `{}`'.format(column_type, name, metric_prefix)
                                    )
                                    break
                                try:
                                    metric_info.append(('{}.{}'.format(metric_prefix, name), float(value), column_type))
                                except (ValueError, TypeError):
                                    self.log.error(
                                        'non-numeric value `{}` for metric column `{}` of '
                                        'metric_prefix `{}`'.format(value, name, metric_prefix)
                                    )
                                    break

                    # Only submit metrics if there were absolutely no errors - all or nothing.
                    else:
                        errored = False
                        for info in metric_info:
                            metric, value, method = info
                            getattr(self, method)(metric, value, tags=query_tags)

                    if errored:
                        # If we failed to parse one row of the results, there is no reason to continue
                        break

    def _get_sys_metrics(self, con, tags):
        with closing(con.cursor()) as cur:
            cur.execute(queries.SYSTEM)
            for row in cur.fetchall():
                metric_name = row[0]
                metric_value = row[1]
                if metric_name in self.SYS_METRICS:
                    self.gauge(self.SYS_METRICS[metric_name], metric_value, tags=tags)

    def _get_process_metrics(self, con, tags):
        with closing(con.cursor()) as cur:
            cur.execute(queries.PROCESS.format(','.join(self.PROCESS_METRICS.keys())))
            for row in cur.fetchall():
                # Oracle program name
                program_tag = ['program:{}'.format(row[0])]

                # Get the metrics
                for i, metric_name in enumerate(self.PROCESS_METRICS.values(), 1):
                    metric_value = row[i]
                    self.gauge(metric_name, metric_value, tags=tags + program_tag)

    def _get_tablespace_metrics(self, con, tags):
        with closing(con.cursor()) as cur:
            cur.execute(queries.TABLESPACE)
            for tablespace_name, used_bytes, max_bytes, used_percent in cur.fetchall():
                tablespace_tags = ['tablespace:{}'.format(tablespace_name)]
                tablespace_tags.extend(tags)
                if used_bytes is None:
                    # mark tablespace as offline if null
                    offline = 1
                    used = 0
                else:
                    offline = 0
                    used = float(used_bytes)
                if max_bytes is None:
                    size = 0
                else:
                    size = float(max_bytes)
                if used_percent is None:
                    in_use = 0
                else:
                    in_use = float(used_percent)

                self.gauge('oracle.tablespace.used', used, tags=tablespace_tags)
                self.gauge('oracle.tablespace.size', size, tags=tablespace_tags)
                self.gauge('oracle.tablespace.in_use', in_use, tags=tablespace_tags)
                self.gauge('oracle.tablespace.offline', offline, tags=tablespace_tags)
