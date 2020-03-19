# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator

import rethinkdb

from .. import operations
from ..types import Metric

logger = logging.getLogger(__name__)


def collect_cluster_statistics(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about cluster statistics.

    See: https://rethinkdb.com/docs/system-stats#cluster
    """
    logger.debug('collect_cluster_statistics')

    stats = operations.query_cluster_stats(conn)
    logger.debug('cluster_statistics stats=%r', stats)

    query_engine = stats['query_engine']

    yield {
        'type': 'gauge',
        'name': 'rethinkdb.stats.cluster.queries_per_sec',
        'value': query_engine['queries_per_sec'],
        'tags': [],
    }

    yield {
        'type': 'gauge',
        'name': 'rethinkdb.stats.cluster.read_docs_per_sec',
        'value': query_engine['read_docs_per_sec'],
        'tags': [],
    }

    yield {
        'type': 'gauge',
        'name': 'rethinkdb.stats.cluster.written_docs_per_sec',
        'value': query_engine['written_docs_per_sec'],
        'tags': [],
    }


def collect_server_statistics(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about server statistics.

    See: https://rethinkdb.com/docs/system-stats#server
    """
    logger.debug('collect_server_statistics')

    for server, stats in operations.query_servers_with_stats(conn):
        logger.debug('server_statistics server=%r stats=%r', server, stats)

        name = server['name']
        server_tags = server['tags']
        query_engine = stats['query_engine']

        tags = ['server:{}'.format(name)]
        tags.extend(server_tags)

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.server.client_connections',
            'value': query_engine['client_connections'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.server.clients_active',
            'value': query_engine['clients_active'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.server.queries_per_sec',
            'value': query_engine['queries_per_sec'],
            'tags': tags,
        }

        yield {
            'type': 'monotonic_count',
            'name': 'rethinkdb.stats.server.queries_total',
            'value': query_engine['queries_total'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.server.read_docs_per_sec',
            'value': query_engine['read_docs_per_sec'],
            'tags': tags,
        }

        yield {
            'type': 'monotonic_count',
            'name': 'rethinkdb.stats.server.read_docs_total',
            'value': query_engine['read_docs_total'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.server.written_docs_per_sec',
            'value': query_engine['written_docs_per_sec'],
            'tags': tags,
        }

        yield {
            'type': 'monotonic_count',
            'name': 'rethinkdb.stats.server.written_docs_total',
            'value': query_engine['written_docs_total'],
            'tags': tags,
        }


def collect_table_statistics(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about table statistics.

    See: https://rethinkdb.com/docs/system-stats#table
    """
    logger.debug('collect_table_statistics')

    for table, stats in operations.query_tables_with_stats(conn):
        logger.debug('table_statistics table=%r stats=%r', table, stats)

        name = table['name']
        database = table['db']
        query_engine = stats['query_engine']

        tags = ['table:{}'.format(name), 'database:{}'.format(database)]

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table.read_docs_per_sec',
            'value': query_engine['read_docs_per_sec'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table.written_docs_per_sec',
            'value': query_engine['written_docs_per_sec'],
            'tags': tags,
        }


def collect_replica_statistics(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about replicas (table/server pairs) statistics.

    See: https://rethinkdb.com/docs/system-stats#replica
    """
    logger.debug('collect_replica_statistics')

    for table, server, replica, stats in operations.query_replicas_with_stats(conn):
        logger.debug('replica_statistics table=%r server=%r replica=%r stats=%r', table, server, replica, stats)

        database = table['db']
        server_name = server['name']
        table_name = table['name']
        server_tags = server['tags']
        query_engine = stats['query_engine']
        storage_engine = stats['storage_engine']
        state = replica['state']

        tags = [
            'table:{}'.format(table_name),
            'database:{}'.format(database),
            'server:{}'.format(server_name),
            'state:{}'.format(state),
        ]
        tags.extend(server_tags)

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table_server.read_docs_per_sec',
            'value': query_engine['read_docs_per_sec'],
            'tags': tags,
        }

        yield {
            'type': 'monotonic_count',
            'name': 'rethinkdb.stats.table_server.read_docs_total',
            'value': query_engine['read_docs_total'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table_server.written_docs_per_sec',
            'value': query_engine['written_docs_per_sec'],
            'tags': tags,
        }

        yield {
            'type': 'monotonic_count',
            'name': 'rethinkdb.stats.table_server.written_docs_total',
            'value': query_engine['written_docs_total'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table_server.cache.in_use_bytes',
            'value': storage_engine['cache']['in_use_bytes'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table_server.disk.read_bytes_per_sec',
            'value': storage_engine['disk']['read_bytes_per_sec'],
            'tags': tags,
        }

        yield {
            'type': 'monotonic_count',
            'name': 'rethinkdb.stats.table_server.disk.read_bytes_total',
            'value': storage_engine['disk']['read_bytes_total'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table_server.disk.written_bytes_per_sec',
            'value': storage_engine['disk']['written_bytes_per_sec'],
            'tags': tags,
        }

        yield {
            'type': 'monotonic_count',
            'name': 'rethinkdb.stats.table_server.disk.written_bytes_total',
            'value': storage_engine['disk']['written_bytes_total'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table_server.disk.metadata_bytes',
            'value': storage_engine['disk']['space_usage']['metadata_bytes'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table_server.disk.data_bytes',
            'value': storage_engine['disk']['space_usage']['data_bytes'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table_server.disk.garbage_bytes',
            'value': storage_engine['disk']['space_usage']['garbage_bytes'],
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.stats.table_server.disk.preallocated_bytes',
            'value': storage_engine['disk']['space_usage']['preallocated_bytes'],
            'tags': tags,
        }
