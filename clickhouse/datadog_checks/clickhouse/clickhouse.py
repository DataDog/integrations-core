# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import clickhouse_connect

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.db import QueryManager

from . import advanced_queries, queries, utils


class ClickhouseCheck(AgentCheck):
    __NAMESPACE__ = 'clickhouse'
    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, name, init_config, instances):
        super(ClickhouseCheck, self).__init__(name, init_config, instances)

        self._server = self.instance.get('server', '')
        self._port = self.instance.get('port')
        self._db = self.instance.get('db', 'default')
        self._user = self.instance.get('username', self.instance.get('user', 'default'))
        self._password = self.instance.get('password', '')
        self._connect_timeout = float(self.instance.get('connect_timeout', 10))
        self._read_timeout = float(self.instance.get('read_timeout', 10))
        self._compression = self.instance.get('compression', False)
        self._tls_verify = is_affirmative(self.instance.get('tls_verify', False))
        self._tls_ca_cert = self.instance.get('tls_ca_cert', None)
        self._verify = self.instance.get('verify', True)
        self._tags = self.instance.get('tags', [])
        self._use_legacy_queries = self.instance.get('use_legacy_queries', True)
        self._use_advanced_queries = self.instance.get('use_advanced_queries', True)
        self._server_version = ''

        # Add global tags
        self._tags.append('server:{}'.format(self._server))
        self._tags.append('port:{}'.format(self._port))
        self._tags.append('db:{}'.format(self._db))

        self._error_sanitizer = utils.ErrorSanitizer(self._password)
        self.check_initializations.append(self.validate_config)

        # We'll connect on the first check run
        self._client = None

        self._query_manager = None

    def check(self, _):
        self.connect()
        self._server_version = self.select_version()
        self._build_query_manager().execute()
        self.set_version_metadata(self._server_version)

    def get_queries(self) -> list[dict]:
        query_list = []

        if self._use_legacy_queries:
            query_list.extend(
                [
                    queries.SystemMetrics,
                    queries.SystemEventsToDeprecate,
                    queries.SystemEvents,
                    queries.SystemAsynchronousMetrics,
                    queries.SystemParts,
                    queries.SystemReplicas,
                    queries.SystemDictionaries,
                ]
            )

        if self._use_advanced_queries:
            query_list.extend(
                [
                    advanced_queries.SystemMetrics,
                    advanced_queries.SystemEvents,
                    advanced_queries.SystemAsynchronousMetrics,
                ]
            )
            if self.version_ge('20.11'):
                query_list.append(advanced_queries.SystemErrors)

        return query_list

    def _build_query_manager(self) -> QueryManager:
        query_manager = QueryManager(
            self,
            self.execute_query_raw,
            queries=self.get_queries(),
            tags=self._tags,
            error_handler=self._error_sanitizer.clean,
        )
        query_manager.compile_queries()

        return query_manager

    def select_version(self) -> str:
        return self._client.command('SELECT version()', use_database=False)

    @AgentCheck.metadata_entrypoint
    def set_version_metadata(self, version: str):
        # The version comes in like `19.15.2.2` though sometimes there is no patch part
        version_parts = dict(zip(('year', 'major', 'minor', 'patch'), version.split('.')))

        self.set_metadata('version', version, scheme='parts', final_scheme='calver', part_map=version_parts)

    def execute_query_raw(self, query):
        return self._client.query(query).result_rows

    def validate_config(self):
        if not self._server:
            raise ConfigurationError('the `server` setting is required')

        # Validate compression type
        if self._compression and self._compression not in ['lz4', 'zstd', 'br', 'gzip']:
            raise ConfigurationError(
                f'Invalid compression type "{self._compression}". Valid values are: lz4, zstd, br, gzip'
            )

    def ping_clickhouse(self):
        return self._client.ping()

    def connect(self):
        if self.instance.get('user'):
            self._log_deprecation('_config_renamed', 'user', 'username')
        if self._client is not None:
            self.log.debug('Clickhouse client already exists. Pinging Clickhouse Server.')
            try:
                if self.ping_clickhouse():
                    self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
                    return
                else:
                    self.log.debug('Clickhouse connection ping failed. Attempting to reconnect')
                    self._client = None
            except Exception as e:
                self.log.debug('Unexpected ping response from Clickhouse', exc_info=e)
                self.log.debug('Attempting to reconnect')
                self._client = None

        try:
            client = clickhouse_connect.get_client(
                # https://clickhouse.com/docs/integrations/python#connection-arguments
                host=self._server,
                port=self._port,
                username=self._user,
                password=self._password,
                database=self._db,
                secure=self._tls_verify,
                connect_timeout=self._connect_timeout,
                send_receive_timeout=self._read_timeout,
                client_name=f'datadog-{self.check_id}',
                compress=self._compression,
                ca_cert=self._tls_ca_cert,
                verify=self._verify,
                # https://clickhouse.com/docs/integrations/python#settings-argument
                settings={},
            )
        except Exception as e:
            error = 'Unable to connect to ClickHouse: {}'.format(
                self._error_sanitizer.clean(self._error_sanitizer.scrub(str(e)))
            )
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=error, tags=self._tags)
            raise type(e)(error) from None
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            self._client = client

    def version_lt(self, version: str) -> bool:
        """
        Returns True if the current ClickHouse server version is less than the compared version, otherwise False.
        """
        # The `latest` version should always be greater than any other
        if version == 'latest':
            return True

        return utils.parse_version(self._server_version) < utils.parse_version(version)

    def version_ge(self, version: str) -> bool:
        """
        Returns True if the current ClickHouse server version is greater than the compared version, otherwise False.
        """
        # The `latest` version should always be less than any other
        if version == 'latest':
            return False

        return utils.parse_version(self._server_version) >= utils.parse_version(version)
