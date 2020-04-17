# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# CHANGED
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
        (
            self._server,
            self._user,
            self._password,
            self._service,
            self._jdbc_driver,
            self._tags,
            only_custom_queries,
        ) = self._get_config(self.instance)

        self.check_initializations.append(self.validate_config)

        self._connection = None

        manager_queries = []
        if not only_custom_queries:
            manager_queries.extend([queries.ProcessMetrics, queries.SystemMetrics, queries.TableSpaceMetrics])

        self._fix_custom_queries()

        self._query_manager = QueryManager(self, self.execute_query_raw, queries=manager_queries, tags=self._tags,)
        self.check_initializations.append(self._query_manager.compile_queries)

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

    def check(self, _):
        self.create_connection()
        with closing(self._connection):
            self._query_manager.execute()
            self._connection = None

    def _get_config(self, instance):
        server = instance.get('server')
        user = instance.get('user')
        password = instance.get('password')
        service = instance.get('service_name')
        jdbc_driver = instance.get('jdbc_driver_path')
        tags = instance.get('tags') or []
        only_custom_queries = instance.get('only_custom_queries', False)

        return server, user, password, service, jdbc_driver, tags, only_custom_queries

    def create_connection(self):
        service_check_tags = ['server:%s' % self._server]
        service_check_tags.extend(self._tags)

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

        try:
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
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags)
            self.log.error(e)
            raise
        self._connection = connection
