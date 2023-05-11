# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing, contextmanager
from typing import Any, AnyStr, Dict, Iterable, Iterator, List, Sequence, cast  # noqa: F401

import pymysql

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager
from datadog_checks.singlestore.config import SingleStoreConfig
from datadog_checks.singlestore.queries import (
    AGGREGATORS,
    LEAVES,
    MV_GLOBAL_STATUS,
    SYSINFO_CPU,
    SYSINFO_DISK,
    SYSINFO_MEM,
    SYSINFO_NET,
    VERSION_METADATA,
)
from datadog_checks.singlestore.values_cleaner import get_row_cleaner

DEFAULT_QUERIES = [MV_GLOBAL_STATUS, AGGREGATORS, LEAVES, VERSION_METADATA]
ADDITIONAL_SYSTEM_QUERIES = [SYSINFO_CPU, SYSINFO_DISK, SYSINFO_MEM, SYSINFO_NET]


class SinglestoreCheck(AgentCheck):

    SERVICE_CHECK_NAME = "can_connect"
    __NAMESPACE__ = "singlestore"

    def __init__(self, name, init_config, instances):
        # type: (AnyStr, Dict[AnyStr, Any], List[Dict[AnyStr, Any]]) -> None
        super(SinglestoreCheck, self).__init__(name, init_config, instances)
        self.config = SingleStoreConfig(self.instance)
        self._connection = cast(pymysql.Connection, None)

        manager_queries = []
        manager_queries.extend(DEFAULT_QUERIES)
        if self.config.collect_system_metrics:
            manager_queries.extend(ADDITIONAL_SYSTEM_QUERIES)
        self._query_manager = QueryManager(self, self.execute_query_raw, queries=manager_queries, tags=self.config.tags)
        self.check_initializations.append(self._query_manager.compile_queries)
        self._service_check_tags = [
            'singlestore_endpoint:{}:{}'.format(self.config.host, self.config.port)
        ] + self.config.tags

    def check(self, _):
        # type: (Any) -> None
        with self.connect() as conn:
            self._connection = conn
            self._query_manager.execute()
            self._connection = cast(pymysql.Connection, None)

    def execute_query_raw(self, query):
        # type: (AnyStr) -> Iterable[Sequence]
        with closing(self._connection.cursor()) as cursor:
            cursor.execute(query)
            if cursor.rowcount < 1:
                self.log.warning("Failed to fetch records from query: `%s`.", query)
                return

            cleaner_method = get_row_cleaner(query)

            for row in cursor.fetchall():
                try:
                    yield cleaner_method(row)
                except Exception:
                    self.log.debug("Unable to clean row %r.", exc_info=True)
                    yield row

    @contextmanager
    def connect(self):
        # type: () ->  Iterator[pymysql.Connection]
        ssl_context = self.get_tls_context() if self.config.use_tls else None

        conn = cast(pymysql.Connection, None)
        try:
            conn = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                connect_timeout=self.config.connect_timeout,
                read_timeout=self.config.read_timeout,
                ssl=ssl_context,
            )
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._service_check_tags)
            self.log.debug("Connected to SingleStore")
            yield conn
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._service_check_tags)
            self.log.exception("Cannot connect to SingleStore")
            raise
        finally:
            if conn:
                conn.close()
