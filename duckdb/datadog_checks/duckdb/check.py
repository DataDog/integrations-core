# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
import json
import time
from typing import Any, AnyStr, Iterable, Iterator, Sequence  # noqa: F401
import duckdb
from contextlib import contextmanager, closing

from datadog_checks.base import AgentCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.utils.db import QueryManager



from .queries import DEFAULT_QUERIES

SERVICE_CHECK_CONNECT = 'can_connect'
SERVICE_CHECK_QUERY = 'can_query'

class DuckdbCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'duckdb'

    def __init__(self, name, init_config, instances):
        super(DuckdbCheck, self).__init__(name, init_config, instances)

        self.db_name = self.instance.get('db_name')
        self.username = self.instance.get('username')
        self.password = self.instance.get('password')
        self.collect_profiling_data = self.instance.get('collect_profiling_data', False)
        self.tags = self.instance.get('tags', [])
        self._connection = None
        self._connect_params = None
        self._tags = []
        self._query_errors = 0

        manager_queries = deepcopy(DEFAULT_QUERIES)

        self._query_manager = QueryManager(
            self,
            self._execute_query_raw,
            queries=manager_queries,
            tags=self.tags,
            error_handler=self._executor_error_handler,
        )
        self.check_initializations.append(self.initialize_config)
        self.check_initializations.append(self._query_manager.compile_queries)


    def check(self, instance):
        try:
            with self.connect() as conn:
                if conn:
                    self._connection = conn
                    self._query_manager.execute()
            self.submit_health_checks()
        except Exception as e:
            self.service_check(SERVICE_CHECK_CONNECT, ServiceCheck.CRITICAL, tags=self._tags)
            raise e

    def _execute_query_raw(self, query):
        # type: (AnyStr) -> Iterable[Sequence]
        with closing(self._connection.cursor()) as cursor:
            query = query.format(self.db_name)
            cursor.execute(query)
            if cursor.rowcount < 1:
                self._query_errors += 1
                self.log.warning('Failed to fetch records from query: `%s`.', query)
                return None
            for row in cursor.fetchall():
                try:
                    yield self._queries_processor(row, query)
                except Exception as e:
                    self.log.debug(
                        'Unable to process row returned from query "%s", skipping row %s. %s', query, row, e
                    )
                    yield row

    def _queries_processor(self, row, query_name):
        # type: (Sequence, AnyStr) -> Sequence
        unprocessed_row = row

        # Return database version 
        if query_name == 'version':
            self.submit_version(row)
            return unprocessed_row

    @contextmanager
    def connect(self):
        conn = None
        retries=3
        delay=5
        for _ in range(retries):
            try:
                # Try to establish the connection
                conn = duckdb.connect(self._connect_params, read_only=True)
                self.log.info('Connected to DuckDB database.')
                yield conn
            except Exception as e:
                if 'Conflicting lock' in str(e):
                    self.log.error('Lock conflict detected, retrying in %s seconds...', delay)
                    time.sleep(delay)
                else:
                    self.log.error('Unable to connect to DuckDB database. %s.', e)
                    raise e
            finally:
                if conn:
                    conn.close()  

    def initialize_config(self):
        self._connect_params = json.dumps(
            {
                'database': self.db_name,
                'username': self.username if self.username is not None else '',
                'password': self.password if self.password is not None else '',
            }
        )
 
    def submit_health_checks(self):
        # Check for connectivity
        connect_status = ServiceCheck.OK
        self.service_check(SERVICE_CHECK_CONNECT, connect_status, tags=self._tags)

        # Check if the ddagent can query the database
        query_status = ServiceCheck.CRITICAL if self._query_errors else ServiceCheck.OK
        self.service_check(SERVICE_CHECK_QUERY, query_status, tags=self._tags)


    @AgentCheck.metadata_entrypoint
    def submit_version(self, row):
        """
        Example version: v1.1.1
        """
        try:
            duckdb_version_row = row[0]
            duckdb_version = duckdb_version_row[1:]
            version_split = duckdb_version(".")

            if len(version_split) >= 3:
                major = version_split[0]
                minor = version_split[1]
                patch = version_split[2]

                version_raw = f'{major}.{minor}.{patch}'

                version_parts = {
                    'major': major,
                    'minor': minor,
                    'patch': patch,
                }
                self.set_metadata('version', version_raw, scheme='parts', final_scheme='semver', part_map=version_parts)
            else:
                self.log.debug("Malformed DuckDB version format: %s", duckdb_version_row)
        except Exception as e:
            self.log.warning("Could not retrieve version metadata: %s", e)

    def _executor_error_handler(self, error):
        # type: (AnyStr) -> AnyStr
        self._query_errors += 1
        return error