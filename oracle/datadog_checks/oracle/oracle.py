# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import itertools
from contextlib import closing

import cx_Oracle

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.db import QueryManager

from . import queries

try:
    import jaydebeapi as jdb
    import jpype

    JDBC_IMPORT_ERROR = None
except ImportError as e:
    jdb = None
    jpype = None
    JDBC_IMPORT_ERROR = e


EVENT_TYPE = SOURCE_TYPE_NAME = 'oracle'
MAX_CUSTOM_RESULTS = 100


class Oracle(AgentCheck):
    __NAMESPACE__ = 'oracle'

    ORACLE_DRIVER_CLASS = "oracle.jdbc.OracleDriver"
    JDBC_CONNECT_STRING = "jdbc:oracle:thin:@//{}/{}"
    CX_CONNECT_STRING = "{}/{}@//{}/{}"

    SERVICE_CHECK_NAME = 'can_connect'

    def __init__(self, name, init_config, instances):
        super(Oracle, self).__init__(name, init_config, instances)
        self._server = self.instance.get('server')
        self._user = self.instance.get('user')
        self._password = self.instance.get('password')
        self._service = self.instance.get('service_name')
        self._jdbc_driver = self.instance.get('jdbc_driver_path')
        self._tags = self.instance.get('tags') or []
        self._service_check_tags = ['server:{}'.format(self._server)]
        self._service_check_tags.extend(self._tags)

        self._cached_connection = None

        manager_queries = []
        if not self.instance.get('only_custom_queries', False):
            manager_queries.extend([queries.ProcessMetrics, queries.SystemMetrics, queries.TableSpaceMetrics])

        self._fix_custom_queries()

        self._query_manager = QueryManager(
            self,
            self.execute_query_raw,
            queries=manager_queries,
            error_handler=self.handle_query_error,
            tags=self._tags,
        )

        self.check_initializations.append(self.validate_config)
        self.check_initializations.append(self._query_manager.compile_queries)

        self._current_errors = 0

    def _fix_custom_queries(self):
        """
        For backward compatibility reasons, if a custom query specifies a
        `metric_prefix`, change the submission name to contain it.
        """
        custom_queries = self.instance.get('custom_queries', [])
        global_custom_queries = self.init_config.get('global_custom_queries', [])
        for query in itertools.chain(custom_queries, global_custom_queries):
            prefix = query.get('metric_prefix')
            if prefix and prefix != self.__NAMESPACE__:
                if prefix.startswith(self.__NAMESPACE__ + '.'):
                    prefix = prefix[len(self.__NAMESPACE__) + 1 :]
                for column in query.get('columns', []):
                    if column.get('type') != 'tag':
                        column['name'] = '{}.{}'.format(prefix, column['name'])

    def validate_config(self):
        if not self._server or not self._user:
            raise ConfigurationError("Oracle host and user are needed")

    def execute_query_raw(self, query):
        with closing(self._connection.cursor()) as cursor:
            cursor.execute(query)
            # JDBC doesn't support iter protocol
            return cursor.fetchall()

    def handle_query_error(self, error):
        self._current_errors += 1
        self._cached_connection = None

        return error

    def check(self, _):
        self._current_errors = 0

        self._query_manager.execute()

        if self._current_errors:
            self.service_check(self.SERVICE_CHECK_NAME, self.CRITICAL, tags=self._service_check_tags)
        else:
            self.service_check(self.SERVICE_CHECK_NAME, self.OK, tags=self._service_check_tags)

    @property
    def _connection(self):
        if self._cached_connection is None:
            try:
                # Check if the instantclient is available
                cx_Oracle.clientversion()
            except cx_Oracle.DatabaseError as e:
                # Fallback to JDBC
                use_oracle_client = False
                self.log.debug('Oracle instant client unavailable, falling back to JDBC: %s', e)
                connect_string = self.JDBC_CONNECT_STRING.format(self._server, self._service)
            else:
                use_oracle_client = True
                self.log.debug('Running cx_Oracle version %s', cx_Oracle.version)
                connect_string = self.CX_CONNECT_STRING.format(self._user, self._password, self._server, self._service)

            if use_oracle_client:
                connection = cx_Oracle.connect(connect_string)
            elif JDBC_IMPORT_ERROR:
                self.log.error(
                    "Oracle client is unavailable and the integration is unable to import JDBC libraries. You may not "
                    "have the Microsoft Visual C++ Runtime 2015 installed on your system. Please double check your "
                    "installation and refer to the Datadog documentation for more information."
                )
                raise JDBC_IMPORT_ERROR
            else:
                try:
                    if jpype.isJVMStarted() and not jpype.isThreadAttachedToJVM():
                        jpype.attachThreadToJVM()
                        jpype.java.lang.Thread.currentThread().setContextClassLoader(
                            jpype.java.lang.ClassLoader.getSystemClassLoader()
                        )
                    connection = jdb.connect(
                        self.ORACLE_DRIVER_CLASS, connect_string, [self._user, self._password], self._jdbc_driver
                    )
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
            self._cached_connection = connection

        return self._cached_connection
