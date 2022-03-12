# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
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

from .common import SERVICE_CHECK_NAME
from .config import TeradataConfig
from .queries import DEFAULT_QUERIES


class TeradataCheck(AgentCheck):
    __NAMESPACE__ = 'teradata'
    JDBC_CONNECTION_STRING = "jdbc:teradata://{}"
    TERADATA_DRIVER_CLASS = "com.teradata.jdbc.TeraDriver"

    def __init__(self, name, init_config, instances):
        super(TeradataCheck, self).__init__(name, init_config, instances)

        self.config = TeradataConfig(self.instance)
        self._connection = None
        self._query_manager = QueryManager(self, self._execute_query_raw, queries=DEFAULT_QUERIES, tags=self._tags)
        self.check_initializations.append(self._query_manager.compile_queries)
        self._tags = ['teradata_server:{}'.format(self.config.server)] + self.config.tags
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
                return []
            else:
                for row in results:
                    yield row

    @contextmanager
    def _connect(self):
        try:
            return self._connect_jdbc()
        except Exception as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, msg=e, tags=self._tags)
            self.log.error('Failed to connect to Teradata database. %s', e)
            raise

    def _connect_jdbc(self):
        conn = None
        jdbc_connect_properties = {'user': self.config.username, 'password': self.config.password}
        conn_str = self._connection_string()
        try:
            if jpype.isJVMStarted() and not jpype.isThreadAttachedToJVM():
                jpype.attachThreadToJVM()
                jpype.java.lang.Thread.currentThread().setContextClassLoader(
                    jpype.java.lang.ClassLoader.getSystemClassLoader()
                )
            self.log.debug('Connecting to Teradata Database using JDBC Connector with connection string: %s', conn_str)
            conn = jdb.connect(
                self.TERADATA_DRIVER_CLASS, conn_str, jdbc_connect_properties, self.config.jdbc_driver_path
            )
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._tags)
            self.log.debug("Connected to Teradata Database.")
            yield conn
        except Exception as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.WARN, msg=e, tags=self._tags)
            self.log.error("Failed to connect to Teradata Database using JDBC Connector. %s", e)
            raise
        finally:
            if conn:
                conn.close()

    def _connection_string(self):
        creds_required = self._creds_required()
        if creds_required and (not self.config.username or not self.config.password):
            raise ConfigurationError("`username` and `password` are required")
            return {}
        else:
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

            if not self.config.use_tls:
                config_opts = {
                    'account': self.config.account,
                    'logmech': self.config.auth_mechanism,
                    'logdata': self.config.auth_data,
                }

            param_count = 0
            for option, value in config_opts.items():
                if value is None:
                    continue
                elif param_count < 1:
                    conn_str += '/{}={}'.format(option, value)
                    param_count += 1
                else:
                    conn_str += ',{}={}'.format(option, value)
                    param_count += 1

        return conn_str

    def _creds_required(self):
        optional = ['JWT', 'KRB5', 'LDAP']
        if self.config.auth_mechanism and self.config.auth_mechanism.upper() in optional:
            self._credentials_required = False
        else:
            self._credentials_required = True
        return self._credentials_required
