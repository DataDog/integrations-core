# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Dict, List, Set

from datadog_checks.utils.common import get_docker_hostname

from ._types import ServerName

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

CHECK_NAME = 'rethinkdb'

IMAGE = 'rethinkdb:2.4.0'
RETHINKDB_VERSION = '2.4.0~0bionic'

HOST = get_docker_hostname()


# Servers.
# NOTE: server information is tightly coupled to the Docker Compose setup.

SERVER_TAGS = {
    'server0': ['default', 'us'],
    'server1': ['default', 'us', 'primary'],
    'server2': ['default', 'eu'],
}  # type: Dict[ServerName, List[str]]
SERVERS = {'server0', 'server1', 'server2'}  # type: Set[ServerName]

SERVER_PORTS = {'server0': 28015, 'server1': 28016, 'server2': 28017, 'proxy': 28018}  # type: Dict[ServerName, int]

# Users.

AGENT_USER = 'datadog-agent'
AGENT_PASSWORD = 'r3th1nK'
CLIENT_USER = 'doggo'

# TLS.

TLS_SERVER = 'server1'  # type: ServerName
TLS_DRIVER_KEY = os.path.join(HERE, 'data', 'tls', 'server.key')
TLS_DRIVER_CERT = os.path.join(HERE, 'data', 'tls', 'server.pem')
TLS_CLIENT_CERT = os.path.join(HERE, 'data', 'tls', 'client.pem')

# Database content.

DATABASE = 'doghouse'

HEROES_TABLE = 'heroes'
HEROES_TABLE_CONFIG = {
    'shards': 1,
    'replicas': {'primary': 1, 'eu': 1},
    'primary_replica_tag': 'primary',
}
HEROES_TABLE_SERVERS = {'server1', 'server2'}  # type: Set[ServerName]
HEROES_TABLE_PRIMARY_REPLICA = 'server1'  # type: ServerName
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

CONFIG_TOTALS_METRICS = (
    'rethinkdb.server.total',
    'rethinkdb.database.total',
    'rethinkdb.database.table.total',
    'rethinkdb.table.secondary_index.total',
)

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
    'rethinkdb.current_issues.total',
    'rethinkdb.current_issues.critical.total',
    'rethinkdb.current_issues.log_write_error.total',
    'rethinkdb.current_issues.log_write_error.critical.total',
    'rethinkdb.current_issues.server_name_collision.total',
    'rethinkdb.current_issues.server_name_collision.critical.total',
    'rethinkdb.current_issues.db_name_collision.total',
    'rethinkdb.current_issues.db_name_collision.critical.total',
    'rethinkdb.current_issues.table_name_collision.total',
    'rethinkdb.current_issues.table_name_collision.critical.total',
    'rethinkdb.current_issues.outdated_index.total',
    'rethinkdb.current_issues.outdated_index.critical.total',
    'rethinkdb.current_issues.table_availability.total',
    'rethinkdb.current_issues.table_availability.critical.total',
    'rethinkdb.current_issues.memory_error.total',
    'rethinkdb.current_issues.memory_error.critical.total',
    'rethinkdb.current_issues.non_transitive_error.total',
    'rethinkdb.current_issues.non_transitive_error.critical.total',
)

CURRENT_ISSUES_METRICS_SUBMITTED_ALWAYS = (
    'rethinkdb.current_issues.total',
    'rethinkdb.current_issues.critical.total',
)

CURRENT_ISSUES_METRICS_SUBMITTED_IF_DISCONNECTED_SERVERS = (
    'rethinkdb.current_issues.table_availability.total',
    'rethinkdb.current_issues.table_availability.critical.total',
)

assert set(CURRENT_ISSUES_METRICS).issuperset(CURRENT_ISSUES_METRICS_SUBMITTED_ALWAYS)
assert set(CURRENT_ISSUES_METRICS).issuperset(CURRENT_ISSUES_METRICS_SUBMITTED_IF_DISCONNECTED_SERVERS)


E2E_METRICS = (
    CONFIG_TOTALS_METRICS
    + CLUSTER_STATISTICS_METRICS
    + SERVER_STATISTICS_METRICS
    + TABLE_STATISTICS_METRICS
    + REPLICA_STATISTICS_METRICS
    + TABLE_STATUS_METRICS
    + TABLE_STATUS_SHARDS_METRICS
    + SERVER_STATUS_METRICS
    + CURRENT_ISSUES_METRICS_SUBMITTED_ALWAYS
)


# Docker Compose configuration.

COMPOSE_FILE = os.path.join(HERE, 'compose', 'docker-compose.yaml')

COMPOSE_ENV_VARS = env_vars = {
    'RETHINKDB_IMAGE': IMAGE,
    'RETHINKDB_PORT_SERVER0': str(SERVER_PORTS['server0']),
    'RETHINKDB_PORT_SERVER1': str(SERVER_PORTS['server1']),
    'RETHINKDB_PORT_SERVER2': str(SERVER_PORTS['server2']),
    'RETHINKDB_PORT_PROXY': str(SERVER_PORTS['proxy']),
    'RETHINKDB_TLS_DRIVER_KEY': TLS_DRIVER_KEY,
    'RETHINKDB_TLS_DRIVER_CERT': TLS_DRIVER_CERT,
}
