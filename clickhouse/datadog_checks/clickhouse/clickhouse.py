# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import clickhouse_driver
from six import raise_from

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.db import QueryManager

from . import queries
from .utils import ErrorSanitizer


class ClickhouseCheck(AgentCheck):
    __NAMESPACE__ = 'clickhouse'
    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, name, init_config, instances):
        super(ClickhouseCheck, self).__init__(name, init_config, instances)

        self._server = self.instance.get('server', '')
        self._port = self.instance.get('port')
        self._db = self.instance.get('db', 'default')
        self._user = self.instance.get('user', 'default')
        self._password = self.instance.get('password', '')
        self._connect_timeout = float(self.instance.get('connect_timeout', 10))
        self._read_timeout = float(self.instance.get('read_timeout', 10))
        self._compression = self.instance.get('compression', False)
        self._tls_verify = is_affirmative(self.instance.get('tls_verify', False))
        self._tags = self.instance.get('tags', [])

        # Add global tags
        self._tags.append('server:{}'.format(self._server))
        self._tags.append('port:{}'.format(self._port))
        self._tags.append('db:{}'.format(self._db))

        self._error_sanitizer = ErrorSanitizer(self._password)
        self.check_initializations.append(self.validate_config)

        # We'll connect on the first check run
        self._client = None
        self.check_initializations.append(self.create_connection)

        self._query_manager = QueryManager(
            self,
            self.execute_query_raw,
            queries=[
                queries.SystemMetrics,
                queries.SystemEvents,
                queries.SystemAsynchronousMetrics,
                queries.SystemParts,
                queries.SystemReplicas,
                queries.SystemDictionaries,
            ],
            tags=self._tags,
            error_handler=self._error_sanitizer.clean,
        )
        self.check_initializations.append(self._query_manager.compile_queries)

    def check(self, _):
        self._query_manager.execute()
        self.collect_version()

    def collect_version(self):
        version = list(self.execute_query_raw('SELECT version()'))[0][0]

        # The version comes in like `19.15.2.2` though sometimes there is no patch part
        version_parts = {name: part for name, part in zip(('year', 'major', 'minor', 'patch'), version.split('.'))}

        self.set_metadata('version', version, scheme='parts', final_scheme='calver', part_map=version_parts)

    def execute_query_raw(self, query):
        return self._client.execute_iter(query)

    def validate_config(self):
        if not self._server:
            raise ConfigurationError('the `server` setting is required')

    def create_connection(self):
        try:
            client = clickhouse_driver.Client(
                host=self._server,
                port=self._port,
                user=self._user,
                password=self._password,
                database=self._db,
                connect_timeout=self._connect_timeout,
                send_receive_timeout=self._read_timeout,
                sync_request_timeout=self._connect_timeout,
                compression=self._compression,
                secure=self._tls_verify,
                settings={},
                # Make every client unique for server logs
                client_name='datadog-{}'.format(self.check_id),
            )
            client.connection.connect()
        except Exception as e:
            error = 'Unable to connect to ClickHouse: {}'.format(
                self._error_sanitizer.clean(self._error_sanitizer.scrub(str(e)))
            )
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=error, tags=self._tags)

            # When an exception is raised in the context of another one, both will be printed. To avoid
            # this we set the context to None. https://www.python.org/dev/peps/pep-0409/
            raise_from(type(e)(error), None)
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            self._client = client
