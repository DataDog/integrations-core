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
    JDBC_CONNECTION_STRING = "jdbc:teradata://{}"
    TERADATA_DRIVER_CLASS = "com.teradata.jdbc.TeraDriver"
    SERVICE_CHECK_NAME = "can_connect"

    def __init__(self, name, init_config, instances):
        super(TeradataCheck, self).__init__(name, init_config, instances)
        self.config = TeradataConfig(self.instance)
        self._connection = None
        self._server_tag = 'teradata_server:{}:{}'.format(self.config.server, self.config.port)
        self._tags = [self._server_tag] + self.config.tags

        manager_queries = []
        if self.config.collect_res_usage:
            manager_queries.extend(COLLECT_RES_USAGE)
        else:
            manager_queries.extend(DEFAULT_QUERIES)

        self._query_manager = QueryManager(self, self._execute_query_raw, queries=manager_queries, tags=self._tags)
        self.check_initializations.append(self._query_manager.compile_queries)
        self._credentials_required = True

    def check(self, _):
        with self.connect() as conn:
            self._connection = conn
            self._query_manager.execute()

    def _execute_query_raw(self, query):
        with closing(self._connection.cursor()) as cursor:
            query = query.format(self.config.db)
            cursor.execute(query)
            if cursor.rowcount < 1:
                self.log.warning("Failed to fetch records from query: `%s`.", query)
            else:
                for row in cursor.fetchall():
                    try:
                        yield self._validate_timestamp(row, query)
                    except Exception:
                        self.log.debug("Unable to validate Resource Usage View timestamps.")
                        yield row

    @contextmanager
    def connect(self):
        try:
            return self._connect()
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, msg=e, tags=self._tags)
            self.log.error('Failed to connect to Teradata database. %s', e)
            raise

    def _connect(self):
        conn = None
        self.log.debug('Connecting to Teradata...')
        conn_params = self._build_connect_params()
        self.log.debug('VALIDATE PARAMS %s', self._validate_conn_params())
        if self._validate_conn_params():
            try:
                conn = teradatasql.connect(json.dumps(conn_params))
                self.log.debug('CONNECTION DUMP %s', str(json.dumps(conn_params)))
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._tags)
                self.log.debug('Connected to Teradata.')
                yield conn
            except Exception as e:
                self.log.exception('Unable to connect to Teradata. %s.', e)
                raise
            finally:
                if conn:
                    conn.close()
        else:
            self.log.exception('Unable to connect to Teradata. Check the configuration.')

    def _validate_conn_params(self):
        optional = ['JWT', 'KRB5', 'LDAP', 'TDNEGO']

        if self.config.auth_mechanism and self.config.auth_mechanism.upper() in optional:
            self._credentials_required = False
            return True
        elif self._credentials_required and (not self.config.username or not self.config.password):
            raise ConfigurationError('`username` and `password` are required')
            return False
        else:
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
                        "Row timestamp is more than 1h in the past. Is `SPMA` Resource Usage Logging enabled?"
                    )
                elif diff < -600:
                    msg = msg.format(
                        "Row timestamp is more than 10 min in the future. Try checking system time settings."
                    )
                self.log.warning(msg)
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.WARNING, msg=msg, tags=self._tags)
            else:
                return row
        else:
            return row

    def _build_connect_params(self):
        connect_params = {
            'host': self.config.server,
            'account': self.config.account,
            'database': self.config.db,
            'dbs_port': str(self.config.port),
            'logmech': self.config.auth_mechanism,
            'logdata': self.config.auth_data,
        }

        credentials_params = {
            'user': self.config.username,
            'password': self.config.password,
        }

        ssl_params = {
            'https_port': str(self.config.https_port),
            'sslca': self.config.ssl_ca,
            'sslcapath': self.config.ssl_ca_path,
            'sslmode': self.config.ssl_mode,
            'sslprotocol': self.config.ssl_protocol,
        }

        if self._credentials_required:
            if self.config.use_tls:
                connect_params.update(credentials_params)
                connect_params.update(ssl_params)
            else:
                connect_params.update(credentials_params)

        return connect_params
