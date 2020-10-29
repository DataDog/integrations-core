# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from collections import defaultdict
from contextlib import closing
from itertools import chain

import pyhdb
from six import iteritems
from six.moves import zip

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.common import total_time_to_temporal_percent
from datadog_checks.base.utils.constants import MICROSECOND
from datadog_checks.base.utils.containers import iter_unique

from . import queries
from .exceptions import QueryExecutionError
from .utils import compute_percent, positive


class SapHanaCheck(AgentCheck):
    __NAMESPACE__ = 'sap_hana'
    SERVICE_CHECK_CONNECT = 'can_connect'
    SERVICE_CHECK_STATUS = 'status'

    def __init__(self, name, init_config, instances):
        super(SapHanaCheck, self).__init__(name, init_config, instances)

        self._server = self.instance.get('server', '')
        self._port = self.instance.get('port', 30015)
        self._username = self.instance.get('username', '')
        self._password = self.instance.get('password', '')
        self._timeout = float(self.instance.get('timeout', 10))
        self._batch_size = int(self.instance.get('batch_size', 1000))
        self._tags = self.instance.get('tags', [])

        # Add server & port tags
        self._tags.append('server:{}'.format(self._server))
        self._tags.append('port:{}'.format(self._port))

        custom_queries = self.instance.get('custom_queries', [])
        use_global_custom_queries = self.instance.get('use_global_custom_queries', True)

        # Handle overrides
        if use_global_custom_queries == 'extend':
            custom_queries.extend(self.init_config.get('global_custom_queries', []))
        elif 'global_custom_queries' in self.init_config and is_affirmative(use_global_custom_queries):
            custom_queries = self.init_config.get('global_custom_queries', [])

        # Deduplicate
        self._custom_queries = list(iter_unique(custom_queries))

        # We'll connect on the first check run
        self._conn = None

        # Whether or not the connection was lost
        self._connection_lost = False

        # Whether or not to use the hostnames contained in the queried views
        self._use_hana_hostnames = is_affirmative(self.instance.get('use_hana_hostnames', False))

        # Save master database hostname to act as the default if `use_hana_hostnames` is true
        self._master_hostname = None

    def check(self, _):
        if self._conn is None:
            connection = self.get_connection()
            if connection is None:
                return

            self._conn = connection

        try:
            for query_method in (
                self.query_master_database,
                self.query_database_status,
                self.query_backup_status,
                self.query_licenses,
                self.query_connection_overview,
                self.query_disk_usage,
                self.query_service_memory,
                self.query_service_component_memory,
                self.query_row_store_memory,
                self.query_service_statistics,
                self.query_volume_io,
                self.query_custom,
            ):
                try:
                    query_method()
                except QueryExecutionError as e:
                    self.log.error('Error querying %s: %s', e.source(), str(e))
                    continue
                except Exception as e:
                    self.log.error('Unexpected error running `%s`: %s', query_method.__name__, str(e))
                    continue
        finally:
            if self._connection_lost:
                self._conn.close()
                self._conn = None
                self._connection_lost = False

    def query_master_database(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20ae63aa7519101496f6b832ec86afbd.html
        # Only 1 database
        for master in self.iter_rows(queries.MasterDatabase):
            tags = ['db:{}'.format(master['db_name']), 'usage:{}'.format(master['usage'])]
            tags.extend(self._tags)

            master_hostname = master['host']
            if self._use_hana_hostnames:
                self._master_hostname = master_hostname

            tags.append('hana_host:{}'.format(master_hostname))

            self.gauge(
                'uptime',
                (master['current_time'] - master['start_time']).total_seconds(),
                tags=tags,
                hostname=self.get_hana_hostname(master_hostname),
            )

    def query_database_status(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/dbbdc0d96675470e80801c5ddfb8d348.html
        for status in self.iter_rows(queries.SystemDatabases):
            tags = ['db:{}'.format(status['db_name'])]
            tags.extend(self._tags)

            db_status = self.OK if status['status'].lower() == 'yes' else self.CRITICAL
            message = status['details'] or None
            self.service_check(
                self.SERVICE_CHECK_STATUS, db_status, message=message, tags=tags, hostname=self.get_hana_hostname()
            )

    def query_backup_status(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/783108ba8b8b4c709959220b4535a010.html
        for backup in self.iter_rows(queries.GlobalSystemBackupProgress):
            tags = [
                'db:{}'.format(backup['db_name']),
                'service_name:{}'.format(backup['service']),
                'status:{}'.format(backup['status']),
            ]
            tags.extend(self._tags)

            hana_host = backup['host']
            tags.append('hana_host:{}'.format(hana_host))
            host = self.get_hana_hostname(hana_host)

            seconds_since_last_backup = (backup['current_time'] - backup['end_time']).total_seconds()
            self.gauge('backup.latest', seconds_since_last_backup, tags=tags, hostname=host)

    def query_licenses(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/1d7e7f52f6574a238c137e17b0840673.html
        for hana_license in self.iter_rows(queries.GlobalSystemLicenses):
            tags = ['sid:{}'.format(hana_license['sid']), 'product_name:{}'.format(hana_license['product_name'])]
            tags.extend(self._tags)

            host = self.get_hana_hostname()

            if hana_license['expiration_date']:
                expiration = (hana_license['expiration_date'] - hana_license['start_date']).total_seconds()
            else:
                expiration = -1
            self.gauge('license.expiration', expiration, tags=tags, hostname=host)

            total = hana_license['limit']
            self.gauge('license.size', total, tags=tags, hostname=host)

            used = hana_license['usage']
            self.gauge('license.usage', used, tags=tags, hostname=host)

            usable = total - used
            self.gauge('license.usable', usable, tags=tags, hostname=host)

            utilized = compute_percent(used, total)
            self.gauge('license.utilized', utilized, tags=tags, hostname=host)

    def query_connection_overview(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20abcf1f75191014a254a82b3d0f66bf.html
        db_counts = defaultdict(lambda: {'running': 0, 'idle': 0})
        for conn in self.iter_rows(queries.GlobalSystemConnectionsStatus):
            db_counts[(conn['db_name'], conn['host'], conn['port'])][conn['status'].lower()] += conn['total']

        for (db, host, port), counts in iteritems(db_counts):
            tags = ['db:{}'.format(db), 'hana_port:{}'.format(port)]
            tags.extend(self._tags)
            tags.append('hana_host:{}'.format(host))

            host = self.get_hana_hostname(host)
            running = counts['running']
            idle = counts['idle']

            self.gauge('connection.running', running, tags=tags, hostname=host)
            self.gauge('connection.idle', idle, tags=tags, hostname=host)
            self.gauge('connection.open', running + idle, tags=tags, hostname=host)

    def query_disk_usage(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/a2aac2ee72b341699fa8eb3988d8cecb.html
        for disk in self.iter_rows(queries.GlobalSystemDiskUsage):
            tags = ['db:{}'.format(disk['db_name']), 'resource_type:{}'.format(disk['resource'])]
            tags.extend(self._tags)

            hana_host = disk['host']
            tags.append('hana_host:{}'.format(hana_host))
            host = self.get_hana_hostname(hana_host)

            total = disk['total']
            self.gauge('disk.size', total, tags=tags, hostname=host)

            used = disk['used']
            self.gauge('disk.used', used, tags=tags, hostname=host)

            free = total - used
            self.gauge('disk.free', free, tags=tags, hostname=host)

            utilized = compute_percent(used, total)
            self.gauge('disk.utilized', utilized, tags=tags, hostname=host)

    def query_service_memory(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20bf33c975191014bc16d7ffb7717db2.html
        for memory in self.iter_rows(queries.GlobalSystemServiceMemory):
            tags = [
                'db:{}'.format(memory['db_name'] or 'none'),
                'hana_port:{}'.format(memory['port']),
                'service_name:{}'.format(memory['service']),
            ]
            tags.extend(self._tags)

            hana_host = memory['host']
            tags.append('hana_host:{}'.format(hana_host))
            host = self.get_hana_hostname(hana_host)

            # Overall
            self.gauge('memory.service.overall.physical.total', memory['physical'], tags=tags, hostname=host)
            self.gauge('memory.service.overall.virtual.total', memory['virtual'], tags=tags, hostname=host)

            total = memory['total']
            self.gauge('memory.service.overall.total', total, tags=tags, hostname=host)

            used = memory['used']
            self.gauge('memory.service.overall.used', used, tags=tags, hostname=host)

            free = total - used
            self.gauge('memory.service.overall.free', free, tags=tags, hostname=host)

            utilized = compute_percent(used, total)
            self.gauge('memory.service.overall.utilized', utilized, tags=tags, hostname=host)

            # Heap
            heap_total = memory['heap_total']
            self.gauge('memory.service.heap.total', heap_total, tags=tags, hostname=host)

            heap_used = memory['heap_used']
            self.gauge('memory.service.heap.used', heap_used, tags=tags, hostname=host)

            heap_free = heap_total - heap_used
            self.gauge('memory.service.heap.free', heap_free, tags=tags, hostname=host)

            heap_utilized = compute_percent(heap_used, heap_total)
            self.gauge('memory.service.heap.utilized', heap_utilized, tags=tags, hostname=host)

            # Shared
            shared_total = memory['shared_total']
            self.gauge('memory.service.shared.total', shared_total, tags=tags, hostname=host)

            shared_used = memory['shared_used']
            self.gauge('memory.service.shared.used', shared_used, tags=tags, hostname=host)

            shared_free = shared_total - shared_used
            self.gauge('memory.service.shared.free', shared_free, tags=tags, hostname=host)

            shared_utilized = compute_percent(shared_used, shared_total)
            self.gauge('memory.service.shared.utilized', shared_utilized, tags=tags, hostname=host)

            # Compactors
            compactors_total = memory['compactors_total']
            self.gauge('memory.service.compactor.total', compactors_total, tags=tags, hostname=host)

            compactors_free = memory['compactors_free']
            self.gauge('memory.service.compactor.free', compactors_free, tags=tags, hostname=host)

            compactors_used = compactors_total - compactors_free
            self.gauge('memory.service.compactor.used', compactors_used, tags=tags, hostname=host)

            compactors_utilized = compute_percent(compactors_used, compactors_total)
            self.gauge('memory.service.compactor.utilized', compactors_utilized, tags=tags, hostname=host)

    def query_service_component_memory(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20bed4f675191014a4cf8e62c28d16ae.html
        for memory in self.iter_rows(queries.GlobalSystemServiceComponentMemory):
            tags = [
                'db:{}'.format(memory['db_name'] or 'none'),
                'hana_port:{}'.format(memory['port']),
                'component_name:{}'.format(memory['component']),
            ]
            tags.extend(self._tags)

            hana_host = memory['host']
            tags.append('hana_host:{}'.format(hana_host))
            host = self.get_hana_hostname(hana_host)

            self.gauge('memory.service.component.used', memory['used'], tags=tags, hostname=host)

    def query_row_store_memory(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20bb47a975191014b1e2f6bd0a685d7b.html
        for memory in self.iter_rows(queries.GlobalSystemRowStoreMemory):
            tags = [
                'db:{}'.format(memory['db_name']),
                'hana_port:{}'.format(memory['port']),
                'resource_type:{}'.format(memory['category']),
            ]
            tags.extend(self._tags)

            hana_host = memory['host']
            tags.append('hana_host:{}'.format(hana_host))
            host = self.get_hana_hostname(hana_host)

            total = memory['total']
            self.gauge('memory.row_store.total', total, tags=tags, hostname=host)

            used = memory['used']
            self.gauge('memory.row_store.used', used, tags=tags, hostname=host)

            free = memory['free']
            self.gauge('memory.row_store.free', free, tags=tags, hostname=host)

            utilized = compute_percent(used, total)
            self.gauge('memory.row_store.utilized', utilized, tags=tags, hostname=host)

    def query_service_statistics(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20c460be751910149173ac5c08d42be5.html
        for service in self.iter_rows(queries.GlobalSystemServiceStatistics):
            tags = [
                'db:{}'.format(service['db_name'] or 'none'),
                'hana_port:{}'.format(service['port']),
                'service_name:{}'.format(service['service']),
            ]
            tags.extend(self._tags)

            hana_host = service['host']
            tags.append('hana_host:{}'.format(hana_host))
            host = self.get_hana_hostname(hana_host)

            response_time = service['response_time']
            self.gauge('network.service.request.response_time', response_time, tags=tags, hostname=host)

            requests_per_second = service['requests_per_second']
            self.gauge('network.service.request.per_second', requests_per_second, tags=tags, hostname=host)

            requests_active = service['requests_active']
            self.gauge('network.service.request.active', requests_active, tags=tags, hostname=host)

            requests_pending = service['requests_pending']
            self.gauge('network.service.request.pending', requests_pending, tags=tags, hostname=host)

            requests_finished_total = service['requests_finished_total']
            self.monotonic_count(
                'network.service.request.total_finished', requests_finished_total, tags=tags, hostname=host
            )

            requests_finished_external = service['requests_finished_external']
            self.monotonic_count(
                'network.service.request.external.total_finished', requests_finished_external, tags=tags, hostname=host
            )

            requests_finished_internal = requests_finished_total - requests_finished_external
            self.monotonic_count(
                'network.service.request.internal.total_finished', requests_finished_internal, tags=tags, hostname=host
            )

            threads_total = service['threads_total']
            self.gauge('thread.service.total', threads_total, tags=tags, hostname=host)

            threads_active = service['threads_active']
            self.gauge('thread.service.active', threads_active, tags=tags, hostname=host)

            threads_inactive = threads_total - threads_active
            self.gauge('thread.service.inactive', threads_inactive, tags=tags, hostname=host)

            files_open = service['files_open']
            self.gauge('file.service.open', files_open, tags=tags, hostname=host)

            cpu_percent = total_time_to_temporal_percent(service['cpu_time'])
            self.rate('cpu.service.utilized', cpu_percent, tags=tags, hostname=host)

    def query_volume_io(self):
        # https://help.sap.com/viewer/4fe29514fd584807ac9f2a04f6754767/2.0.02/en-US/20cadec8751910148bab98528e3634a9.html
        for volume in self.iter_rows(queries.GlobalSystemVolumeIO):
            tags = [
                'db:{}'.format(volume['db_name']),
                'hana_port:{}'.format(volume['port']),
                'resource_type:{}'.format(volume['resource']),
                'fs_path:{}'.format(volume['path']),
            ]
            tags.extend(self._tags)

            hana_host = volume['host']
            tags.append('hana_host:{}'.format(hana_host))
            host = self.get_hana_hostname(hana_host)

            # Read
            reads = volume['reads']
            self.gauge('volume.io.read.total', reads, tags=tags, hostname=host)
            self.monotonic_count('volume.io.read.count', reads, tags=tags, hostname=host)

            read_size = volume['read_size']
            self.gauge('volume.io.read.size.total', read_size, tags=tags, hostname=host)
            self.monotonic_count('volume.io.read.size.count', read_size, tags=tags, hostname=host)

            read_percent = total_time_to_temporal_percent(volume['read_time'], scale=MICROSECOND)
            self.rate('volume.io.read.utilized', read_percent, tags=tags, hostname=host)

            # Write
            writes = volume['writes']
            self.gauge('volume.io.write.total', writes, tags=tags, hostname=host)
            self.monotonic_count('volume.io.write.count', writes, tags=tags, hostname=host)

            write_size = volume['write_size']
            self.gauge('volume.io.write.size.total', write_size, tags=tags, hostname=host)
            self.monotonic_count('volume.io.write.size.count', write_size, tags=tags, hostname=host)

            write_percent = total_time_to_temporal_percent(volume['write_time'], scale=MICROSECOND)
            self.rate('volume.io.write.utilized', write_percent, tags=tags, hostname=host)

            # Overall

            # Convert microseconds -> seconds
            io_time = volume['io_time'] / MICROSECOND
            io_percent = total_time_to_temporal_percent(io_time, scale=1)
            self.rate('volume.io.utilized', io_percent, tags=tags, hostname=host)

            if io_time:
                throughput = (read_size + write_size) / io_time
            else:
                throughput = 0
            self.gauge('volume.io.throughput', throughput, tags=tags, hostname=host)

    def query_custom(self):
        for custom_query in self._custom_queries:
            query = custom_query.get('query')
            if not query:
                self.log.error('Custom query field `query` is required')
                continue

            columns = custom_query.get('columns')
            if not columns:
                self.log.error('Custom query field `columns` is required')
                continue

            self.log.debug('Running custom query for SAP HANA')
            rows = self.iter_rows_raw(query)

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

                if len(columns) != len(row):
                    self.log.error('Custom query result expected %s column(s), got %s', len(columns), len(row))
                    continue

                metric_info = []
                query_tags = list(self._tags)
                query_tags.extend(custom_query.get('tags', []))

                for column, value in zip(columns, row):
                    # Columns can be ignored via configuration.
                    if not column:  # no cov
                        continue

                    name = column.get('name')
                    if not name:
                        self.log.error('Column field `name` is required')
                        break

                    column_type = column.get('type')
                    if not column_type:
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
                        except (ValueError, TypeError):
                            self.log.error('Non-numeric value `%s` for metric column `%s`', value, name)
                            break

                # Only submit metrics if there were absolutely no errors - all or nothing.
                else:
                    for info in metric_info:
                        metric, value, method = info
                        getattr(self, method)(metric, value, tags=query_tags)

    def iter_rows(self, query, implicit_values=True):
        # https://github.com/SAP/PyHDB
        with closing(self._conn.cursor()) as cursor:
            self.execute_query(cursor, query.query, lambda: ', '.join(sorted(query.views)))

            # Re-use column access map for efficiency
            result = {}

            rows = cursor.fetchmany(self._batch_size)
            while rows:
                for row in rows:
                    for column, value in zip(query.fields, row):
                        # Undefined database sources may yield negative values.
                        # This can also occur for metrics that have no value yet.
                        if implicit_values and isinstance(value, (float, int)):
                            value = positive(value)

                        result[column] = value

                    yield result

                # Get next result set, if any
                rows = cursor.fetchmany(self._batch_size)

    def iter_rows_raw(self, query):
        with closing(self._conn.cursor()) as cursor:
            self.execute_query(cursor, query, lambda: 'custom query')

            rows = cursor.fetchmany(self._batch_size)
            while rows:
                for row in rows:
                    yield row

                # Get next result set, if any
                rows = cursor.fetchmany(self._batch_size)

    def get_connection(self):
        try:
            connection = pyhdb.connection.Connection(
                host=self._server, port=self._port, user=self._username, password=self._password, timeout=self._timeout
            )
            connection.connect()
        except Exception as e:
            error = str(e).replace(self._password, '**********')
            self.log.error('Unable to connect to SAP HANA: %s', error)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=error, tags=self._tags)
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            return connection

    def execute_query(self, cursor, query, source):
        try:
            cursor.execute(query)
        except Exception as e:
            error = str(e)
            if 'Lost connection to HANA server' in error:
                self._connection_lost = True

            raise QueryExecutionError(error, source)

    def get_hana_hostname(self, hostname=None):
        if self._use_hana_hostnames:
            return hostname or self._master_hostname
