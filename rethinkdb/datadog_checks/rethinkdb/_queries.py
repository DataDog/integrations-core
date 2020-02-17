# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

from typing import Iterator, Tuple

import rethinkdb

from ._types import (
    ClusterStats,
    JoinRow,
    ReplicaStats,
    Server,
    ServerStats,
    ServerStatus,
    Table,
    TableStats,
    TableStatus,
)


def query_cluster_stats(conn):
    # type: (rethinkdb.net.Connection) -> ClusterStats
    """
    Retrieve statistics about the cluster.
    """
    return rethinkdb.r.table('stats').get(['cluster']).run(conn)


def query_servers_with_stats(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Tuple[Server, ServerStats]]
    """
    Retrieve each server in the cluster along with its statistics.
    """

    # See: https://rethinkdb.com/api/python/eq_join/

    # For servers: stats['id'] = ['server', '<SERVER_ID>']
    is_server_stats_row = rethinkdb.r.row['id'].nth(0) == 'server'
    server_id = rethinkdb.r.row['id'].nth(1)

    rows = (
        rethinkdb.r.table('stats')
        .filter(is_server_stats_row)
        .eq_join(server_id, rethinkdb.r.table('server_config'))
        .run(conn)
    )  # type: Iterator[JoinRow]

    for row in rows:
        stats = row['left']  # type: ServerStats
        server = row['right']  # type: Server
        yield server, stats


def query_tables_with_stats(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Tuple[Table, TableStats]]
    """
    Retrieve each table in the cluster along with its statistics.
    """

    # See: https://rethinkdb.com/api/python/eq_join/

    # For tables: stats['id'] = ['table', '<TABLE_ID>']

    is_table_stats_row = rethinkdb.r.row['id'].nth(0) == 'table'
    table_id = rethinkdb.r.row['id'].nth(1)

    rows = (
        rethinkdb.r.table('stats')
        .filter(is_table_stats_row)
        .eq_join(table_id, rethinkdb.r.table('table_config'))
        .run(conn)
    )  # type: Iterator[JoinRow]

    for row in rows:
        stats = row['left']  # type: TableStats
        table = row['right']  # type: Table
        yield table, stats


def query_replica_stats(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Tuple[Table, Server, ReplicaStats]]
    """
    Retrieve each replica (table/server pair) in the cluster along with its statistics.
    """

    # For replicas: stats['id'] = ['table_server', '<TABLE_ID>', 'SERVER_ID']

    is_table_server_stats_row = rethinkdb.r.row['id'].nth(0) == 'table_server'
    table_id = rethinkdb.r.row['id'].nth(1)
    server_id = rethinkdb.r.row['left']['id'].nth(2)

    rows = (
        rethinkdb.r.table('stats')
        .filter(is_table_server_stats_row)
        .eq_join(table_id, rethinkdb.r.table('table_config'))
        .eq_join(server_id, rethinkdb.r.table('server_config'))
        # TODO: filter entries where
        .run(conn)
    )  # type: Iterator[JoinRow]

    for row in rows:
        join_row = row['left']  # type: JoinRow
        stats = join_row['left']  # type: ReplicaStats
        table = join_row['right']  # type: Table
        server = row['right']  # type: Server
        yield table, server, stats


def query_table_status(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[TableStatus]
    """
    Retrieve the status of each table in the cluster.
    """
    return rethinkdb.r.table('table_status').run(conn)


def query_server_status(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[ServerStatus]
    """
    Retrieve the status of each server in the cluster.
    """
    return rethinkdb.r.table('server_status').run(conn)
