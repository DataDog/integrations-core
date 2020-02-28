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
    'server0': ['default', 'us'],
    'server1': ['default', 'us', 'primary'],
    'server2': ['default', 'eu'],
}
SERVERS = set(SERVER_TAGS)

CONNECT_SERVER_NAME = 'server0'
CONNECT_SERVER_PORT = 28015

PROXY_PORT = 28018

DATABASE = 'doghouse'

HEROES_TABLE = 'heroes'
HEROES_TABLE_CONFIG = {
    'shards': 1,
    'replicas': {'primary': 1, 'eu': 1},
    'primary_replica_tag': 'primary',
}
HEROES_TABLE_SERVERS = {'server1', 'server2'}
HEROES_TABLE_PRIMARY_REPLICA = 'server1'
HEROES_TABLE_REPLICAS_BY_SHARD = {0: HEROES_TABLE_SERVERS}
HEROES_TABLE_DOCUMENTS = [
    {
        "hero": "Magneto",
        "name": "Max Eisenhardt",
        "aka": ["Magnus", "Erik Lehnsherr", "Lehnsherr"],
        "magazine_titles": ["Alpha Flight", "Avengers", "Avengers West Coast"],
        "appearances_count": 42,
    },
    {
        "hero": "Professor Xavier",
        "name": "Charles Francis Xavier",
        "magazine_titles": ["Alpha Flight", "Avengers", "Bishop", "Defenders"],
        "appearances_count": 72,
    },
    {
        "hero": "Storm",
        "name": "Ororo Monroe",
        "magazine_titles": ["Amazing Spider-Man vs. Wolverine", "Excalibur", "Fantastic Four", "Iron Fist"],
        "appearances_count": 72,
    },
]
HEROES_TABLE_INDEX_FIELD = 'appearances_count'

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

TABLE_STATUS_SERVICE_CHECKS = (
    'rethinkdb.table_status.ready_for_outdated_reads',
    'rethinkdb.table_status.ready_for_reads',
    'rethinkdb.table_status.ready_for_writes',
    'rethinkdb.table_status.all_replicas_ready',
)

TABLE_STATUS_METRICS = ('rethinkdb.table_status.shards.total',)

TABLE_STATUS_SHARDS_METRICS = (
    'rethinkdb.table_status.shards.replicas.total',
    'rethinkdb.table_status.shards.replicas.primary.total',
)

SERVER_STATUS_METRICS = (
    'rethinkdb.server_status.network.time_connected',
    'rethinkdb.server_status.network.connected_to.total',
    'rethinkdb.server_status.network.connected_to.pending.total',
    'rethinkdb.server_status.process.time_started',
)

# NOTE: jobs metrics are not listed here as they are covered by unit tests instead of integration tests.

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


METRICS = (
    CLUSTER_STATISTICS_METRICS
    + SERVER_STATISTICS_METRICS
    + TABLE_STATISTICS_METRICS
    + REPLICA_STATISTICS_METRICS
    + TABLE_STATUS_METRICS
    + TABLE_STATUS_SHARDS_METRICS
    + SERVER_STATUS_METRICS
)


# Docker Compose configuration.

COMPOSE_FILE = os.path.join(HERE, 'compose', 'docker-compose.yaml')
COMPOSE_ENV_VARS = env_vars = {
    'RETHINKDB_IMAGE': IMAGE,
    'RETHINKDB_CONNECT_SERVER_PORT': str(CONNECT_SERVER_PORT),
    'RETHINKDB_PROXY_PORT': str(PROXY_PORT),
}
