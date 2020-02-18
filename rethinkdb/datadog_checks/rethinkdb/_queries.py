# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Definition of RethinkDB queries used by the RethinkDB integration.

Useful reference documentation:
- Python ReQL command reference: https://rethinkdb.com/api/python/
- Usage of `eq_join`: https://rethinkdb.com/api/python/eq_join/
"""

from __future__ import absolute_import

from typing import Iterator, Tuple

import rethinkdb
from rethinkdb import r

from ._types import (
    ClusterStats,
    Job,
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
    return r.db('rethinkdb').table('stats').get(['cluster']).run(conn)


def query_servers_with_stats(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Tuple[Server, ServerStats]]
    """
    Retrieve each server in the cluster along with its statistics.
    """
    # For servers: stats['id'] = ['server', '<SERVER_ID>']
    is_server_stats_row = r.row['id'].nth(0) == 'server'
    server_id = r.row['id'].nth(1)

    stats = r.db('rethinkdb').table('stats')
    server_config = r.db('rethinkdb').table('server_config')

    rows = stats.filter(is_server_stats_row).eq_join(server_id, server_config).run(conn)  # type: Iterator[JoinRow]

    for row in rows:
        server_stats = row['left']  # type: ServerStats
        server = row['right']  # type: Server
        yield server, server_stats


def query_tables_with_stats(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Tuple[Table, TableStats]]
    """
    Retrieve each table in the cluster along with its statistics.
    """
    # For tables: stats['id'] = ['table', '<TABLE_ID>']
    is_table_stats_row = r.row['id'].nth(0) == 'table'
    table_id = r.row['id'].nth(1)

    stats = r.db('rethinkdb').table('stats')
    table_config = r.db('rethinkdb').table('table_config')

    rows = stats.filter(is_table_stats_row).eq_join(table_id, table_config).run(conn)  # type: Iterator[JoinRow]

    for row in rows:
        table_stats = row['left']  # type: TableStats
        table = row['right']  # type: Table
        yield table, table_stats


def query_replicas_with_stats(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Tuple[Table, Server, ReplicaStats]]
    """
    Retrieve each replica (table/server pair) in the cluster along with its statistics.
    """

    # For replicas: stats['id'] = ['table_server', '<TABLE_ID>', 'SERVER_ID']
    is_table_server_stats_row = r.row['id'].nth(0) == 'table_server'
    table_id = r.row['id'].nth(1)
    server_id = r.row['left']['id'].nth(2)

    stats = r.db('rethinkdb').table('stats')
    server_config = r.db('rethinkdb').table('server_config')
    table_config = r.db('rethinkdb').table('table_config')

    rows = (
        stats.filter(is_table_server_stats_row)
        .eq_join(table_id, table_config)
        .eq_join(server_id, server_config)
        .run(conn)
    )  # type: Iterator[JoinRow]

    for row in rows:
        join_row = row['left']  # type: JoinRow
        replica_stats = join_row['left']  # type: ReplicaStats
        table = join_row['right']  # type: Table
        server = row['right']  # type: Server
        yield table, server, replica_stats


def query_table_status(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[TableStatus]
    """
    Retrieve the status of each table in the cluster.
    """
    return r.db('rethinkdb').table('table_status').run(conn)


def query_server_status(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[ServerStatus]
    """
    Retrieve the status of each server in the cluster.
    """
    return r.db('rethinkdb').table('server_status').run(conn)


def query_system_jobs(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Job]
    """
    Retrieve all the currently running system jobs.
    """
    return r.db('rethinkdb').table('jobs').run(conn)
