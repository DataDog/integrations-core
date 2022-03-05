# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing, contextmanager
from typing import Any

import pyodbc

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager

from .queries import DB_SPACE
from .values_sanitizer import get_row_sanitizer

DEFAULT_QUERIES = [DB_SPACE]


class TeradataCheck(AgentCheck):
    DEFAULT_COMMAND_TIMEOUT = 5
    SERVICE_CHECK_NAME = "teradata.can_connect"
    __NAMESPACE__ = 'teradata'

    def __init__(self, name, init_config, instances):
        super(TeradataCheck, self).__init__(name, init_config, instances)

        self.host = self.instance.get("host", "")
        self.port = self.instance.get("port", "")
        self.username = self.instance.get("username", "")
        self.password = self.instance.get("password", "")
        self.db = self.instance.get("database", "")
        self.odbc_driver = self.instance.get("driver", "")
        self.connection_string = self.instance.get("connection_string", "")
        self.tags = self.instance.get("tags", [])
        self.timeout = int(self.instance.get('command_timeout', self.DEFAULT_COMMAND_TIMEOUT))

        self._connection = None
        # If the check is going to perform SQL queries you should define a query manager here.
        # More info at
        # https://datadoghq.dev/integrations-core/base/databases/#datadog_checks.base.utils.db.core.QueryManager

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
        # ssl_context = self.get_tls_context() if self.config.use_tls else None
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string, timeout=self.timeout, autocommit=True)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)
            self.log.debug('Connected to Teradata')
            yield conn
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL)
            self.log.exception('Unable to connect. Error is %s', e)
            raise
        finally:
            if conn:
                conn.close()
