# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import re
from contextlib import closing, contextmanager
from copy import deepcopy
from typing import Any, AnyStr, Iterable, Iterator, Sequence  # noqa: F401

try:
    import teradatasql

    TERADATASQL_IMPORT_ERROR = None
except ImportError as e:
    teradatasql = None
    TERADATASQL_IMPORT_ERROR = e

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.utils.db import QueryManager

from .config_models import ConfigMixin
from .queries import COLLECT_ALL_SPACE, COLLECT_RES_USAGE, DEFAULT_QUERIES
from .utils import create_tables_filter, filter_tables, submit_version, tags_normalizer, timestamp_validator

SERVICE_CHECK_CONNECT = 'can_connect'
SERVICE_CHECK_QUERY = 'can_query'


class TeradataCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'teradata'

    def __init__(self, name, init_config, instances):
        super(TeradataCheck, self).__init__(name, init_config, instances)

        self._connect_params = None
        self._connection = None
        self._tags = []
        self._query_errors = 0
        self._tables_filter = None

        manager_queries = deepcopy(DEFAULT_QUERIES)
        if is_affirmative(self.instance.get('collect_res_usage_metrics', False)):
            manager_queries.extend(COLLECT_RES_USAGE)
        if is_affirmative(self.instance.get('collect_table_disk_metrics', False)):
            manager_queries.extend(COLLECT_ALL_SPACE)

        self._query_manager = QueryManager(
            self,
            self._execute_query_raw,
            queries=manager_queries,
            tags=self._tags,
            error_handler=self._executor_error_handler,
        )
        self.check_initializations.append(self.initialize_config)
        self.check_initializations.append(self._query_manager.compile_queries)

    def check(self, _):
        # type: (Any) -> None
        self._query_errors = 0

        try:
            with self.connect() as conn:
                if conn:
                    self._connection = conn
                    self._query_manager.execute()
            self.submit_health_checks()
        except Exception as e:
            self.service_check(SERVICE_CHECK_CONNECT, ServiceCheck.CRITICAL, tags=self._tags)
            raise e

    def initialize_config(self):
        # type: (Any) -> None
        self._connect_params = json.dumps(
            {
                'host': self.config.server,
                'account': self.config.account,
                'database': self.config.database,
                'dbs_port': str(self.config.port),
                'logmech': self.config.auth_mechanism,
                'logdata': self.config.auth_data,
                'user': self.config.username,
                'password': self.config.password,
                'https_port': str(self.config.https_port),
                'sslmode': self.config.ssl_mode,
                'sslprotocol': self.config.ssl_protocol,
            }
        )

        global_tags = [
            'teradata_server:{}'.format(self.instance.get('server')),
            'teradata_port:{}'.format(self.instance.get('port', 1025)),
        ]
        self._tags = list(self.config.tags)
        self._tags.extend(global_tags)
        self._query_manager.tags = self._tags

        self._tables_filter = create_tables_filter(self.config.tables)

    def _execute_query_raw(self, query):
        # type: (AnyStr) -> Iterable[Sequence]
        with closing(self._connection.cursor()) as cursor:
            query = query.format(self.config.database)
            cursor.execute(query)
            if cursor.rowcount < 1:
                self._query_errors += 1
                self.log.warning('Failed to fetch records from query: `%s`.', query)
                return None
            for row in cursor.fetchall():
                query_name = re.search(r'(DBC.[^\s]+)', query).group(1)
                try:
                    yield self._queries_processor(row, query_name)
                except Exception as e:
                    self.log.debug(
                        'Unable to process row returned from query "%s", skipping row %s. %s', query_name, row, e
                    )
                    yield row

    def _executor_error_handler(self, error):
        # type: (AnyStr) -> AnyStr
        self._query_errors += 1
        return error

    @contextmanager
    def connect(self):
        # type: () -> Iterator[teradatasql.connection]
        conn = None
        if TERADATASQL_IMPORT_ERROR:
            self.log.error(
                'Teradata SQL Driver module is unavailable. Please double check your installation and refer to the '
                'Datadog documentation for more information. %s',
                TERADATASQL_IMPORT_ERROR,
            )
            raise TERADATASQL_IMPORT_ERROR
        self.log.info('Connecting to Teradata database %s on server %s.', self.config.database, self.config.server)
        try:
            conn = teradatasql.connect(self._connect_params)
            self.log.info('Connected to Teradata.')
            yield conn
        except Exception as e:
            self.log.error('Unable to connect to Teradata. %s.', e)
            raise e
        finally:
            if conn:
                conn.close()

    def submit_health_checks(self):
        # type: () -> None
        connect_status = ServiceCheck.OK
        query_status = ServiceCheck.CRITICAL if self._query_errors else ServiceCheck.OK

        self.service_check(SERVICE_CHECK_QUERY, query_status, tags=self._tags)
        self.service_check(SERVICE_CHECK_CONNECT, connect_status, tags=self._tags)

    def _queries_processor(self, row, query_name):
        # type: (Sequence, AnyStr) -> Sequence
        """
        Validate timestamps, filter tables, and normalize empty tags.
        """
        unprocessed_row = row

        # Return database version immediately
        if query_name == 'DBC.DBCInfoV':
            submit_version(self, row)
            return unprocessed_row

        # Only Resource Usage rows include timestamps and also do not include tags.
        if query_name == 'DBC.ResSpmaView':
            processed_row = timestamp_validator(self, unprocessed_row)
            return processed_row

        # Only AllSpaceV rows include table tags
        if (
            query_name == 'DBC.AllSpaceV'
            and is_affirmative(self.config.collect_table_disk_metrics)
            and self._tables_filter
        ):
            tables_filtered_row = filter_tables(self._tables_filter, unprocessed_row)
            if tables_filtered_row:
                processed_row = tags_normalizer(tables_filtered_row, query_name)
                return processed_row
            # Discard row if empty (table is filtered out)
            return tables_filtered_row
        processed_row = tags_normalizer(unprocessed_row, query_name)
        self.log.trace('Row processor returned: %s. \nFrom query: "%s"', processed_row, query_name)
        return processed_row
