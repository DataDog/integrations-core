# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

CHECK_NAME = 'rethinkdb'

IMAGE = 'rethinkdb:2.4.0'

HOST = get_docker_hostname()


# Cluster configuration.
# NOTE: server information used below is tightly coupled to the Docker Compose setup.

SERVER_TAGS = {
    'server0': ['default', 'us', 'initial'],
    'server1': ['default', 'us', 'primary'],
    'server2': ['default', 'eu'],
    'server3': ['default', 'eu'],
}
SERVERS = set(SERVER_TAGS)

CONNECT_SERVER_NAME = 'server0'
CONNECT_SERVER_PORT = 28015

PROXY_PORT = 28018

DATABASE = 'doghouse'
HEROES_TABLE = 'heroes'

# NOTE: Hello, reader! It may not be immediately obvious what's going on below, so let me explain.
#
# ARethinkDB cluster is dynamic: as nodes, shards or replicas are added or removed, the distribution of
# data may change -- also known as "rebalancing".
# Most of the default metrics we collect are emitted regardless of the state of the cluster.
# But some metrics are only emitted when the cluster is evolving.
# (For example, this includes metrics about backfill jobs.)
#
# So, in order for all default metrics to be emitted during tests, we have one "initial" configuration
# for a single-server cluster, which is used as a starting point:
HEROES_TABLE_SINGLE_SERVER_CONFIG = {'shards': 1, 'replicas': {'initial': 1}, 'primary_replica_tag': 'initial'}
HEROES_TABLE_SERVER_INITIAL = 'server0'  # (Because it's the only server tagged as 'initial'.)
# We'll then create a table there and fill it with data.
# Then, we'll switch to a "replicated" configuration, which changes the primary replica, and replicates the
# table across more servers:
HEROES_TABLE_REPLICATED_PRIMARY_REPLICA_TAG = 'primary'
HEROES_TABLE_REPLICATED_CONFIG = {
    'shards': 1,
    'replicas': {'primary': 1, 'eu': 2},
    'primary_replica_tag': HEROES_TABLE_REPLICATED_PRIMARY_REPLICA_TAG,
}
HEROES_TABLE_SERVERS_REPLICATED = {'server1', 'server2', 'server3'}
HEROES_TABLE_REPLICAS_BY_SHARD = {0: HEROES_TABLE_SERVERS_REPLICATED}
# RethinkDB will then start moving data from server0 to those new replicas, emitting the transient metrics we'd
# like to test.
# The number of inserted documents should be large enough that any backfill job lasts long enough that its metrics
# are emitted during a check. Empirically, >80k documents seems to be enough:
HEROES_NUM_DOCUMENTS = 90000

HEROES_DOCUMENTS = [
    {
        "hero": "Magneto",
        "name": "Max Eisenhardt",
        "aka": ["Magnus", "Erik Lehnsherr", "Lehnsherr"],
        "magazine_titles": ["Alpha Flight", "Avengers", "Avengers West Coast"],
        "appearances_count": 42,
    }
] * HEROES_NUM_DOCUMENTS


# Metrics lists.

CLUSTER_STATISTICS_METRICS = (
    'rethinkdb.stats.cluster.queries_per_sec',
    'rethinkdb.stats.cluster.read_docs_per_sec',
    'rethinkdb.stats.cluster.written_docs_per_sec',
)

SERVER_STATISTICS_METRICS = (
    'rethinkdb.stats.server.queries_per_sec',
    'rethinkdb.stats.server.queries_total',
    'rethinkdb.stats.server.read_docs_per_sec',
    'rethinkdb.stats.server.read_docs_total',
    'rethinkdb.stats.server.written_docs_per_sec',
    'rethinkdb.stats.server.written_docs_total',
    'rethinkdb.stats.server.client_connections',
    'rethinkdb.stats.server.clients_active',  # NOTE: sent, but not documented on the RethinkDB website.
)

TABLE_STATISTICS_METRICS = (
    'rethinkdb.stats.table.read_docs_per_sec',
    'rethinkdb.stats.table.written_docs_per_sec',
)

REPLICA_STATISTICS_METRICS = (
    'rethinkdb.stats.table_server.read_docs_per_sec',
    'rethinkdb.stats.table_server.read_docs_total',
    'rethinkdb.stats.table_server.written_docs_per_sec',
    'rethinkdb.stats.table_server.written_docs_total',
    'rethinkdb.stats.table_server.cache.in_use_bytes',
    'rethinkdb.stats.table_server.disk.read_bytes_per_sec',
    'rethinkdb.stats.table_server.disk.read_bytes_total',
    'rethinkdb.stats.table_server.disk.written_bytes_per_sec',
    'rethinkdb.stats.table_server.disk.written_bytes_total',
    'rethinkdb.stats.table_server.disk.metadata_bytes',
    'rethinkdb.stats.table_server.disk.data_bytes',
    'rethinkdb.stats.table_server.disk.garbage_bytes',
    'rethinkdb.stats.table_server.disk.preallocated_bytes',
)

TABLE_STATUS_METRICS = (
    'rethinkdb.table_status.ready_for_outdated_reads',
    'rethinkdb.table_status.ready_for_reads',
    'rethinkdb.table_status.ready_for_writes',
    'rethinkdb.table_status.all_replicas_ready',
    'rethinkdb.table_status.shards.total',
)

TABLE_STATUS_SHARDS_METRICS = (
    'rethinkdb.table_status.shards.replicas.total',
    'rethinkdb.table_status.shards.replicas.primary.total',
)

TABLE_STATUS_SHARDS_REPLICA_STATE_METRICS = (
    'rethinkdb.table_status.shards.replicas.state.ready',
    'rethinkdb.table_status.shards.replicas.state.transitioning',
    'rethinkdb.table_status.shards.replicas.state.backfilling',
    'rethinkdb.table_status.shards.replicas.state.disconnected',
    'rethinkdb.table_status.shards.replicas.state.waiting_for_primary',
    'rethinkdb.table_status.shards.replicas.state.waiting_for_quorum',
)

SERVER_STATUS_METRICS = (
    'rethinkdb.server_status.network.time_connected',
    'rethinkdb.server_status.network.connected_to.total',
    'rethinkdb.server_status.network.connected_to.pending.total',
    'rethinkdb.server_status.process.time_started',
)

QUERY_JOBS_METRICS = ('rethinkdb.jobs.query.duration',)

# TODO: trigger index construction
INDEX_CONSTRUCTION_JOBS_METRICS = (
    'rethinkdb.jobs.index_construction.duration',
    'rethinkdb.jobs.index_construction.progress',
)

BACKFILL_JOBS_METRICS = (
    'rethinkdb.jobs.backfill.duration',
    'rethinkdb.jobs.backfill.progress',
)

CURRENT_ISSUES_METRICS = (
    'rethinkdb.current_issues.log_write_error.total',
    'rethinkdb.current_issues.server_name_collision.total',
    'rethinkdb.current_issues.db_name_collision.total',
    'rethinkdb.current_issues.table_name_collision.total',
    'rethinkdb.current_issues.outdated_index.total',
    'rethinkdb.current_issues.table_availability.total',
    'rethinkdb.current_issues.memory_error.total',
    'rethinkdb.current_issues.non_transitive_error.total',
)
