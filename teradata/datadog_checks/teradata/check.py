# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from contextlib import closing, contextmanager

try:
    import jaydebeapi as jdb
    import jpype

    JDBC_IMPORT_ERROR = None
except ImportError as e:
    jdb = None
    jpype = None
    JDBC_IMPORT_ERROR = e


from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.db import QueryManager

from .config import TeradataConfig
from .queries import COLLECT_RES_USAGE, DEFAULT_QUERIES


class TeradataCheck(AgentCheck):
    __NAMESPACE__ = 'teradata'
    JDBC_CONNECTION_STRING = "jdbc:teradata://{}"
    TERADATA_DRIVER_CLASS = "com.teradata.jdbc.TeraDriver"
    SERVICE_CHECK_CONNECT = "can_connect"

    def __init__(self, name, init_config, instances):
        super(TeradataCheck, self).__init__(name, init_config, instances)
        self.config = TeradataConfig(self.instance)
        self._server_tag = 'teradata_server:{}:{}'.format(self.config.server, self.config.port)
        self._tags = [self._server_tag] + self.config.tags

        self._connection = None

        manager_queries = []
        if self.config.collect_res_usage:
            manager_queries.extend(COLLECT_RES_USAGE)
        else:
            manager_queries.extend(DEFAULT_QUERIES)

        self._query_manager = QueryManager(self, self._execute_query_raw, queries=manager_queries, tags=self._tags)
        self.check_initializations.append(self._query_manager.compile_queries)

        self._credentials_required = True

    def check(self, _):
        with self._connect() as conn:
            self._connection = conn
            self._query_manager.execute()

    def _execute_query_raw(self, query):
        with closing(self._connection.cursor()) as cursor:
            query = query.format(self.config.db)
            cursor.execute(query)
            results = cursor.fetchall()
            if len(results) < 1:
                self.log.warning("Failed to fetch records from query: `%s`.", query)
            else:
                for row in results:
                    yield self._validate_timestamp(row, query)

    @contextmanager
    def _connect(self):
        if JDBC_IMPORT_ERROR:
            err_msg = """
            Teradata JDBC Client is unavailable and the integration is unable to import JDBC libraries.
            Please double check your installation and refer to the Datadog documentation for more information."""
            self.log.error(err_msg)
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.CRITICAL, message=err_msg, tags=self._tags)
            raise JDBC_IMPORT_ERROR
        else:
            try:
                return self._connect_jdbc()
            except Exception as e:
                self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.CRITICAL, message=e, tags=self._tags)
                self.log.error('Failed to connect to Teradata database. %s', e)
                raise

    def _connect_jdbc(self):
        conn = None
        conn_str = self._connection_string()
        jdbc_connect_properties = self._connect_properties()
        try:
            if jpype.isJVMStarted() and not jpype.java.lang.Thread.isAttached():
                jpype.attachThreadToJVM()
                jpype.java.lang.Thread.currentThread().setContextClassLoader(
                    jpype.java.lang.ClassLoader.getSystemClassLoader()
                )
            self.log.debug('Connecting to Teradata Database using JDBC Connector with connection string: %s', conn_str)
            conn = jdb.connect(
                self.TERADATA_DRIVER_CLASS, conn_str, jdbc_connect_properties, self.config.jdbc_driver_path
            )
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.OK, tags=self._tags)
            self.log.debug("Connected to Teradata Database.")
            yield conn
        except Exception as e:
            self.log.error("Failed to connect to Teradata Database using JDBC Connector. %s", e)
            raise
        finally:
            if conn:
                conn.close()

    def _connection_string(self):
        conn_str = self.JDBC_CONNECTION_STRING.format(self.config.server)
        config_opts = {
            'account': self.config.account,
            'dbs_port': self.config.port,
            'https_port': self.config.https_port,
            'sslmode': self.config.ssl_mode,
            'sslprotocol': self.config.ssl_protocol,
            'sslca': self.config.ssl_ca,
            'sslcapath': self.config.ssl_ca_path,
            'logmech': self.config.auth_mechanism,
            'logdata': self.config.auth_data,
        }

        param_count = 0
        for option, value in sorted(config_opts.items()):
            if value is None:
                if option == 'logdata' and not self._credentials_required:
                    raise ConfigurationError(
                        "`auth_data` is required for auth_mechanisms JWT, KRB5, and LDAP. "
                        "Configured `auth_mechanism` is: %s",
                        self.config.auth_mechanism,
                    )
                else:
                    continue
            elif param_count < 1:
                conn_str += '/{}={}'.format(option, value)
                param_count += 1
            else:
                conn_str += ',{}={}'.format(option, value)
                param_count += 1

        return conn_str

    def _connect_properties(self):
        jdbc_connect_properties = {}
        optional = ['JWT', 'KRB5', 'LDAP', 'TDNEGO']
        if self.config.auth_mechanism and self.config.auth_mechanism.upper() in optional:
            self._credentials_required = False
        elif self._credentials_required and (not self.config.username or not self.config.password):
            raise ConfigurationError("`username` and `password` are required")
            return
        else:
            jdbc_connect_properties.update({'user': self.config.username, 'password': self.config.password})
        return jdbc_connect_properties

    def _validate_timestamp(self, row, query):
        if 'DBC.ResSpmaView' in query:
            now = time.time()
            row_ts = row[0]
            diff = now - row_ts
            # Valid metrics should be no more than 10 min in the future or 1h in the past
            if (diff > 3600) or (diff < -600):
                msg = 'Resource Usage stats are invalid. {}'
                if diff > 3600:
                    msg = msg.format(
                        "Row timestamp is more than 1h in the past. Is `SPMA` Resource Usage Logging enabled?"
                    )
                elif diff < -600:
                    msg = msg.format(
                        "Row timestamp is more than 10 min in the future. Try checking system time settings."
                    )
                self.log.warning(msg)
                self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.WARNING, message=msg, tags=self._tags)
                raise Exception(msg)
        return row
