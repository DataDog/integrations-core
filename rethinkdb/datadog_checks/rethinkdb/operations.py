# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Definition of high-level RethinkDB operations used by the RethinkDB check.

Python ReQL reference documentation: https://rethinkdb.com/api/python/
"""

from typing import Any, Iterator, List, Mapping, Optional, Tuple

import rethinkdb

from .config import Config
from .types import (
    ClusterStats,
    ConfigSummary,
    ConnectionServer,
    CurrentIssuesSummary,
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

# The usual entrypoint for building ReQL queries.
r = rethinkdb.r

# All system tables are located in this database.
# See: https://rethinkdb.com/docs/system-tables/
system = r.db('rethinkdb')


def get_connected_server_raw_version(conn, **kwargs):
    # type: (rethinkdb.net.Connection, **Any) -> Optional[str]
    """
    Return the RethinkDB version used by the server at the other end of the connection, in raw string format.
    """
    # See: https://rethinkdb.com/docs/system-tables/#server_status
    server = conn.server()  # type: ConnectionServer
    server_status = system.table('server_status').get(server['id']).run(conn)  # type: Optional[ServerStatus]

    if server_status is None:
        if server['proxy']:
            # Proxies don't have an entry in the `server_status` table.
            return None
        else:  # pragma: no cover
            raise RuntimeError('Expected a `server_status` entry for server {!r}, got none'.format(server))

    return server_status['process']['version']


def get_config_summary(conn, **kwargs):
    # type: (rethinkdb.net.Connection, **Any) -> Iterator[Tuple[ConfigSummary, List[str]]]
    """
    Return a summary of the cluster configuration.
    """
    table_config = system.table('table_config')
    server_config = system.table('server_config')
    db_config = system.table('db_config')

    # Need to `.run()` these separately because ReQL does not support putting grouped data in raw expressions yet.
    # See: https://github.com/rethinkdb/rethinkdb/issues/2067

    tables_per_database = table_config.group('db').count().run(conn)  # type: Mapping[str, int]

    secondary_indexes_per_table = (
        # NOTE: this is an example of a map-reduce query.
        # See: https://rethinkdb.com/docs/map-reduce/#a-more-complex-example
        table_config.pluck('name', 'indexes')
        .concat_map(lambda row: row['indexes'].map(lambda _: {'table': row['name']}))
        .group('table')
        .count()
        .run(conn)
    )  # type: Mapping[str, int]

    summary = {
        'servers': server_config.count(),
        'databases': db_config.count(),
        'tables_per_database': tables_per_database,
        'secondary_indexes_per_table': secondary_indexes_per_table,
    }  # type: ConfigSummary  # Enforce keys to match.

    yield r.expr(summary).run(conn), []


def get_cluster_statistics(conn, **kwargs):
    # type: (rethinkdb.net.Connection, **Any) -> Iterator[Tuple[ClusterStats, List[str]]]
    """
    Retrieve statistics about the cluster.
    """
    yield system.table('stats').get(['cluster']).run(conn), []


def get_servers_statistics(conn, **kwargs):
    # type: (rethinkdb.net.Connection, **Any) -> Iterator[Tuple[ServerStats, List[str]]]
    """
    Retrieve statistics about each server in the cluster.
    """
    # For servers: stats['id'] = ['server', '<SERVER_ID>']
    is_server_stats_row = r.row['id'].nth(0) == 'server'
    server_id = r.row['id'].nth(1)

    stats = system.table('stats')
    server_config = system.table('server_config')

    rows = stats.filter(is_server_stats_row).eq_join(server_id, server_config).run(conn)  # type: Iterator[JoinRow]

    for row in rows:
        server_stats = row['left']  # type: ServerStats
        server = row['right']  # type: Server
        tags = ['server:{}'.format(server['name'])]
        tags.extend(server['tags'])
        yield server_stats, tags


def get_tables_statistics(conn, **kwargs):
    # type: (rethinkdb.net.Connection, **Any) -> Iterator[Tuple[TableStats, List[str]]]
    """
    Retrieve statistics about each table in the cluster.
    """
    # For tables: stats['id'] = ['table', '<TABLE_ID>']
    is_table_stats_row = r.row['id'].nth(0) == 'table'
    table_id = r.row['id'].nth(1)

    stats = system.table('stats')
    table_config = system.table('table_config')

    rows = stats.filter(is_table_stats_row).eq_join(table_id, table_config).run(conn)  # type: Iterator[JoinRow]

    for row in rows:
        table_stats = row['left']  # type: TableStats
        table = row['right']  # type: Table
        tags = ['table:{}'.format(table['name']), 'database:{}'.format(table['db'])]
        yield table_stats, tags


def get_replicas_statistics(conn, **kwargs):
    # type: (rethinkdb.net.Connection, **Any) -> Iterator[Tuple[ReplicaStats, List[str]]]
    """
    Retrieve statistics about each replica (table/server pair) in the cluster.
    """
    # NOTE: To reduce bandwidth usage, we make heavy use of the `.pluck()` operation, i.e. ask RethinkDB
    # for a specific set of fields, instead of sending entire objects, which can be expensive when joining
    # data as we do here.
    # See: https://rethinkdb.com/api/python/pluck/

    stats = system.table('stats')
    server_config = system.table('server_config')
    table_config = system.table('table_config')
    table_status = system.table(
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
            lambda row: (row['replicas'].map(lambda replica: row.merge({'replica': replica.pluck('server', 'state')})))
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

    rows = query.run(conn)  # type: Iterator[Mapping[str, Any]]

    for row in rows:
        table = row['table']  # type: Table
        server = row['server']  # type: Server
        replica = row['replica']  # type: ShardReplica
        replica_stats = row['stats']  # type: ReplicaStats

        tags = [
            'table:{}'.format(table['name']),
            'database:{}'.format(table['db']),
            'server:{}'.format(server['name']),
            'state:{}'.format(replica['state']),
        ]
        tags.extend(server['tags'])

        yield replica_stats, tags


def get_table_statuses(conn, **kwargs):
    # type: (rethinkdb.net.Connection, **Any) -> Iterator[Tuple[TableStatus, List[str]]]
    """
    Retrieve the status of each table in the cluster.
    """
    for table_status in system.table('table_status').run(conn):  # type: TableStatus
        tags = ['table:{}'.format(table_status['name']), 'database:{}'.format(table_status['db'])]
        yield table_status, tags


def get_server_statuses(conn, **kwargs):
    # type: (rethinkdb.net.Connection, **Any) -> Iterator[Tuple[ServerStatus, List[str]]]
    """
    Retrieve the status of each server in the cluster.
    """
    for server_status in system.table('server_status').run(conn):  # type: ServerStatus
        tags = ['server:{}'.format(server_status['name'])]
        yield server_status, tags


def get_system_jobs(conn, config, **kwargs):
    # type: (rethinkdb.net.Connection, Config, **Any) -> Iterator[Tuple[Job, List[str]]]
    """
    Retrieve all the currently running system jobs.
    """
    for job in system.table('jobs').run(conn):  # type: Job
        tags = ['job_type:{}'.format(job['type'])]
        tags.extend('server:{}'.format(server) for server in job['servers'])

        # Follow job types listed on: https://rethinkdb.com/docs/system-jobs/#document-schema

        if job['type'] == 'query':
            # A query job only exists while the query is running, and its `duration` is unstable (it changes depending
            # on when the check is executed), so it doesn't make sense to submit metrics from these documents.
            # So let's skip them. (Query duration information should come from a persistent source, eg slow logs.)
            continue
        elif job['type'] == 'disk_compaction':
            # Ongoing task on each server. Duration is `null` and `info` is empty, so nothing interesting there.
            continue
        elif job['type'] == 'index_construction':
            tags.extend(
                [
                    'database:{}'.format(job['info']['db']),
                    'table:{}'.format(job['info']['table']),
                    'index:{}'.format(job['info']['index']),
                ]
            )
        elif job['type'] == 'backfill':
            tags.extend(
                [
                    'database:{}'.format(job['info']['db']),
                    'destination_server:{}'.format(job['info']['destination_server']),
                    'source_server:{}'.format(job['info']['source_server']),
                    'table:{}'.format(job['info']['table']),
                ]
            )
        else:
            raise RuntimeError('Unknown job type: {!r}'.format(job['type']))

        yield job, tags


def get_current_issues_summary(conn, **kwargs):
    # type: (rethinkdb.net.Connection, **Any) -> Iterator[Tuple[CurrentIssuesSummary, List[str]]]
    """
    Retrieve a summary of problems detected within the cluster.
    """
    current_issues = system.table('current_issues').pluck('type', 'critical')

    # NOTE: Need to `.run()` these separately because ReQL does not support putting grouped data in raw
    # expressions yet. See: https://github.com/rethinkdb/rethinkdb/issues/2067

    issues_by_type = current_issues.group('type').count().run(conn)  # type: Mapping[str, int]
    critical_issues_by_type = (
        current_issues.filter(r.row['critical']).group('type').count().run(conn)
    )  # type: Mapping[str, int]

    yield {'issues': issues_by_type, 'critical_issues': critical_issues_by_type}, []
