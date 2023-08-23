# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import logging
import ssl

import vertica_python as vertica

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.common import exclude_undefined_keys
from datadog_checks.base.utils.db import QueryManager

from .queries import METRIC_GROUPS, QueryBuilder
from .utils import parse_major_version

# Python 3 only
PROTOCOL_TLS_CLIENT = getattr(ssl, 'PROTOCOL_TLS_CLIENT', ssl.PROTOCOL_TLS)


class VerticaCheck(AgentCheck):
    __NAMESPACE__ = 'vertica'
    SERVICE_CHECK_CONNECT = 'can_connect'

    # This remapper is used to support legacy Vertica integration config values
    TLS_CONFIG_REMAPPER = {
        'cert': {'name': 'tls_cert'},
        'private_key': {'name': 'tls_private_key'},
        'ca_cert': {'name': 'tls_ca_cert'},
        'validate_hostname': {'name': 'tls_validate_hostname'},
    }

    def __init__(self, name, init_config, instances):
        super(VerticaCheck, self).__init__(name, init_config, instances)

        self._server = self.instance.get('server', 'localhost')
        self._port = int(self.instance.get('port', 5433))
        self._username = self.instance.get('username')
        self._db = self.instance.get('db', self._username)
        self._password = self.instance.get('password', '')
        self._backup_servers = [
            (bs.get('server', self._server), int(bs.get('port', self._port)))
            for bs in self.instance.get('backup_servers', [])
        ]
        self._connection_load_balance = is_affirmative(self.instance.get('connection_load_balance', False))
        self._timeout = float(self.instance.get('timeout', 10))
        self._tags = self.instance.get('tags', [])

        self._client_lib_log_level = self.instance.get('client_lib_log_level', self._get_default_client_lib_log_level())

        # `tls_verify` being explicitly set to true overrides the value `use_tls` for legacy reasons
        # `tls_verify` used to do what `use_tls` does now
        tls_verify = is_affirmative(self.instance.get('tls_verify'))
        use_tls = is_affirmative(self.instance.get('use_tls', False))
        self._tls_context = self.get_tls_context() if use_tls or tls_verify else None

        # Add global database tag
        self._tags.append('db:{}'.format(self._db))

        self.query_manager = None

        self._metric_groups = {}

        self._initialize_vertica_client()
        self.check_initializations.extend([self.parse_metric_groups])

    def _get_default_client_lib_log_level(self):
        if self.log.logger.getEffectiveLevel() <= logging.DEBUG:
            # Automatically collect library logs for debug flares.
            return logging.DEBUG
        # Default to no library logs, since they're too verbose even at the INFO level.
        return None

    def _initialize_vertica_client(self):
        connection_options = {
            'database': self._db,
            'host': self._server,
            'port': self._port,
            'user': self._username,
            'password': self._password,
            'backup_server_node': self._backup_servers,
            'connection_load_balance': self._connection_load_balance,
            'connection_timeout': self._timeout,
        }

        self._client = VerticaClient(connection_options, self._tls_context, self._client_lib_log_level, log=self.log)

    def _connect(self):
        try:
            self._client.connect()
        except Exception as e:
            self.log.error('Unable to connect to database `%s` as user `%s`: %s', self._db, self._username, e)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, tags=self._tags)
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            return self._client.connection

    def setup_query_manager(self, monitor_schema='v_monitor', catalog_schema='v_catalog'):
        query_builder = QueryBuilder(self._major_version())
        self._query_manager = QueryManager(
            self,
            self._client.query,
            queries=query_builder.get_queries(self._metric_groups),
            tags=self._tags,
        )
        self._query_manager.compile_queries()

    def check(self, _):
        connection = self._connect()

        if not connection:
            self.log.debug('Skipping check due to connection issue.')
            return

        self.setup_query_manager()
        self._query_manager.execute()
        self.set_version_metadata()

    @AgentCheck.metadata_entrypoint
    def set_version_metadata(self):
        self.set_metadata('version', self._version())

    @staticmethod
    def parse_db_version(vertica_version_string):
        return (
            vertica_version_string.replace('Vertica Analytic Database v', '')
            # Force the last part to represent the build part of semver
            .replace('-', '+', 1)
        )

    def _major_version(self):
        return parse_major_version(self._version())

    def _version(self):
        return self.parse_db_version(self._client.query_version())

    def parse_metric_groups(self):
        default_metric_groups = METRIC_GROUPS
        metric_groups = self.instance.get('metric_groups') or default_metric_groups

        # Ensure all metric groups are valid
        invalid_groups = []

        for group in metric_groups:
            if group not in default_metric_groups:
                invalid_groups.append(group)

        if invalid_groups:
            raise ConfigurationError(
                'Invalid metric_groups found in vertica conf.yaml: {}'.format(', '.join(invalid_groups))
            )

        self._metric_groups = [group for group in default_metric_groups if group in metric_groups]


class VerticaClient(object):
    """Wrapper around interactions with vertica."""

    def __init__(self, connection_options, tls_context=None, client_lib_log_level=None, log=None):
        self._client_lib_log_level = client_lib_log_level
        self._tls_context = tls_context

        self.connection = None
        self.log = log or logging.getLogger()
        self.options = connection_options

    def connect(self):
        """Establish connection to Vertica database.

        It does nothing if the connection is already open and load
        balancing is not active.
        """
        if self.connection:
            if self.connection_load_balance or self.connection.closed():
                self.log.debug("Recreate the connection")
                self.connection.close()
                self.connection = vertica.connect(**exclude_undefined_keys(self.options))
        else:
            self.connection = vertica.connect(**exclude_undefined_keys(self.options))

        return self.connection

    def query(self, query):
        return self.connection.cursor().execute(query).iterate()

    def query_version(self):
        """Get the Vertica version by queriying the DB.

        https://www.vertica.com/docs/11.1.x/HTML/Content/Authoring/AdministratorsGuide/Diagnostics/DeterminingYourVersionOfVertica.htm
        """
        return self.connection.cursor().execute('SELECT version()').fetchone()[0]

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        self._options = dict(options)
        if self._client_lib_log_level:
            self._options['log_level'] = self._client_lib_log_level
            # log_path is required by vertica client for using logging
            # when log_path is set to '', vertica won't log to a file
            # but we still get logs via parent root logger
            self._options['log_path'] = ''

        if self.use_tls:
            self._options['ssl'] = self._tls_context

    @property
    def use_tls(self):
        return self._tls_context is not None

    @property
    def connection_load_balance(self):
        return self.options.get('connection_load_balance', False)
