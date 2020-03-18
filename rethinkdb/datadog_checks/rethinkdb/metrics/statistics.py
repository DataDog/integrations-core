# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Iterator, List, Tuple

from ..connections import Connection
from ..queries import QueryEngine
from ..types import ClusterStats, ReplicaStats, ServerStats, TableStats
from ._base import DocumentMetricCollector


class ClusterStatisticsCollector(DocumentMetricCollector[ClusterStats]):
    """
    Collect metrics about cluster statistics.

    See: https://rethinkdb.com/docs/system-stats#cluster
    """

    name = 'cluster_statistics'
    group = 'stats.cluster'
    metrics = [
        {'type': 'gauge', 'path': 'query_engine.queries_per_sec'},
        {'type': 'gauge', 'path': 'query_engine.read_docs_per_sec'},
        {'type': 'gauge', 'path': 'query_engine.written_docs_per_sec'},
    ]

    def iter_documents(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Tuple[ClusterStats, List[str]]]
        yield engine.query_cluster_stats(conn), []


class ServerStatisticsCollector(DocumentMetricCollector[ServerStats]):
    """
    Collect metrics about server statistics.

    See: https://rethinkdb.com/docs/system-stats#server
    """

    name = 'server_statistics'
    group = 'stats.server'
    metrics = [
        {'type': 'gauge', 'path': 'query_engine.client_connections'},
        {'type': 'gauge', 'path': 'query_engine.clients_active'},
        {'type': 'gauge', 'path': 'query_engine.queries_per_sec'},
        {'type': 'monotonic_count', 'path': 'query_engine.queries_total'},
        {'type': 'gauge', 'path': 'query_engine.read_docs_per_sec'},
        {'type': 'monotonic_count', 'path': 'query_engine.read_docs_total'},
        {'type': 'gauge', 'path': 'query_engine.written_docs_per_sec'},
        {'type': 'monotonic_count', 'path': 'query_engine.written_docs_total'},
    ]

    def iter_documents(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Tuple[ServerStats, List[str]]]
        for server, stats in engine.query_servers_with_stats(conn):
            tags = ['server:{}'.format(server['name'])]
            tags.extend(server['tags'])
            yield stats, tags


class TableStatisticsCollector(DocumentMetricCollector[TableStats]):
    """
    Collect metrics about table statistics.

    See: https://rethinkdb.com/docs/system-stats#table
    """

    name = 'table_statistics'
    group = 'stats.table'
    metrics = [
        {'type': 'gauge', 'path': 'query_engine.read_docs_per_sec'},
        {'type': 'gauge', 'path': 'query_engine.written_docs_per_sec'},
    ]

    def iter_documents(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Tuple[TableStats, List[str]]]
        for table, stats in engine.query_tables_with_stats(conn):
            tags = ['table:{}'.format(table['name']), 'database:{}'.format(table['db'])]
            yield stats, tags


class ReplicaStatisticsCollector(DocumentMetricCollector[ReplicaStats]):
    """
    Collect metrics about replicas (table/server pairs) statistics.

    See: https://rethinkdb.com/docs/system-stats#replica
    """

    name = 'replica_statistics'
    group = 'stats.table_server'
    metrics = [
        {'type': 'gauge', 'path': 'query_engine.read_docs_per_sec'},
        {'type': 'monotonic_count', 'path': 'query_engine.read_docs_total'},
        {'type': 'gauge', 'path': 'query_engine.written_docs_per_sec'},
        {'type': 'monotonic_count', 'path': 'query_engine.written_docs_total'},
        {'type': 'gauge', 'path': 'storage_engine.cache.in_use_bytes'},
        {'type': 'gauge', 'path': 'storage_engine.disk.read_bytes_per_sec'},
        {'type': 'monotonic_count', 'path': 'storage_engine.disk.read_bytes_total'},
        {'type': 'gauge', 'path': 'storage_engine.disk.written_bytes_per_sec'},
        {'type': 'monotonic_count', 'path': 'storage_engine.disk.written_bytes_total'},
        {'type': 'gauge', 'path': 'storage_engine.disk.space_usage.metadata_bytes'},
        {'type': 'gauge', 'path': 'storage_engine.disk.space_usage.data_bytes'},
        {'type': 'gauge', 'path': 'storage_engine.disk.space_usage.garbage_bytes'},
        {'type': 'gauge', 'path': 'storage_engine.disk.space_usage.preallocated_bytes'},
    ]

    def iter_documents(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Tuple[ReplicaStats, List[str]]]
        for table, server, replica, stats in engine.query_replicas_with_stats(conn):
            tags = [
                'table:{}'.format(table['name']),
                'database:{}'.format(table['db']),
                'server:{}'.format(server['name']),
                'state:{}'.format(replica['state']),
            ]
            tags.extend(server['tags'])
            yield stats, tags


collect_cluster_statistics = ClusterStatisticsCollector()
collect_server_statistics = ServerStatisticsCollector()
collect_table_statistics = TableStatisticsCollector()
collect_replica_statistics = ReplicaStatisticsCollector()
