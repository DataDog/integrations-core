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


from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.db import QueryManager

from .config import TeradataConfig
from .queries import COLLECT_RES_USAGE, DEFAULT_QUERIES


class TeradataCheck(AgentCheck):
    __NAMESPACE__ = 'teradata'
    SERVICE_CHECK_CONNECT = 'can_connect'
    SERVICE_CHECK_QUERY = 'can_query'

    def __init__(self, name, init_config, instances):
        super(TeradataCheck, self).__init__(name, init_config, instances)
        self.config = TeradataConfig(self.instance)
        self._connection = None
        self._server_tag = 'teradata_server:{}'.format(self.config.server)
        self._port_tag = 'teradata_port:{}'.format(self.config.port)
        self._tags = [self._server_tag, self._port_tag] + self.config.tags

        manager_queries = []
        if self.config.collect_res_usage:
            manager_queries.extend(COLLECT_RES_USAGE)
        else:
            manager_queries.extend(DEFAULT_QUERIES)

        self._query_manager = QueryManager(self, self._execute_query_raw, queries=manager_queries, tags=self._tags)
        self.check_initializations.append(self._query_manager.compile_queries)

        self._connection_errors = 0
        self._query_errors = 0

    def check(self, _):
        self._connection_errors = 0
        self._query_errors = 0

        with self.connect() as conn:
            self._connection = conn
            self._query_manager.execute()

        if self._connection_errors:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, tags=self._tags)
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)

        if self._query_errors:
            self.service_check(self.SERVICE_CHECK_QUERY, self.CRITICAL, tags=self._tags)
        else:
            self.service_check(self.SERVICE_CHECK_QUERY, self.OK, tags=self._tags)

    def _execute_query_raw(self, query):
        with closing(self._connection.cursor()) as cursor:
            query = query.format(self.config.db)
            cursor.execute(query)
            if cursor.rowcount < 1:
                self.log.warning('Failed to fetch records from query: `%s`.', query)
                self._query_errors += 1
            else:
                for row in cursor.fetchall():
                    try:
                        yield self._validate_timestamp(row, query)
                    except Exception:
                        self.log.debug('Unable to validate Resource Usage View timestamps.')
                        self._query_errors += 1
                        yield row

    @contextmanager
    def connect(self):
        try:
            return self._connect()
        except Exception as e:
            self._connection_errors += 1
            self.log.error('Failed to connect to Teradata database. %s', e)
            raise

    def _connect(self):
        conn = None
        if TERADATASQL_IMPORT_ERROR:
            self.log.error(
                'Teradata SQL Driver module is unavailable. Please double check your installation and refer to the '
                'Datadog documentation for more information.'
            )
            self._connection_errors += 1
            raise TERADATASQL_IMPORT_ERROR
        else:
            self.log.debug('Connecting to Teradata...')
            validated_conn_params = self._validate_conn_params()

            if validated_conn_params:
                conn_params = self._build_connect_params()
                try:
                    conn = teradatasql.connect(json.dumps(conn_params))
                    self.log.debug('Connected to Teradata.')
                    yield conn
                except Exception as e:
                    self.log.exception('Unable to connect to Teradata. %s.', e)
                    self._connection_errors += 1
                    raise
                finally:
                    if conn:
                        conn.close()
            else:
                self.log.exception('Unable to connect to Teradata. Check the configuration.')
                self._connection_errors += 1

    def _validate_conn_params(self):
        credentials_optional = ['JWT', 'KRB5', 'LDAP', 'TDNEGO']
        valid_ssl_modes = ['ALLOW', 'DISABLE', 'PREFER', 'REQUIRE']
        valid_auth_mechs = ['TD2', 'TDNEGO', 'LDAP', 'KRB5', 'JWT']

        if self.config.auth_mechanism and self.config.auth_mechanism.upper() not in credentials_optional:
            if not self.config.username or not self.config.password:
                raise ConfigurationError('`username` and `password` are required.')
                return False

        if self.config.auth_mechanism is not None and self.config.auth_mechanism.upper() not in valid_auth_mechs:
            raise ConfigurationError(
                'Specified `auth_mechanism`: %s is not a valid option. Specify one of "TD2",'
                '"TDNEGO", "LDAP", "KRB5" or "JWT". '
                'Refer to the Datadog documentation for more information.'
            )
            return False

        if self.config.ssl_mode is not None and self.config.ssl_mode.upper() not in valid_ssl_modes:
            raise ConfigurationError(
                'Specified `ssl_mode`: %s is not a valid option. Specify one of "ALLOW", "DISABLE",'
                '"PREFER", or "REQUIRE". Refer to the Datadog documentation for more information.'
            )
            return False

        return True

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
                        'Row timestamp is more than 1h in the past. Is `SPMA` Resource Usage Logging enabled?'
                    )
                elif diff < -600:
                    msg = msg.format(
                        'Row timestamp is more than 10 min in the future. Try checking system time settings.'
                    )
                self.log.warning(msg)
                self._query_errors += 1
                raise Exception(msg)
        return row

    def _build_connect_params(self):
        return {
            'host': self.config.server,
            'account': self.config.account,
            'database': self.config.db,
            'dbs_port': str(self.config.port),
            'logmech': self.config.auth_mechanism,
            'logdata': self.config.auth_data,
            'user': self.config.username,
            'password': self.config.password,
            'https_port': str(self.config.https_port),
            'sslmode': self.config.ssl_mode,
            'sslprotocol': self.config.ssl_protocol,
        }
