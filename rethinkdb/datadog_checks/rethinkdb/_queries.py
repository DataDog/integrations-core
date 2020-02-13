# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

from typing import Iterator, Tuple

import rethinkdb

from ._types import ClusterStats, EqJoinRow, Server, ServerStats


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

    # A naive approach would be to query 'server_config', then for each server find the row in 'stats' that
    # corresponds to each server's ID. This would lead to the N+1 query problem.
    # Instead, we make a single (but more complex) query by joining 'stats' with 'server_config' on the server ID.
    # See: https://rethinkdb.com/api/python/eq_join/

    def _join_on_server_id(server_stats):
        # type: (rethinkdb.ast.RqlQuery) -> str
        server_stats_id = server_stats['id']  # ['server', '<ID>']
        return server_stats_id.nth(1)

    rows = (
        rethinkdb.r.table('stats').eq_join(_join_on_server_id, rethinkdb.r.table('server_config')).run(conn)
    )  # type: Iterator[EqJoinRow]

    for row in rows:
        stats = row['left']  # type: ServerStats
        server = row['right']  # type: Server
        yield server, stats
