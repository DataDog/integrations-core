# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

from typing import Any, Iterator, Mapping, Tuple

import rethinkdb

from .connections import Connection, ConnectionServer
from .types import (
    ClusterStats,
    ConfigTotals,
    CurrentIssuesTotals,
    Job,
    JoinRow,
    ReplicaStats,
    Server,
    ServerStats,
    ServerStatus,
    ShardReplica,
    Table,
    TableStats,
    TableStatus,
)


class QueryEngine(object):
    """
    Definition of RethinkDB queries used by the RethinkDB check.

    Python ReQL reference documentation: https://rethinkdb.com/api/python/
    """

    def __init__(self, r=None):
        # type: (rethinkdb.RethinkDB) -> None
        self._r = rethinkdb.r if r is None else r

    def query_connected_server_version_string(self, conn):
        # type: (Connection) -> str
        """
        Return the raw string of the RethinkDB version used by the server at the other end of the connection.
        """
        r = self._r
        # See: https://rethinkdb.com/docs/system-tables/#server_status
        server = conn.server()  # type: ConnectionServer
        server_status = conn.run(r.db('rethinkdb').table('server_status').get(server['id']))  # type: ServerStatus
        return server_status['process']['version']

    def query_config_totals(self, conn):
        # type: (Connection) -> ConfigTotals
        r = self._r

        table_config = r.db('rethinkdb').table('table_config')
        server_config = r.db('rethinkdb').table('server_config')
        db_config = r.db('rethinkdb').table('db_config')

        # Need to `.run()` these separately because ReQL does not support putting grouped data in raw expressions yet.
        # See: https://github.com/rethinkdb/rethinkdb/issues/2067

        tables_per_database = conn.run(table_config.group('db').count())  # type: Mapping[str, int]

        secondary_indexes_per_table = conn.run(
            # NOTE: this is an example of a map-reduce query.
            # See: https://rethinkdb.com/docs/map-reduce/#a-more-complex-example
            table_config.pluck('name', 'indexes')
            .concat_map(lambda row: row['indexes'].map(lambda _: {'table': row['name']}))
            .group('table')
            .count()
        )  # type: Mapping[str, int]

        totals = {
            'servers': server_config.count(),
            'databases': db_config.count(),
            'tables_per_database': tables_per_database,
            'secondary_indexes_per_table': secondary_indexes_per_table,
        }  # type: ConfigTotals  # Enforce keys to match.

        return conn.run(r.expr(totals))

    def query_cluster_stats(self, conn):
        # type: (Connection) -> ClusterStats
        """
        Retrieve statistics about the cluster.
        """
        return conn.run(self._r.db('rethinkdb').table('stats').get(['cluster']))

    def query_servers_with_stats(self, conn):
        # type: (Connection) -> Iterator[Tuple[Server, ServerStats]]
        """
        Retrieve each server in the cluster along with its statistics.
        """
        r = self._r

        # For servers: stats['id'] = ['server', '<SERVER_ID>']
        is_server_stats_row = r.row['id'].nth(0) == 'server'
        server_id = r.row['id'].nth(1)

        stats = r.db('rethinkdb').table('stats')
        server_config = r.db('rethinkdb').table('server_config')

        rows = conn.run(stats.filter(is_server_stats_row).eq_join(server_id, server_config))  # type: Iterator[JoinRow]

        for row in rows:
            server_stats = row['left']  # type: ServerStats
            server = row['right']  # type: Server
            yield server, server_stats

    def query_tables_with_stats(self, conn):
        # type: (Connection) -> Iterator[Tuple[Table, TableStats]]
        """
        Retrieve each table in the cluster along with its statistics.
        """
        r = self._r

        # For tables: stats['id'] = ['table', '<TABLE_ID>']
        is_table_stats_row = r.row['id'].nth(0) == 'table'
        table_id = r.row['id'].nth(1)

        stats = r.db('rethinkdb').table('stats')
        table_config = r.db('rethinkdb').table('table_config')

        rows = conn.run(stats.filter(is_table_stats_row).eq_join(table_id, table_config))  # type: Iterator[JoinRow]

        for row in rows:
            table_stats = row['left']  # type: TableStats
            table = row['right']  # type: Table
            yield table, table_stats

    def query_replicas_with_stats(self, conn):
        # type: (Connection) -> Iterator[Tuple[Table, Server, ShardReplica, ReplicaStats]]
        """
        Retrieve each replica (table/server pair) in the cluster along with its statistics.
        """
        r = self._r

        # NOTE: To reduce bandwidth usage, we make heavy use of the `.pluck()` operation, i.e. ask RethinkDB
        # for a specific set of fields, instead of sending entire objects, which can be expensive when joining
        # data as we do here.
        # See: https://rethinkdb.com/api/python/pluck/

        stats = r.db('rethinkdb').table('stats')
        server_config = r.db('rethinkdb').table('server_config')
        table_config = r.db('rethinkdb').table('table_config')
        table_status = r.db('rethinkdb').table(
            'table_status',
            # Required so that we can join on 'server_config' below without having to look up UUIDs from names.
            # See: https://rethinkdb.com/api/python/table/#description
            identifier_format='uuid',
        )

        query = (
            # Start from table statuses, as they contain the list of replicas for each shard of the table.
            # See: https://rethinkdb.com/docs/system-tables/#table_status
            table_status.pluck('id', {'shards': ['replicas']})
            .merge({'table': r.row['id']})
            .without('id')
            # Flatten each table status entry into one entry per shard and replica.
            .concat_map(lambda row: row['shards'].map(lambda shard: row.merge(shard.pluck('replicas'))))
            .without('shards')
            .concat_map(
                lambda row: (
                    row['replicas'].map(lambda replica: row.merge({'replica': replica.pluck('server', 'state')}))
                )
            )
            .without('replicas')
            # Grab table information for each replica.
            # See: https://rethinkdb.com/docs/system-tables#table_config
            .merge({'table': table_config.get(r.row['table']).pluck('id', 'db', 'name')})
            # Grab server information for each replica.
            # See: https://rethinkdb.com/docs/system-tables#server_config
            .merge({'server': server_config.get(r.row['replica']['server'])})
            .filter(r.row['server'])  # Skip replicas stored on disconnected servers.
            .merge({'server': r.row['server'].pluck('id', 'name', 'tags')})
            # Grab statistics for each replica.
            # See: https://rethinkdb.com/docs/system-stats/#replica-tableserver-pair
            .merge(
                {
                    'stats': stats.get(['table_server', r.row['table']['id'], r.row['server']['id']]).pluck(
                        'query_engine', 'storage_engine'
                    ),
                }
            )
        )

        rows = conn.run(query)  # type: Iterator[Mapping[str, Any]]

        for row in rows:
            table = row['table']  # type: Table
            server = row['server']  # type: Server
            replica = row['replica']  # type: ShardReplica
            replica_stats = row['stats']  # type: ReplicaStats
            yield table, server, replica, replica_stats

    def query_table_status(self, conn):
        # type: (Connection) -> Iterator[TableStatus]
        """
        Retrieve the status of each table in the cluster.
        """
        return conn.run(self._r.db('rethinkdb').table('table_status'))

    def query_server_status(self, conn):
        # type: (Connection) -> Iterator[ServerStatus]
        """
        Retrieve the status of each server in the cluster.
        """
        return conn.run(self._r.db('rethinkdb').table('server_status'))

    def query_system_jobs(self, conn):
        # type: (Connection) -> Iterator[Job]
        """
        Retrieve all the currently running system jobs.
        """
        return conn.run(self._r.db('rethinkdb').table('jobs'))

    def query_current_issues_totals(self, conn):
        # type: (Connection) -> CurrentIssuesTotals
        """
        Retrieve all the problems detected with the cluster.
        """
        r = self._r

        current_issues = r.db('rethinkdb').table('current_issues').pluck('type', 'critical')
        critical_current_issues = current_issues.filter(r.row['critical'])

        # NOTE: Need to `.run()` these separately because ReQL does not support putting grouped data in raw
        # expressions yet. See: https://github.com/rethinkdb/rethinkdb/issues/2067

        issues_by_type = conn.run(current_issues.group('type').count())  # type: Mapping[str, int]
        critical_issues_by_type = conn.run(critical_current_issues.group('type').count())  # type: Mapping[str, int]

        totals = {
            'issues': current_issues.count(),
            'critical_issues': critical_current_issues.count(),
            'issues_by_type': issues_by_type,
            'critical_issues_by_type': critical_issues_by_type,
        }  # type: CurrentIssuesTotals  # Enforce keys to match.

        return conn.run(r.expr(totals))
