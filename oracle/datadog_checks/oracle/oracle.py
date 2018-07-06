# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
from contextlib import closing
from collections import OrderedDict

# 3rd party
import jaydebeapi as jdb
import jpype
import cx_Oracle

# project
from datadog_checks.checks import AgentCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'oracle'


class OracleConfigError(Exception):
    pass


class Oracle(AgentCheck):

    ORACLE_DRIVER_CLASS = "oracle.jdbc.OracleDriver"
    JDBC_CONNECT_STRING = "jdbc:oracle:thin:@//{}/{}"
    CX_CONNECT_STRING = "{}/{}@//{}/{}"

    SERVICE_CHECK_NAME = 'oracle.can_connect'
    SYS_METRICS = {
        'Buffer Cache Hit Ratio':           'oracle.buffer_cachehit_ratio',
        'Cursor Cache Hit Ratio':           'oracle.cursor_cachehit_ratio',
        'Library Cache Hit Ratio':          'oracle.library_cachehit_ratio',
        'Shared Pool Free %':               'oracle.shared_pool_free',
        'Physical Reads Per Sec':           'oracle.physical_reads',
        'Physical Writes Per Sec':          'oracle.physical_writes',
        'Enqueue Timeouts Per Sec':         'oracle.enqueue_timeouts',
        'GC CR Block Received Per Second':  'oracle.gc_cr_block_received',
        'Global Cache Blocks Corrupted':    'oracle.cache_blocks_corrupt',
        'Global Cache Blocks Lost':         'oracle.cache_blocks_lost',
        'Logons Per Sec':                   'oracle.logons',
        'Average Active Sessions':          'oracle.active_sessions',
        'Long Table Scans Per Sec':         'oracle.long_table_scans',
        'SQL Service Response Time':        'oracle.service_response_time',
        'User Rollbacks Per Sec':           'oracle.user_rollbacks',
        'Total Sorts Per User Call':        'oracle.sorts_per_user_call',
        'Rows Per Sort':                    'oracle.rows_per_sort',
        'Disk Sort Per Sec':                'oracle.disk_sorts',
        'Memory Sorts Ratio':               'oracle.memory_sorts_ratio',
        'Database Wait Time Ratio':         'oracle.database_wait_time_ratio',
        'Session Limit %':                  'oracle.session_limit_usage',
        'Session Count':                    'oracle.session_count',
        'Temp Space Used':                  'oracle.temp_space_used',
    }

    PROCESS_METRICS = OrderedDict([
        ('PGA_USED_MEM', 'oracle.process.pga_used_memory'),
        ('PGA_ALLOC_MEM', 'oracle.process.pga_allocated_memory'),
        ('PGA_FREEABLE_MEM', 'oracle.process.pga_freeable_memory'),
        ('PGA_MAX_MEM', 'oracle.process.pga_maximum_memory')
    ])

    def check(self, instance):
        self.use_oracle_client = True
        server, user, password, service, jdbc_driver, tags, custom_queries = self._get_config(instance)

        if not server or not user:
            raise OracleConfigError("Oracle host and user are needed")

        try:
            # Check if the instantclient is available
            cx_Oracle.clientversion()
            self.log.debug('Running cx_Oracle version {0}'.format(cx_Oracle.version))
        except cx_Oracle.DatabaseError as e:
            # Fallback to JDBC
            self.use_oracle_client = False
            self.log.info('Oracle instant client unavailable, falling back to JDBC: {}'.format(e))

        with closing(self._get_connection(server, user, password, service, jdbc_driver, tags)) as con:
            self._get_sys_metrics(con, tags)
            self._get_process_metrics(con, tags)
            self._get_tablespace_metrics(con, tags)
            self._get_custom_metrics(con, custom_queries, tags)

    def _get_config(self, instance):
        self.server = instance.get('server', None)
        user = instance.get('user', None)
        password = instance.get('password', None)
        service = instance.get('service_name', None)
        jdbc_driver = instance.get('jdbc_driver_path', None)
        tags = instance.get('tags', [])
        custom_queries = instance.get('custom_queries', [])
        return self.server, user, password, service, jdbc_driver, tags, custom_queries

    def _get_connection(self, server, user, password, service, jdbc_driver, tags):
        if tags is None:
            tags = []
        self.service_check_tags = [
            'server:%s' % server
        ] + tags

        if self.use_oracle_client:
            connect_string = self.CX_CONNECT_STRING.format(user, password, server, service)
        else:
            connect_string = self.JDBC_CONNECT_STRING.format(server, service)

        try:
            if self.use_oracle_client:
                con = cx_Oracle.connect(connect_string)
            else:
                try:
                    if jpype.isJVMStarted() and not jpype.isThreadAttachedToJVM():
                        jpype.attachThreadToJVM()
                        jpype.java.lang.Thread.currentThread().setContextClassLoader(
                            jpype.java.lang.ClassLoader.getSystemClassLoader())
                    con = jdb.connect(self.ORACLE_DRIVER_CLASS, connect_string, [user, password], jdbc_driver)
                except jpype.JException(jpype.java.lang.RuntimeException) as e:
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
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                               tags=self.service_check_tags)
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=self.service_check_tags)
            self.log.error(e)
            raise
        return con

    def _get_custom_metrics(self, con, custom_queries, global_tags):
        global_tags = global_tags or []

        for custom_query in custom_queries:
            metric_prefix = custom_query.get('metric_prefix')
            if not metric_prefix:
                self.log.error('custom query field `metric_prefix` is required')
                continue
            metric_prefix = metric_prefix.rstrip('.')

            query = custom_query.get('query')
            if not query:
                self.log.error(
                    'custom query field `query` is required for metric_prefix `{}`'.format(metric_prefix)
                )
                continue

            columns = custom_query.get('columns')
            if not columns:
                self.log.error(
                    'custom query field `columns` is required for metric_prefix `{}`'.format(metric_prefix)
                )
                continue

            with closing(con.cursor()) as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                if row:
                    if len(columns) != len(row):
                        self.log.error(
                            'query result for metric_prefix {}: expected {} columns, got {}'.format(
                                metric_prefix, len(columns), len(row)
                            )
                        )
                        continue

                    metric_info = []
                    query_tags = custom_query.get('tags', [])
                    query_tags.extend(global_tags)

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
                                    metric_info.append((
                                        '{}.{}'.format(metric_prefix, name),
                                        float(value),
                                        column_type
                                    ))
                                except (ValueError, TypeError):
                                    self.log.error(
                                        'non-numeric value `{}` for metric column `{}` of '
                                        'metric_prefix `{}`'.format(value, name, metric_prefix)
                                    )
                                    break

                    # Only submit metrics if there were absolutely no errors - all or nothing.
                    else:
                        for info in metric_info:
                            metric, value, method = info
                            getattr(self, method)(metric, value, tags=query_tags)

    def _get_sys_metrics(self, con, tags):
        if tags is None:
            tags = []
        query = "SELECT METRIC_NAME, VALUE, BEGIN_TIME FROM GV$SYSMETRIC ORDER BY BEGIN_TIME"
        with closing(con.cursor()) as cur:
            cur.execute(query)
            for row in cur.fetchall():
                metric_name = row[0]
                metric_value = row[1]
                if metric_name in self.SYS_METRICS:
                    self.gauge(self.SYS_METRICS[metric_name], metric_value, tags=tags)

    def _get_process_metrics(self, con, tags):
        if tags is None:
            tags = []

        query = "SELECT PROGRAM, {} FROM GV$PROCESS".format(','.join(self.PROCESS_METRICS.keys()))
        with closing(con.cursor()) as cur:
            cur.execute(query)
            for row in cur.fetchall():

                # Oracle program name
                program_tag = ['program:{}'.format(row[0])]

                # Get the metrics
                for i, metric_name in enumerate(self.PROCESS_METRICS.values(), 1):
                    metric_value = row[i]
                    self.gauge(metric_name, metric_value, tags=tags + program_tag)

    def _get_tablespace_metrics(self, con, tags):
        if tags is None:
            tags = []
        query = "SELECT TABLESPACE_NAME, sum(BYTES), sum(MAXBYTES) FROM sys.dba_data_files GROUP BY TABLESPACE_NAME"
        with closing(con.cursor()) as cur:
            cur.execute(query)
            for row in cur.fetchall():
                tablespace_tag = 'tablespace:%s' % row[0]
                if row[1] is None:
                    # mark tablespace as offline if sum(BYTES) is null
                    offline = True
                    used = 0
                else:
                    offline = False
                    used = float(row[1])
                if row[2] is None:
                    size = 0
                else:
                    size = float(row[2])
                if (used >= size):
                    in_use = 100
                elif (used == 0) or (size == 0):
                    in_use = 0
                else:
                    in_use = used / size * 100

                self.gauge('oracle.tablespace.used', used, tags=tags + [tablespace_tag])
                self.gauge('oracle.tablespace.size', size, tags=tags + [tablespace_tag])
                self.gauge('oracle.tablespace.in_use', in_use, tags=tags + [tablespace_tag])
                self.gauge('oracle.tablespace.offline', offline, tags=tags + [tablespace_tag])
