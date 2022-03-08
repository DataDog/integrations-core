# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing, contextmanager
from typing import Any

import pyodbc

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager

from .common import SERVICE_CHECK_NAME
from .config import TeradataConfig
from .queries import DB_SPACE, PCT_SPACE_BY_DB
from .values_sanitizer import get_row_sanitizer

DEFAULT_QUERIES = [DB_SPACE, PCT_SPACE_BY_DB]


class TeradataCheck(AgentCheck):
    __NAMESPACE__ = 'teradata'

    def __init__(self, name, init_config, instances):
        super(TeradataCheck, self).__init__(name, init_config, instances)

        self.config = TeradataConfig(self.instance)
        self._connection = None
        self._query_manager = QueryManager(self, self.execute_query_raw, queries=DEFAULT_QUERIES)
        self.check_initializations.append(self._query_manager.compile_queries)

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
        conn = None
        connection_string = self._gen_conn_string()

        try:
            conn = pyodbc.connect(connection_string, timeout=self.config.timeout, autocommit=True)
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK)
            self.log.debug('Connected to Teradata')
            yield conn
        except Exception as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL)
            self.log.exception('Unable to connect. Error is %s', e)
            raise
        finally:
            if conn:
                conn.close()

    def _gen_conn_string(self):
        conn_str = 'RECONNECTCOUNT=2;CHARSET=UTF8;USEREGIONALSETTINGS=N;'
        if self.config.connection_string:
            conn_str += self.config.connection_string
            return conn_str
        if self.config.dsn:
            conn_str += 'DSN={};'.format(self.config.dsn)
        if self.config.account:
            conn_str += 'ACCOUNTSTR={};'.format(self.config.account)
        if self.config.dbc_name:
            conn_str += 'DBCNAME={};'.format(self.config.dbc_name)
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
            conn_str += 'SSLMode={}'.format(self.config.ssl_mode)
        if self.config.ssl_ca:
            conn_str += 'SSLCA={};'.format(self.config.ssl_ca)
        if self.config.ssl_ca_path:
            conn_str += 'SSLCAPath={}'.format(self.config.ssl_ca_path)
        if self.config.mechanism_key:
            conn_str += 'MECHANISMKEY={};'.format(self.config.mechanism_key)
        if self.config.mechanism_name:
            conn_str += 'MECHANISMNAME={};'.format(self.config.mechanism_name)
        return conn_str
