# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import time
from contextlib import closing, contextmanager
from copy import deepcopy

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

SERVICE_CHECK_CONNECT = 'can_connect'
SERVICE_CHECK_QUERY = 'can_query'


class TeradataCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'teradata'

    def __init__(self, name, init_config, instances):
        super(TeradataCheck, self).__init__(name, init_config, instances)

        self._connect_params = None
        self._connection = None
        self._tags = None
        self._query_errors = 0
        self._tables_filter = None

        manager_queries = deepcopy(DEFAULT_QUERIES)
        if is_affirmative(self.instance.get('collect_res_usage', False)):
            manager_queries.extend(COLLECT_RES_USAGE)
        if is_affirmative(self.instance.get('enable_table_tags', False)):
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
        with self.connect() as conn:
            if conn:
                self._connection = conn
                self._query_manager.execute()

        self.submit_health_checks()

    def initialize_config(self):
        self._connect_params = json.dumps(
            {
                'host': self.config.server,
                'account': self.config.account,
                'database': self.config.database,
                'dbs_port': str(self.config.port),
                'logmech': self.config.auth_mechanism.upper(),
                'logdata': self.config.auth_data,
                'user': self.config.username,
                'password': self.config.password,
                'https_port': str(self.config.https_port),
                'sslmode': self.config.ssl_mode.upper(),
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

        self._tables_filter = self._create_tables_filter()

    def _execute_query_raw(self, query):
        with closing(self._connection.cursor()) as cursor:
            query = query.format(self.config.database)
            cursor.execute(query)
            if cursor.rowcount < 1:
                self._query_errors += 1
                self.log.warning('Failed to fetch records from query: `%s`.', query)
                return None
            for row in cursor.fetchall():
                try:
                    yield self._queries_handler(row, query)
                except Exception as e:
                    self.log.debug('Unable to process row, skipping row. %s', e)
                    yield row

    def _executor_error_handler(self, error):
        self._query_errors += 1
        return error

    @contextmanager
    def connect(self):
        conn = None
        if TERADATASQL_IMPORT_ERROR:
            self.service_check(SERVICE_CHECK_CONNECT, ServiceCheck.CRITICAL, tags=self._tags)
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
            self.service_check(SERVICE_CHECK_CONNECT, ServiceCheck.CRITICAL, tags=self._tags)
            self.log.error('Unable to connect to Teradata. %s.', e)
            raise e
        finally:
            if conn:
                conn.close()

    def submit_health_checks(self):
        connect_status = ServiceCheck.OK
        query_status = ServiceCheck.OK

        if self._query_errors:
            query_status = ServiceCheck.CRITICAL

        self.service_check(SERVICE_CHECK_CONNECT, connect_status, tags=self._tags)
        self.service_check(SERVICE_CHECK_QUERY, query_status, tags=self._tags)

    def _queries_handler(self, row, query):
        """
        Perform timestamp validation and filter tables.
        Only rows returned from the Resource Usage table include timestamps.
        Only rows returned from the AllSpaceV table (disk space) tag by table.
        """
        processed_row = row
        if 'DBC.ResSpmaView' in query:
            processed_row = self._timestamp_validator(row)

        if 'TableName' in query and is_affirmative(self.config.enable_table_tags):
            processed_row = self._filter_tables(row)
        return processed_row

    def _filter_tables(self, row):
        tables_to_collect, tables_to_exclude = self._tables_filter
        table_name = row[3]

        if not tables_to_collect and not tables_to_exclude:
            return row
        if table_name in tables_to_exclude:
            return []
        if table_name in tables_to_collect:
            return row
        return []

    def _create_tables_filter(self):
        """
        List of strings
        Mapping of `include` (list of strings) and `exclude` (list of strings)
        """
        tables_to_collect = set()
        tables_to_exclude = set()

        tables = self.config.tables

        if isinstance(tables, list):
            tables_to_collect = set(tables)

        if isinstance(tables, dict):
            include_tables = tables.get('include')
            exclude_tables = tables.get('exclude')

            if include_tables and exclude_tables:
                for table in include_tables:
                    if table not in exclude_tables:
                        tables_to_collect.add(table)
                tables_to_exclude = set(exclude_tables)
                return tables_to_collect, tables_to_exclude

            if include_tables:
                tables_to_collect = set(include_tables)

            if exclude_tables:
                tables_to_exclude = set(exclude_tables)

        return tables_to_collect, tables_to_exclude

    def _timestamp_validator(self, row):
        # Only rows returned from the Resource Usage table include timestamps
        now = time.time()
        row_ts = row[0]
        if type(row_ts) is not int:
            msg = 'Returned timestamp `{}` is invalid.'.format(row_ts)
            self.log.warning(msg)
            self._query_errors += 1
            return []
        diff = now - row_ts
        # Valid metrics should be no more than 10 min in the future or 1h in the past
        if (diff > 3600) or (diff < -600):
            msg = 'Resource Usage stats are invalid. {}'
            if diff > 3600:
                msg = msg.format('Row timestamp is more than 1h in the past. Is `SPMA` Resource Usage Logging enabled?')
            elif diff < -600:
                msg = msg.format('Row timestamp is more than 10 min in the future. Try checking system time settings.')
            self.log.warning(msg)
            self._query_errors += 1
            return []
        return row
