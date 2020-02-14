# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

from typing import Iterator, Tuple

import rethinkdb

from ._types import ClusterStats, EqJoinRow, Server, ServerStats, Table, TableStats


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

    # stats['id'] = ['server', '<SERVER_ID>'] -> '<SERVER_ID>' (= server_config['id'])
    server_id = rethinkdb.r.row['id'].nth(1)

    rows = (
        rethinkdb.r.table('stats').eq_join(server_id, rethinkdb.r.table('server_config')).run(conn)
    )  # type: Iterator[EqJoinRow]

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

    # stats['id'] = ['table', '<TABLE_ID>'] -> '<TABLE_ID>' (= table_config['id'])
    table_id = rethinkdb.r.row['id'].nth(1)

    rows = (
        rethinkdb.r.table('stats').eq_join(table_id, rethinkdb.r.table('table_config')).run(conn)
    )  # type: Iterator[EqJoinRow]

    for row in rows:
        stats = row['left']  # type: TableStats
        table = row['right']  # type: Table
        yield table, stats
