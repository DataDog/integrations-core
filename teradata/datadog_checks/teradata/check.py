# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing, contextmanager
from typing import Any

import pyodbc
import teradatasql
import json

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
from .queries import DB_SPACE, PCT_SPACE_BY_DB
from .values_sanitizer import get_row_sanitizer

DEFAULT_QUERIES = [DB_SPACE, PCT_SPACE_BY_DB]


class TeradataCheck(AgentCheck):
    __NAMESPACE__ = 'teradata'
    JDBC_CONNECTION_STRING = "jdbc:teradata://{}/{},{}"
    TERADATA_DRIVER_CLASS = "com.teradata.jdbc.TeraDriver"

    def __init__(self, name, init_config, instances):
        super(TeradataCheck, self).__init__(name, init_config, instances)

        self.config = TeradataConfig(self.instance)
        self._connection = None
        self._query_manager = QueryManager(self, self.execute_query_raw, queries=DEFAULT_QUERIES)
        self.check_initializations.append(self._query_manager.compile_queries)
        self._service_check_tags = ['teradata_host:{}'.format(self.config.host)] + self.config.tags

    def check(self, _):
        # type: (Any) -> None
        with self.connect() as conn:
            self._connection = conn
            self._query_manager.execute()

    def execute_query_raw(self, query):
        with closing(self._connection.cursor()) as cursor:
            cursor.execute(query)
            if cursor.rowcount < 1:
                self.log.warning("Failed to fetch records from query: `%s`.", query)
                return []
            sanitizer_method = get_row_sanitizer(query)

            for row in cursor.fetchall():
                try:
                    yield sanitizer_method(row)
                except Exception:
                    self.log.debug("Unable to sanitize row %r.", exc_info=True)
                    yield row

    @contextmanager
    def connect(self):
        try:
            if self.config.use_jdbc:
                return self.connect_jdbc()
            if self.config.use_odbc:
                return self.connect_odbc()
            else:
                return self.connect_non_odbc()
        except Exception as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, msg=e, tags=self._service_check_tags)
            self.log.error('Failed to connect to Teradata database. %s', e)
            raise

    def connect_odbc(self):
        conn = None
        connection_string = self._gen_odbc_conn_string()
        self.log.debug('Connecting to Teradata via ODBC with connection_string: %s.', connection_string)
        try:
            conn = pyodbc.connect(connection_string, timeout=self.config.timeout, autocommit=True)
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._service_check_tags)
            self.log.debug('Connected to Teradata.')
            yield conn
        except Exception as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL)
            self.log.exception('Unable to connect to Teradata database. %e', e)
            raise
        finally:
            if conn:
                conn.close()

    def connect_non_odbc(self):
        conn = None
        self.log.debug('Connecting to Teradata via teradatasql driver...')
        conn_params = {
            'host': self.config.host,
            'user': self.config.username,
            'password': self.config.password,
            'account': self.config.account,
            'database': self.config.db,
            'dbs_port': str(self.config.port),
            'https_port': str(self.config.https_port),
            'sslca': self.config.ssl_ca,
            'sslcapath': self.config.ssl_ca_path,
            'sslmode': self.config.ssl_mode,
            'sslprotocol': self.config.ssl_protocol
        }
        try:
            conn = teradatasql.connect(json.dumps(conn_params))
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._service_check_tags)
            self.log.debug('Connected to Teradata.')
            yield conn
        except Exception as e:
            self.log.exception('Unable to connect via teradatasql driver. %s.', e)
            raise
        finally:
            if conn:
                conn.close()

    def _gen_odbc_conn_string(self):
        conn_str = 'RECONNECTCOUNT=2;CHARSET=UTF8;USEREGIONALSETTINGS=N;'
        try:
            normalized_cs = self._validate_custom_connection_options()

            if self.config.connection_string:
                conn_str += normalized_cs
            if self.config.dsn:
                conn_str += 'DSN={};'.format(self.config.dsn)
            if self.config.account:
                conn_str += 'ACCOUNTSTR={};'.format(self.config.account)
            if self.config.host:
                conn_str += 'DBCNAME={};'.format(self.config.host)
            if self.config.db:
                conn_str += 'DATABASE={};'.format(self.config.db)
            if self.config.driver:
                conn_str += 'DRIVER={};'.format(self.config.driver)
            if self.config.username:
                conn_str += 'USERNAME={};'.format(self.config.username)
            if self.config.password:
                conn_str += 'PASSWORD={};'.format(self.config.password)
            if self.config.use_tls and self.config.https_port:
                conn_str += 'HTTPS_PORT={};'.format(self.config.https_port)
            if self.config.ssl_mode:
                conn_str += 'SSLMODE={}'.format(self.config.ssl_mode)
            if self.config.ssl_ca:
                conn_str += 'SSLCA={};'.format(self.config.ssl_ca)
            if self.config.ssl_ca_path:
                conn_str += 'SSLCAPATH={}'.format(self.config.ssl_ca_path)
            if self.config.mechanism_key:
                conn_str += 'MECHANISMKEY={};'.format(self.config.mechanism_key)
            if self.config.mechanism_name:
                conn_str += 'MECHANISMNAME={};'.format(self.config.mechanism_name)

            return conn_str

        except Exception:
            self.log.error('Error occurred while constructing connection string. Check configuration options.')
            raise

    def _validate_custom_connection_options(self):
        normalized_cs = self._normalize_conn_str(self.config.connection_string)

        odbc_options = {
            'dsn': ['DSN'],
            'account': ['ACCOUNTSTR', 'ACCOUNT'],
            'dbc_name': ['DBCNAME'],
            'db': ['DEFAULTDATABASE', 'DATABASE'],
            'driver': ['DRIVER'],
            'username': ['USERNAME', 'UID'],
            'password': ['PASSWORD', 'PWD'],
            'https_port': ['HTTPS_PORT'],
            'ssl_mode': ['SSLMODE'],
            'ssl_protocol': ['SSLPROTOCOL'],
            'ssl_ca': ['SSLCA'],
            'ssl_ca_path': ['SSLCAPATH'],
            'mechanism_key': ['MECHANISMKEY', 'AUTHENTICATIONPARAMETER'],
            'mechanism_name': ['MECHANISMNAME', 'AUTHENTICATION'],
        }

        required_options = ['dbc_name', 'driver', 'username', 'password']

        for option, values in odbc_options.items():
            for value in values:
                if option in required_options and self.config.get(option) is None:
                    raise ConfigurationError("Configuration option %s is required.")
                if value in normalized_cs and self.config.get(option) is not None:
                    raise ConfigurationError(
                        "%s has been provided both in the connection string and as a configuration"
                        " option (%s), please specify it only once." % (value, option)
                    )

        return normalized_cs

    def _normalize_conn_str(self, conn_str):
        default_options = {
            'RECONNECTCOUNT': '2',
            'CHARSET': 'UTF8',
            'USEREGIONALSETTINGS': 'N'
        }

        raw_cs = conn_str.split(';')

        for index, config in enumerate(raw_cs):
            raw_cs[index] = config.split('=')
            option = raw_cs[index][0]
            if option.upper() in default_options:
                self.log.debug("Connection string option %s is ignored. Default setting is %s.", option, default_options[option])
                raw_cs.remove(raw_cs[index])
            else:
                raw_cs[index][0] = option.upper()
                raw_cs[index] = '='.join(raw_cs[index])

        normalized_cs = ';'.join(raw_cs)
        return normalized_cs

    def connect_jdbc(self):
        conn = None
        jdbc_connect_properties = {'user': self.config.username, 'password': self.config.password}
        conn_str = self.JDBC_CONNECTION_STRING.format(self.config.host, self.config.username, self.config.password)
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
            self.log.debug("Connected to Teradata Database using JDBC Connector")
            yield conn
        except Exception as e:
            self.log.error("Failed to connect to Teradata Database using JDBC Connector. %s", e)
            raise
        finally:
            if conn:
                conn.close()
