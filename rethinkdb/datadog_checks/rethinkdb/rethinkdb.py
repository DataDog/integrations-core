# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Required for `import rethinkdb` to import the Python client instead of this package on Python 2.
from __future__ import absolute_import

from contextlib import contextmanager
from typing import Any, Dict, Iterator, Tuple

import rethinkdb

from datadog_checks.base import AgentCheck

from .types import ClusterStats, EqJoinRow, Server, ServerStats, Table, TableStats


class RethinkDBCheck(AgentCheck):
    @contextmanager
    def _submit_service_check(self):
        # type: () -> Iterator[None]
        try:
            yield
        except rethinkdb.errors.ReqlDriverError:
            self.service_check('rethinkdb.can_connect', self.CRITICAL)
            raise
        else:
            self.service_check('rethinkdb.can_connect', self.OK)

    def check(self, instance):
        # type: (Dict[str, Any]) -> None
        with self._submit_service_check():
            with rethinkdb.r.connect(db='rethinkdb', host='localhost', port=28015) as conn:
                self._collect_statistics(conn)
                self._collect_statuses(conn)
                self._collect_jobs(conn)
                self._collect_current_issues(conn)

    def _collect_statistics(self, conn):
        # type: (rethinkdb.net.Connection) -> None
        self._collect_cluster_statistics(conn)
        self._collect_servers_statistics(conn)
        self._collect_table_statistics(conn)
        self._collect_replicas_statistics(conn)

    def _collect_cluster_statistics(self, conn):
        # type: (rethinkdb.net.Connection) -> None
        stats = rethinkdb.r.table('stats').get(['cluster']).run(conn)  # type: ClusterStats
        query_engine = stats['query_engine']

        self.rate('rethinkdb.stats.cluster.queries_per_sec', value=query_engine['queries_per_sec'])
        self.rate('rethinkdb.stats.cluster.read_docs_per_sec', value=query_engine['read_docs_per_sec'])
        self.rate('rethinkdb.stats.cluster.written_docs_per_sec', value=query_engine['written_docs_per_sec'])

    def _collect_servers_statistics(self, conn):
        # type: (rethinkdb.net.Connection) -> None
        for server, stats in _query_server_stats(conn):
            name = server['name']
            server_tags = server['tags']
            query_engine = stats['query_engine']

            tags = ['server:{}'.format(name)] + server_tags

            self.gauge('rethinkdb.stats.server.client_connections', value=query_engine['client_connections'], tags=tags)
            self.gauge('rethinkdb.stats.server.clients_active', value=query_engine['clients_active'], tags=tags)

            self.rate('rethinkdb.stats.server.queries_per_sec', value=query_engine['queries_per_sec'], tags=tags)
            self.monotonic_count('rethinkdb.stats.server.queries_total', query_engine['queries_total'], tags=tags)

            self.rate('rethinkdb.stats.server.read_docs_per_sec', value=query_engine['read_docs_per_sec'], tags=tags)
            self.monotonic_count(
                'rethinkdb.stats.server.read_docs_total', value=query_engine['read_docs_total'], tags=tags
            )

            self.rate(
                'rethinkdb.stats.server.written_docs_per_sec', value=query_engine['written_docs_per_sec'], tags=tags
            )
            self.monotonic_count(
                'rethinkdb.stats.server.written_docs_total', value=query_engine['written_docs_total'], tags=tags
            )

    def _collect_table_statistics(self, conn):
        # type: (rethinkdb.net.Connection) -> None
        tables = rethinkdb.r.table('table_config').run(conn)  # type: Iterator[Table]

        for table in tables:
            # TODO: get rid of N+1 query problem.
            stats = rethinkdb.r.table('stats').get(['table', table['id']]).run(conn)  # type: TableStats

            name = table['name']
            database = table['db']
            query_engine = stats['query_engine']

            tags = ['table:{}'.format(name), 'database:{}'.format(database)]

            self.rate('rethinkdb.stats.table.read_docs_per_sec', value=query_engine['read_docs_per_sec'], tags=tags)
            self.rate(
                'rethinkdb.stats.table.written_docs_per_sec', value=query_engine['written_docs_per_sec'], tags=tags
            )

    def _collect_replicas_statistics(self, conn):
        # type: (rethinkdb.net.Connection) -> None
        pass  # TODO

    def _collect_statuses(self, conn):
        # type: (rethinkdb.net.Connection) -> None
        pass  # TODO

    def _collect_jobs(self, conn):
        # type: (rethinkdb.net.Connection) -> None
        pass  # TODO

    def _collect_current_issues(self, conn):
        # type: (rethinkdb.net.Connection) -> None
        pass  # TODO

    # TODO: version metadata.
    # TODO: custom queries. (Hint: look at `QueryManager`.)
    # TODO: allow not sending default metrics.
    # TODO: decide if and how to deal with `identifier_format`: https://rethinkdb.com/api/python/table/#description


def _query_server_stats(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Tuple[Server, ServerStats]]

    # Here, we want to retrieve each server in the cluster along with its statistics.
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
