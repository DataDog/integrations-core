# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import logging
import ssl
from itertools import chain

import vertica_python as vertica

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.common import exclude_undefined_keys
from datadog_checks.base.utils.containers import iter_unique
from datadog_checks.base.utils.db import QueryManager

from . import views
from .queries import get_queries
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

        # If `tls_verify` is explicitly set to true, set `use_tls` to true (for legacy support)
        # `tls_verify` used to do what `use_tls` does now
        self._tls_verify = is_affirmative(self.instance.get('tls_verify'))
        self._use_tls = is_affirmative(self.instance.get('use_tls', False))

        if self._tls_verify and not self._use_tls:
            self._use_tls = True

        custom_queries = self.instance.get('custom_queries', [])
        use_global_custom_queries = self.instance.get('use_global_custom_queries', True)

        # Handle overrides
        if use_global_custom_queries == 'extend':
            custom_queries.extend(self.init_config.get('global_custom_queries', []))
        elif 'global_custom_queries' in self.init_config and is_affirmative(use_global_custom_queries):
            custom_queries = self.init_config.get('global_custom_queries', [])

        # Deduplicate
        self._custom_queries = list(iter_unique(custom_queries))

        # Add global database tag
        self._tags.append('db:{}'.format(self._db))

        # We'll connect on the first check run
        self._connection = None
        self._query_manager = None

        self._metric_groups = {}

        self.check_initializations.extend([self.parse_metric_groups])

    def _get_default_client_lib_log_level(self):
        if self.log.logger.getEffectiveLevel() <= logging.DEBUG:
            # Automatically collect library logs for debug flares.
            return logging.DEBUG
        # Default to no library logs, since they're too verbose even at the INFO level.
        return None

    def _connect(self):
        if self._connection is None:
            connection = self.get_connection()
            if connection is None:
                return

            self._connection = connection
            self._initialize_query_manager()

        elif self._connection_load_balance or self._connection.closed():
            self._connection.reset_connection()

    def _initialize_query_manager(self):
        self._query_manager = QueryManager(
            self,
            self.execute_query,
            queries=get_queries(self._major_version(), self._metric_groups),
            tags=self._tags,
        )

        self._query_manager.compile_queries()

    def _major_version(self):
        return parse_major_version(self._connection.parameters['server_version'])

    def check(self, _):
        self._connect()

        if not self._connection:
            self.log.debug('Skipping check due to connection issue.')
            return

        self._query_manager.execute()
        self.query_version()
        self.query_custom()

    @AgentCheck.metadata_entrypoint
    def query_version(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/AdministratorsGuide/Diagnostics/DeterminingYourVersionOfVertica.htm
        for v in self.iter_rows(views.Version):
            version = v['version'].replace('Vertica Analytic Database v', '')

            # Force the last part to represent the build part of semver
            version = version.replace('-', '+', 1)

            self.set_metadata('version', version)

    def query_custom(self):
        for custom_query in self._custom_queries:
            query = custom_query.get('query')
            if not query:  # no cov
                self.log.error('Custom query field `query` is required')
                continue

            columns = custom_query.get('columns')
            if not columns:  # no cov
                self.log.error('Custom query field `columns` is required')
                continue

            self.log.debug('Running custom query for Vertica')
            cursor = self._connection.cursor()
            cursor.execute(query)

            rows = cursor.iterate()

            # Trigger query execution
            try:
                first_row = next(rows)
            except Exception as e:  # no cov
                self.log.error('Error executing custom query: %s', e)
                continue

            for row in chain((first_row,), rows):
                if not row:  # no cov
                    self.log.debug('Custom query returned an empty result')
                    continue

                if len(columns) != len(row):  # no cov
                    self.log.error('Custom query result expected %s columns, got %s', len(columns), len(row))
                    continue

                metric_info = []
                query_tags = list(self._tags)
                query_tags.extend(custom_query.get('tags', []))

                for column, value in zip(columns, row):
                    # Columns can be ignored via configuration.
                    if not column:  # no cov
                        continue

                    name = column.get('name')
                    if not name:  # no cov
                        self.log.error('Column field `name` is required')
                        break

                    column_type = column.get('type')
                    if not column_type:  # no cov
                        self.log.error('Column field `type` is required for column `%s`', name)
                        break

                    if column_type == 'tag':
                        query_tags.append('{}:{}'.format(name, value))
                    else:
                        if not hasattr(self, column_type):
                            self.log.error('Invalid submission method `%s` for metric column `%s`', column_type, name)
                            break
                        try:
                            metric_info.append((name, float(value), column_type))
                        except (ValueError, TypeError):  # no cov
                            self.log.error('Non-numeric value `%s` for metric column `%s`', value, name)
                            break

                # Only submit metrics if there were absolutely no errors - all or nothing.
                else:
                    for info in metric_info:
                        metric, value, method = info
                        getattr(self, method)(metric, value, tags=query_tags)

    def get_connection(self):
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
        if self._client_lib_log_level:
            connection_options['log_level'] = self._client_lib_log_level
            # log_path is required by vertica client for using logging
            # when log_path is set to '', vertica won't log to a file
            # but we still get logs via parent root logger
            connection_options['log_path'] = ''

        if self._use_tls:
            tls_context = self.get_tls_context()
            connection_options['ssl'] = tls_context

        try:
            connection = vertica.connect(**exclude_undefined_keys(connection_options))
        except Exception as e:
            self.log.error('Unable to connect to database `%s` as user `%s`: %s', self._db, self._username, e)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, tags=self._tags)
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            return connection

    def iter_rows(self, view):
        for row in self.iter_rows_query(view.query):
            yield row

    def iter_rows_query(self, query):
        cursor = self._connection.cursor('dict')
        cursor.execute(query)

        for row in cursor.iterate():
            yield row

    def execute_query(self, query):
        return self._connection.cursor().execute(query).iterate()

    def parse_metric_groups(self):
        # If you create a new function, please add this to `default_metric_groups` below and
        # the config file (under `metric_groups`).
        default_metric_groups = [
            'licenses',
            'license_audits',
            'system',
            'nodes',
            'projections',
            'projection_storage',
            'storage_containers',
            'host_resources',
            'query_metrics',
            'resource_pool_status',
            'disk_storage',
            'resource_usage',
        ]

        metric_groups = self.instance.get('metric_groups') or list(default_metric_groups)

        # Ensure all metric groups are valid
        invalid_groups = []

        for group in metric_groups:
            if group not in default_metric_groups:
                invalid_groups.append(group)

        if invalid_groups:
            raise ConfigurationError(
                'Invalid metric_groups found in vertica conf.yaml: {}'.format(', '.join(invalid_groups))
            )

        # License query needs to be run before getting system
        if 'system' in metric_groups and 'licenses' not in metric_groups:
            self.log.debug('Detected `system` metric group, adding the `licenses` to metric_groups.')
            metric_groups.insert(0, 'licenses')

        self._metric_groups = [group for group in default_metric_groups if group in metric_groups]
