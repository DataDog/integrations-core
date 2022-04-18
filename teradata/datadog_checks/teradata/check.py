# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import time
from contextlib import closing, contextmanager

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
from .queries import COLLECT_RES_USAGE, DEFAULT_QUERIES

SERVICE_CHECK_CONNECT = 'can_connect'
SERVICE_CHECK_QUERY = 'can_query'


class TeradataCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'teradata'

    def __init__(self, name, init_config, instances):
        super(TeradataCheck, self).__init__(name, init_config, instances)

        self._connect_params = None
        self._connection = None

        self._tags = [
            'teradata_server:{}'.format(self.instance.get('server')),
            'teradata_port:{}'.format(self.instance.get('port', 1025)),
        ]
        self._tags.extend(self.instance.get('tags', []))

        manager_queries = []
        if is_affirmative(self.instance.get('collect_res_usage', False)):
            manager_queries.extend(COLLECT_RES_USAGE)
        else:
            manager_queries.extend(DEFAULT_QUERIES)

        self._query_manager = QueryManager(
            self,
            self._execute_query_raw,
            queries=manager_queries,
            tags=self._tags,
            error_handler=self._executor_error_handler,
        )
        self.check_initializations.append(self.initialize_config)
        self.check_initializations.append(self._query_manager.compile_queries)

        self._connection_errors = 0
        self._query_errors = 0

    def check(self, _):
        with self.connect() as conn:
            if conn:
                self._connection = conn
                self._query_manager.execute()

        self.submit_health_checks()

    def initialize_config(self):
        self._connect_params = {
            'host': self.config.server,
            'account': self.config.account if self.config.account else None,
            'database': self.config.database,
            'dbs_port': str(self.config.port),
            'logmech': self.config.auth_mechanism.upper() if self.config.auth_mechanism else None,
            'logdata': self.config.auth_data if self.config.auth_data else None,
            'user': self.config.username if self.config.username else None,
            'password': self.config.password if self.config.password else None,
            'https_port': str(self.config.https_port) if self.config.https_port else '443',
            'sslmode': self.config.ssl_mode.upper() if self.config.ssl_mode else 'PREFER',
            'sslprotocol': self.config.ssl_protocol if self.config.ssl_protocol else 'TLSv1.2',
        }

    def _execute_query_raw(self, query):
        with closing(self._connection.cursor()) as cursor:
            query = query.format(self.config.database)
            cursor.execute(query)
            if cursor.rowcount < 1:
                self.service_check(SERVICE_CHECK_QUERY, ServiceCheck.CRITICAL, tags=self._tags)
                self.log.warning('Failed to fetch records from query: `%s`.', query)
                return None
            else:
                for row in cursor.fetchall():
                    try:
                        yield self._timestamp_validator(row, query)
                    except Exception:
                        self.log.debug('Unable to validate Resource Usage View timestamp, skipping row.')
                        yield row

    def _executor_error_handler(self, error):
        self._query_errors += 1
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                self.log.warning("Couldn't close the connection after a query failure: %s", str(e))
        self._connection = None
        return error

    @contextmanager
    def connect(self):
        # How to handle service checks when exceptions get raised
        conn = None
        if TERADATASQL_IMPORT_ERROR:
            self.service_check(SERVICE_CHECK_CONNECT, ServiceCheck.CRITICAL, tags=self._tags)
            self.log.error(
                'Teradata SQL Driver module is unavailable. Please double check your installation and refer to the '
                'Datadog documentation for more information. %s',
                TERADATASQL_IMPORT_ERROR,
            )
            raise TERADATASQL_IMPORT_ERROR
        else:
            self.log.debug('Connecting to Teradata...')
            try:
                conn = teradatasql.connect(json.dumps(self._connect_params))
                self.log.debug('Connected to Teradata.')
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

        if self._connection_errors:
            connect_status = ServiceCheck.CRITICAL

        if self._query_errors:
            query_status = ServiceCheck.CRITICAL

        self.service_check(SERVICE_CHECK_CONNECT, connect_status, tags=self._tags)
        self.service_check(SERVICE_CHECK_QUERY, query_status, tags=self._tags)

    def _timestamp_validator(self, row, query):
        # Only rows returned from the Resource Usage table include timestamps
        if 'DBC.ResSpmaView' in query:
            now = time.time()
            row_ts = row[0]
            if type(row_ts) is not int:
                msg = 'Returned timestamp `{}` is invalid.'.format(row_ts)
                self.log.warning(msg)
                self._query_errors += 1
                return []
            else:
                diff = now - row_ts
                # Valid metrics should be no more than 10 min in the future or 1h in the past
                if (diff > 3600) or (diff < -600):
                    msg = 'Resource Usage stats are invalid. {}'
                    if diff > 3600:
                        msg = msg.format(
                            'Row timestamp is more than 1h in the past. Is `SPMA` Resource Usage Logging enabled?'
                        )
                    elif diff < -600:
                        msg = msg.format(
                            'Row timestamp is more than 10 min in the future. Try checking system time settings.'
                        )
                    self.log.warning(msg)
                    self._query_errors += 1
                    return []
        return row
