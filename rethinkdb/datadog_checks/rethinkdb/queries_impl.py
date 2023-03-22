# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import collections
import itertools
from typing import Any, Dict, List, Optional  # noqa: F401

import rethinkdb

from .utils import to_time_elapsed
from .version import parse_version

r = rethinkdb.r

# See: https://rethinkdb.com/docs/system-tables/
SYSTEM = r.db('rethinkdb')
STATS = SYSTEM.table('stats')
DB_CONFIG = SYSTEM.table('db_config')
SERVER_CONFIG = SYSTEM.table('server_config')
SERVER_STATUS = SYSTEM.table('server_status')
TABLE_CONFIG = SYSTEM.table('table_config')
TABLE_STATUS = SYSTEM.table('table_status')
JOBS = SYSTEM.table('jobs')
CURRENT_ISSUES = SYSTEM.table('current_issues')


def get_cluster_metrics(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    """
    Return cluster-wide metrics.
    """
    cluster_counts = r.expr(
        {
            'servers': SERVER_CONFIG.count(),
            'databases': DB_CONFIG.count(),
        }
    ).run(conn)

    cluster_stats = STATS.get(['cluster']).run(conn)

    row = (
        cluster_counts['servers'],
        cluster_counts['databases'],
        cluster_stats['query_engine']['queries_per_sec'],
        cluster_stats['query_engine']['read_docs_per_sec'],
        cluster_stats['query_engine']['written_docs_per_sec'],
    )

    return [row]


def get_server_metrics(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    """
    Return metrics about each `server`.
    """
    # For servers, stats['id'] has the form ['server', '<SERVER_ID>']
    is_server_stats_row = r.row['id'].nth(0) == 'server'
    server_id = r.row['id'].nth(1)

    server_statuses = list(SERVER_STATUS.run(conn))
    joined_server_stats = STATS.filter(is_server_stats_row).eq_join(server_id, SERVER_CONFIG).run(conn)

    rows = []  # type: List[tuple]
    for document in joined_server_stats:
        server_stats = document['left']
        server = document['right']
        # Join stats and statuses in Python.
        server_status = next(status for status in server_statuses if status['name'] == server['name'])

        row = (
            server['name'],
            server['tags'],
            server_stats['query_engine']['client_connections'],
            server_stats['query_engine']['clients_active'],
            server_stats['query_engine']['queries_per_sec'],
            server_stats['query_engine']['queries_total'],
            server_stats['query_engine']['read_docs_per_sec'],
            server_stats['query_engine']['read_docs_total'],
            server_stats['query_engine']['written_docs_per_sec'],
            server_stats['query_engine']['written_docs_total'],
            to_time_elapsed(server_status['network']['time_connected']),
            len(server_status['network']['connected_to']),
            to_time_elapsed(server_status['process']['time_started']),
        )
        rows.append(row)

    return rows


def get_database_config_metrics(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    """
    Return metrics about each `db`.
    """
    query = TABLE_CONFIG.group('db').count()
    num_tables_per_database = query.run(conn)  # type: Dict[str, int]
    return [(database, num_tables) for database, num_tables in num_tables_per_database.items()]


def get_database_table_metrics(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    """
    Return metrics a about each `(database, table)` pair.
    """
    # For tables: stats['id'] has the form ['table', '<TABLE_ID>']
    is_table_stats_row = r.row['id'].nth(0) == 'table'
    table_id = r.row['id'].nth(1)

    joined_table_stats = STATS.filter(is_table_stats_row).eq_join(table_id, TABLE_CONFIG).run(conn)
    table_statuses = list(TABLE_STATUS.run(conn))

    rows = []  # type: List[tuple]
    for document in joined_table_stats:
        table_stats = document['left']
        table = document['right']
        # Join stats and statuses in Python.
        table_status = next(status for status in table_statuses if status['name'] == table['name'])

        row = (
            table['db'],
            table['name'],
            table_stats['query_engine']['read_docs_per_sec'],
            table_stats['query_engine']['written_docs_per_sec'],
            len(table_status['shards']),
            table_status['status']['ready_for_outdated_reads'],
            table_status['status']['ready_for_reads'],
            table_status['status']['ready_for_writes'],
            table_status['status']['all_replicas_ready'],
        )
        rows.append(row)

    return rows


def get_table_config_metrics(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    """
    Return metrics about each `table`.
    """
    secondary_indexes_per_table = (
        TABLE_CONFIG.pluck('name', 'indexes')
        # [table1, table2, ...] -> [index1_1, index1_2, ..., index2_1, index2_2, ...]
        .concat_map(lambda row: row['indexes'].map(lambda _: {'table': row['name']}))
        # [...] -> {table1: [index1_1, index1_2, ...], table2: [index2_1, index2_2, ...]}
        .group('table')
        # {...} -> {table1: num_indexes_1, table2: num_indexes_2, ...}
        .count().run(conn)
    )  # type: Dict[str, int]

    return [(table_name, secondary_indexes) for table_name, secondary_indexes in secondary_indexes_per_table.items()]


def get_replica_metrics(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    """
    Return metrics about replicas.
    """
    table_status = SYSTEM.table(
        'table_status',
        # Required so that we can join on 'server_config' below without having to look up UUIDs from names.
        # See: https://rethinkdb.com/api/python/table/#description
        identifier_format='uuid',
    )

    results = (
        # Grab table statuses with shards and replica info.
        table_status.pluck('id', {'shards': ['replicas']})
        # table_status -> [shard1, shard2, ...]
        .concat_map(lambda row: row['shards'].map(lambda shard: row.merge(shard.pluck('replicas'))))
        .without('shards')
        # [shard1, shard2,...] -> [replica1_1, replica1_2, ..., replica2_1, replica2_2, ...]
        .concat_map(
            lambda row: (row['replicas'].map(lambda replica: row.merge({'replica': replica.pluck('server', 'state')})))
        )
        .without('replicas')
        # Attach table info to each replica.
        .merge({'table': TABLE_CONFIG.get(r.row['id']).pluck('id', 'db', 'name')})
        # Attach server info to each replica.
        .merge({'server': SERVER_CONFIG.get(r.row['replica']['server'])})
        .filter(r.row['server'])  # Skip replicas stored on disconnected servers.
        .merge({'server': r.row['server'].pluck('id', 'name', 'tags')})
        # Attach statistics to each replica.
        # See: https://rethinkdb.com/docs/system-stats/#replica-tableserver-pair
        .merge(
            {
                'stats': STATS.get(['table_server', r.row['table']['id'], r.row['server']['id']]).pluck(
                    'query_engine', 'storage_engine'
                ),
            }
        )
    ).run(conn)

    rows = []  # type: List[tuple]

    for document in results:
        row = (
            document['table']['name'],
            document['table']['db'],
            document['server']['name'],
            document['server']['tags'],
            document['replica']['state'],
            document['stats']['query_engine']['read_docs_per_sec'],
            document['stats']['query_engine']['read_docs_total'],
            document['stats']['query_engine']['written_docs_per_sec'],
            document['stats']['query_engine']['written_docs_total'],
            document['stats']['storage_engine']['cache']['in_use_bytes'],
            document['stats']['storage_engine']['disk']['read_bytes_per_sec'],
            document['stats']['storage_engine']['disk']['read_bytes_total'],
            document['stats']['storage_engine']['disk']['written_bytes_per_sec'],
            document['stats']['storage_engine']['disk']['written_bytes_total'],
            document['stats']['storage_engine']['disk']['space_usage']['metadata_bytes'],
            document['stats']['storage_engine']['disk']['space_usage']['data_bytes'],
            document['stats']['storage_engine']['disk']['space_usage']['garbage_bytes'],
            document['stats']['storage_engine']['disk']['space_usage']['preallocated_bytes'],
        )
        rows.append(row)

    return rows


def get_table_status_metrics(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    """
    Return metrics about table statuses.
    """
    results = TABLE_STATUS.run(conn)

    rows = []  # type: List[tuple]
    for table_status in results:
        row = (
            table_status['name'],
            table_status['db'],
            len(table_status['shards']),
            table_status['status']['ready_for_outdated_reads'],
            table_status['status']['ready_for_reads'],
            table_status['status']['ready_for_writes'],
            table_status['status']['all_replicas_ready'],
        )
        rows.append(row)

    return rows


def get_shard_metrics(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    """
    Return metrics for each shard of each `table` in each `db`.
    """
    results = (
        # Grab table statuses with shards info.
        TABLE_STATUS.pluck('id', {'shards': ['replicas', 'primary_replicas']})
        # table_status -> [shard1, shard2, ...]
        .concat_map(lambda row: row['shards'].map(lambda shard: row.merge(shard))).without('shards')
        # Attach table info to shards
        .merge({'table': TABLE_CONFIG.get(r.row['id']).pluck('id', 'db', 'name')})
    ).run(conn)

    rows = []  # type: List[tuple]
    for _, shards in itertools.groupby(results, lambda r: r['table']['name']):
        for shard_index, shard in enumerate(shards):
            row = (
                shard_index,
                shard['table']['name'],
                shard['table']['db'],
                len(shard['replicas']),
                len(shard['primary_replicas']),
            )
            rows.append(row)

    return rows


def get_job_metrics(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    """
    Return metrics about jobs running in the cluster.
    """
    jobs_per_type = JOBS.group('type').count().run(conn)  # type: Dict[str, int]

    rows = []  # type: List[tuple]
    for job_type, num_jobs in jobs_per_type.items():
        row = (
            job_type,
            num_jobs,
        )
        rows.append(row)

    return rows


def get_current_issues_metrics(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    """
    Return metrics about issues detected by RethinkDB.
    """
    current_issues = CURRENT_ISSUES.pluck('type', 'critical')
    # NOTE: Need to `.run()` these separately because ReQL does not support putting grouped data in raw
    # expressions yet. See: https://github.com/rethinkdb/rethinkdb/issues/2067
    issues_by_type = current_issues.group('type').count().run(conn)  # type: Dict[str, int]
    critical_issues_by_type = (
        current_issues.filter(r.row['critical']).group('type').count().run(conn)
    )  # type: Dict[str, int]

    # Join manually by job type. Note that groups may not have all job types (eg if there are 0 issues for that type).
    merged = collections.defaultdict(lambda: {'issues': 0, 'critical_issues': 0})  # type: Dict[str, Dict[str, int]]
    for job_type, issues in issues_by_type.items():
        merged[job_type]['issues'] = issues
    for job_type, critical_issues in critical_issues_by_type.items():
        merged[job_type]['critical_issues'] = critical_issues

    rows = []  # type: List[tuple]
    for job_type, document in merged.items():
        row = (
            job_type,
            document['issues'],
            document['critical_issues'],
        )
        rows.append(row)

    return rows


def get_version_metadata(conn):
    # type: (rethinkdb.net.Connection) -> List[tuple]
    # See: https://rethinkdb.com/docs/system-tables/#server_status
    server = conn.server()  # type: Dict[str, Any]
    server_status = SERVER_STATUS.get(server['id']).run(conn)  # type: Optional[Dict[str, Any]]

    if server_status is None:
        if server['proxy']:
            # Proxies don't have an entry in the `server_status` table.
            return []
        else:  # pragma: no cover
            raise RuntimeError('Expected a `server_status` entry for server {!r}, got none'.format(server))

    raw_version = server_status['process']['version']
    version = parse_version(raw_version)

    return [(version,)]
