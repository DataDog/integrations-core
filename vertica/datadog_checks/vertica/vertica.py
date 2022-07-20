# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import logging
import ssl
from collections import OrderedDict, defaultdict
from datetime import datetime
from itertools import chain

import vertica_python as vertica
from vertica_python.vertica.column import timestamp_tz_parse

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.common import exclude_undefined_keys
from datadog_checks.base.utils.containers import iter_unique

from . import views
from .utils import kilobytes_to_bytes, node_state_to_service_check, parse_major_version

# Python 3 only
PROTOCOL_TLS_CLIENT = getattr(ssl, 'PROTOCOL_TLS_CLIENT', ssl.PROTOCOL_TLS)


class VerticaCheck(AgentCheck):
    __NAMESPACE__ = 'vertica'
    SERVICE_CHECK_CONNECT = 'can_connect'
    SERVICE_CHECK_NODE_STATE = 'node_state'

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

        # Cache database results for re-use among disparate functions
        self._view = defaultdict(list)

        self._metric_groups = []

        self.check_initializations.append(self.parse_metric_groups)

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
        elif self._connection_load_balance or self._connection.closed():
            self._connection.reset_connection()

    def _major_version(self):
        return parse_major_version(self._connection.parameters['server_version'])

    def check(self, _):
        self._connect()
        # The order of queries is important as some results are cached for later re-use
        try:
            for method in self._metric_groups:
                method()

            self.query_version()
            self.query_custom()

        finally:
            self._view.clear()

    def query_licenses(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/LICENSES.htm
        for db_license in self.iter_rows(views.Licenses):
            self._view[views.Licenses].append(db_license)

            tags = ['license_type:{}'.format(db_license['licensetype'])]
            tags.extend(self._tags)

            expiration = db_license['end_date']
            if expiration and expiration != 'Perpetual':
                expiration = timestamp_tz_parse(expiration)
                seconds_until_expiration = (expiration - datetime.now(tz=expiration.tzinfo)).total_seconds()
            else:
                seconds_until_expiration = -1

            self.gauge('license.expiration', seconds_until_expiration, tags=tags)

    def query_license_audits(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/LICENSE_AUDITS.htm
        for license_audit in self.iter_rows(views.LicenseAudits):
            last_audit = license_audit['audit_start_timestamp']
            if last_audit:
                seconds_since_last_audit = (datetime.now(tz=last_audit.tzinfo) - last_audit).total_seconds()
            else:
                seconds_since_last_audit = -1
            self.gauge('license.latest_audit', seconds_since_last_audit, tags=self._tags)

            size = int(license_audit['license_size_bytes'])
            used = int(license_audit['database_size_bytes'])
            self.gauge('license.size', size, tags=self._tags)
            self.gauge('license.used', used, tags=self._tags)
            self.gauge('license.usable', size - used, tags=self._tags)
            self.gauge('license.utilized', used / size * 100, tags=self._tags)

    def query_system(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/SYSTEM.htm

        # Will only be 1 system
        for system in self.iter_rows(views.System):
            total_nodes = system['node_count']
            self.gauge('node.total', total_nodes, tags=self._tags)
            self.gauge('node.down', system['node_down_count'], tags=self._tags)

            # Is is possible for there to be no restriction
            allowed_nodes = self._view[views.Licenses][0]['node_restriction']
            if allowed_nodes is not None:
                self.gauge('node.allowed', allowed_nodes, tags=self._tags)
                self.gauge('node.available', allowed_nodes - total_nodes, tags=self._tags)

            self.gauge('ksafety.current', system['current_fault_tolerance'], tags=self._tags)
            self.gauge('ksafety.intended', system['designed_fault_tolerance'], tags=self._tags)

            self.gauge('epoch.ahm', system['ahm_epoch'], tags=self._tags)
            self.gauge('epoch.current', system['current_epoch'], tags=self._tags)
            self.gauge('epoch.last_good', system['last_good_epoch'], tags=self._tags)

    def query_nodes(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/NODES.htm
        for node in self.iter_rows(views.Nodes):
            tags = ['node_name:{}'.format(node['node_name'])]
            tags.extend(self._tags)

            node_state = node['node_state']
            status = node_state_to_service_check(node_state)
            message = node_state if status is not AgentCheck.OK else None
            self.service_check(self.SERVICE_CHECK_NODE_STATE, status, message=message, tags=tags)

    def query_projections(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/CATALOG/PROJECTIONS.htm
        total_projections = 0
        unsegmented_projections = 0
        unsafe_projections = 0

        for projection in self.iter_rows(views.Projections):
            total_projections += 1

            if not projection['is_segmented']:
                unsegmented_projections += 1

            if not projection['is_up_to_date']:
                unsafe_projections += 1

        self.gauge('projection.total', total_projections, tags=self._tags)

        self.gauge('projection.unsegmented', unsegmented_projections, tags=self._tags)
        if total_projections:
            unsegmented_percent = unsegmented_projections / total_projections * 100
        else:
            unsegmented_percent = 0
        self.gauge('projection.unsegmented_percent', unsegmented_percent, tags=self._tags)

        self.gauge('projection.unsafe', unsafe_projections, tags=self._tags)
        if total_projections:
            unsafe_percent = unsafe_projections / total_projections * 100
        else:
            unsafe_percent = 0
        self.gauge('projection.unsafe_percent', unsafe_percent, tags=self._tags)

    def query_projection_storage(self):
        queries = views.make_projection_storage_queries(self._major_version())

        for projection in self.iter_rows_query(queries['per_projection']):
            tags = self._tags + [
                'projection_name:{}'.format(projection['projection_name']),
                'table_name:{}'.format(projection['anchor_table_name']),
                'node_name:{}'.format(projection['node_name']),
            ]
            self.gauge('projection.ros.containers', projection['ros_count'], tags=tags)
            self.gauge('projection.row.ros', projection.get('ros_row_count'), tags=tags)
            self.gauge('projection.row.wos', projection.get('wos_row_count'), tags=tags)
            self.gauge('projection.row.total', projection['row_count'], tags=tags)
            self.gauge('projection.disk.used.ros', projection.get('ros_used_bytes'), tags=tags)
            self.gauge('projection.disk.used.wos', projection.get('wos_used_bytes'), tags=tags)
            self.gauge('projection.disk.used', projection['used_bytes'], tags=tags)

        for table in self.iter_rows_query(queries['per_table']):
            tags = self._tags + [
                'table_name:{}'.format(projection['anchor_table_name']),
                'node_name:{}'.format(projection['node_name']),
            ]
            self.gauge('table.row.ros', table.get('ros_row_count'), tags=tags)
            self.gauge('table.row.wos', table.get('wos_row_count'), tags=tags)
            self.gauge('table.row.total', table['row_count'], tags=tags)
            self.gauge('table.disk.used.ros', table.get('ros_used_bytes'), tags=tags)
            self.gauge('table.disk.used.wos', table.get('wos_used_bytes'), tags=tags)
            self.gauge('table.disk.used', table['used_bytes'], tags=tags)

        for node in self.iter_rows_query(queries['per_node']):
            tags = self._tags + ['node_name:{}'.format(projection['node_name'])]

            self.gauge('node.row.ros', node.get('ros_row_count'), tags=tags)
            self.gauge('node.row.wos', node.get('wos_row_count'), tags=tags)
            self.gauge('node.row.total', node['row_count'], tags=tags)
            self.gauge('node.disk.used.ros', node.get('ros_used_bytes'), tags=tags)
            self.gauge('node.disk.used.wos', node.get('wos_used_bytes'), tags=tags)
            self.gauge('node.disk.used', node['used_bytes'], tags=tags)

        # Total metrics
        total = self._connection.cursor('dict').execute(queries['total']).fetchone()
        self.gauge('row.ros', total.get('ros_row_count'), tags=self._tags)
        self.gauge('row.wos', total.get('wos_row_count'), tags=self._tags)
        self.gauge('row.total', total['row_count'], tags=self._tags)
        self.gauge('disk.used.ros', total.get('ros_used_bytes'), tags=self._tags)
        self.gauge('disk.used.wos', total.get('wos_used_bytes'), tags=self._tags)
        self.gauge('disk.used', total['used_bytes'], tags=self._tags)

    def query_storage_containers(self):
        queries = views.make_storage_containers_queries(self._major_version())

        for projection in self.iter_rows_query(queries['per_projection']):
            tags = self._tags + [
                'projection_name:{}'.format(projection['projection_name']),
                'node_name:{}'.format(projection['node_name']),
            ]
            if 'storage_type' in projection:
                tags.append('container_type:{}'.format(projection['storage_type']))

            self.gauge('projection.delete_vectors', projection['delete_vector_count'], tags=tags)

        for node in self.iter_rows_query(queries['per_node']):
            tags = self._tags + ['node_name:{}'.format(projection['node_name'])]
            self.gauge('node.delete_vectors', node['delete_vector_count'], tags=tags)

        total = self._connection.cursor('dict').execute(queries['total']).fetchone()
        self.gauge('delete_vectors', total['delete_vector_count'], tags=self._tags)

    def query_host_resources(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/HOST_RESOURCES.htm
        for host in self.iter_rows(views.HostResources):
            tags = ['host_name:{}'.format(host['host_name'])]
            tags.extend(self._tags)

            self.gauge('processor.cpu', host['processor_count'], tags=tags)
            self.gauge('processor.core', host['processor_core_count'], tags=tags)
            self.gauge('file.max', host['open_files_limit'], tags=tags)
            self.gauge('file.open', host['opened_file_count'], tags=tags)
            self.gauge('socket.open', host['opened_socket_count'], tags=tags)
            self.gauge('thread.max', host['threads_limit'], tags=tags)

            # Memory
            total = host['total_memory_bytes']
            usable = host['total_memory_free_bytes']
            used = total - usable

            self.gauge('memory.total', total, tags=tags)
            self.gauge('memory.usable', usable, tags=tags)
            self.gauge('memory.used', used, tags=tags)

            if total:
                utilized = used / total * 100
            else:
                utilized = 0
            self.gauge('memory.utilized', utilized, tags=tags)

            # Swap
            total = host['total_swap_memory_bytes']
            usable = host['total_swap_memory_free_bytes']
            used = total - usable

            self.gauge('memory.swap.total', total, tags=tags)
            self.gauge('memory.swap.usable', usable, tags=tags)
            self.gauge('memory.swap.used', used, tags=tags)

            if total:
                utilized = used / total * 100
            else:
                utilized = 0
            self.gauge('memory.swap.utilized', utilized, tags=tags)

    def query_query_metrics(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/QUERY_METRICS.htm
        for node in self.iter_rows(views.QueryMetrics):
            tags = ['node_name:{}'.format(node['node_name'])]
            tags.extend(self._tags)

            self.gauge('connection.active', node['active_user_session_count'], tags=tags)
            self.monotonic_count('connection.total', node['total_user_session_count'], tags=tags)
            self.gauge('query.active', node['running_query_count'], tags=tags)
            self.monotonic_count('query.total', node['executed_query_count'], tags=tags)

    def query_resource_pool_status(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/RESOURCE_POOL_STATUS.htm
        for pool in self.iter_rows(views.ResourcePoolStatus):
            tags = ['node_name:{}'.format(pool['node_name']), 'pool_name:{}'.format(pool['pool_name'])]
            tags.extend(self._tags)

            self.gauge(
                'resource_pool.memory.borrowed', kilobytes_to_bytes(pool['general_memory_borrowed_kb']), tags=tags
            )
            self.gauge('resource_pool.memory.max', kilobytes_to_bytes(pool['max_memory_size_kb']), tags=tags)
            self.gauge('resource_pool.memory.used', kilobytes_to_bytes(pool['memory_inuse_kb']), tags=tags)
            self.gauge('resource_pool.query.running', pool['running_query_count'], tags=tags)

    def query_disk_storage(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/DISK_STORAGE.htm
        for storage in self.iter_rows(views.DiskStorage):
            tags = [
                'node_name:{}'.format(storage['node_name']),
                'storage_status:{}'.format(storage['storage_status']),
                'storage_usage:{}'.format(storage['storage_usage']),
            ]
            tags.extend(self._tags)

            # Space
            block_size = storage['disk_block_size_bytes']
            usable = block_size * storage['disk_space_free_blocks']
            used = block_size * storage['disk_space_used_blocks']
            total = usable + used

            self.gauge('storage.size', total, tags=tags)
            self.gauge('storage.usable', usable, tags=tags)
            self.gauge('storage.used', used, tags=tags)

            if total:
                utilized = used / total * 100
            else:
                utilized = 0
            self.gauge('storage.utilized', utilized, tags=tags)

            # Latency
            latency = storage['latency']
            self.gauge('storage.latency', latency, tags=tags)

            if latency:
                latency_reciprocal = 1 / latency
            else:
                latency_reciprocal = 0

            # Throughput
            throughput = storage['throughput']
            self.gauge('storage.throughput', throughput, tags=tags)

            if throughput:
                throughput_reciprocal = 1 / throughput
            else:
                throughput_reciprocal = 0

            # Time to read 1 MiB
            self.gauge('storage.speed', latency_reciprocal + throughput_reciprocal, tags=tags)

    def query_resource_usage(self):
        # https://www.vertica.com/docs/9.2.x/HTML/Content/Authoring/SQLReferenceManual/SystemTables/MONITOR/RESOURCE_USAGE.htm
        for node in self.iter_rows(views.ResourceUsage):
            tags = ['node_name:{}'.format(node['node_name'])]
            tags.extend(self._tags)

            self.gauge('node.resource_requests', node['request_count'], tags=tags)
            self.gauge('thread.active', node['active_thread_count'], tags=tags)

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

    def parse_metric_groups(self):
        # If you create a new function, please add this to `default_metric_groups` below and
        # the config file (under `metric_groups`).
        default_metric_groups = OrderedDict(
            (
                ('licenses', self.query_licenses),
                ('license_audits', self.query_license_audits),
                ('system', self.query_system),
                ('nodes', self.query_nodes),
                ('projections', self.query_projections),
                ('projection_storage', self.query_projection_storage),
                ('storage_containers', self.query_storage_containers),
                ('host_resources', self.query_host_resources),
                ('query_metrics', self.query_query_metrics),
                ('resource_pool_status', self.query_resource_pool_status),
                ('disk_storage', self.query_disk_storage),
                ('resource_usage', self.query_resource_usage),
            )
        )

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

        self._metric_groups.extend(
            default_metric_groups[group] for group in default_metric_groups if group in metric_groups
        )
