# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

# We tell the server to not send the stack trace but
# the library leaves the start indication regardless.
STACK_TRACE_LEFTOVER = re.compile(r'\.?\s*Stack trace:\s*$')


class ErrorSanitizer(object):
    def __init__(self, password):
        self.password = password

    @staticmethod
    def clean(error):
        return STACK_TRACE_LEFTOVER.sub('', error)

    def scrub(self, error):
        if self.password:
            return error.replace(self.password, '**********')

        return error


def compact_query(query):
    return re.sub(r'\n\s+', ' ', query.strip())


# Tag added to per-node metrics when collecting from all replicas in single endpoint mode.
CLUSTER_NODE_TAG = 'clickhouse_node'

# Tag identifying the cluster this instance belongs to, one level above CLUSTER_NODE_TAG.
CLUSTER_TAG = 'clickhouse_cluster'

# The {cluster} macro used by ON CLUSTER DDL. Tried first because it is only ever set when an
# operator deliberately configured a cluster, which makes it the highest-signal source.
# Read from system.macros rather than getMacro('cluster'): the function raises server-side when the
# macro is undefined, which increments FailedQuery/FailedSelectQuery and pollutes the customer's
# clickhouse.query.failed metrics. Selecting from the table returns zero rows instead, no error.
CLUSTER_MACRO_QUERY = "SELECT substitution FROM system.macros WHERE macro = 'cluster'"

# Sample clusters that ClickHouse ships in its own default config (present through at least 21.x,
# gone by 24.8). They are indistinguishable from real clusters in system.clusters and would
# otherwise mislabel every stock instance, so they are excluded by name.
BUILTIN_SAMPLE_CLUSTERS = (
    'test_cluster_one_shard_three_replicas_localhost',
    'test_cluster_two_shards',
    'test_cluster_two_shards_internal_replication',
    'test_cluster_two_shards_localhost',
    'test_shard_localhost',
    'test_shard_localhost_secure',
    'test_unavailable_shard',
)

# ClickHouse Cloud exposes an internal 'all_groups.<cluster>' entry spanning every service group
# alongside the real cluster, and both are is_local. It sorts first alphabetically, so without this
# filter Cloud instances would be tagged all_groups.default while their data is actually collected
# from 'default' via clusterAllReplicas.
CLUSTER_GROUP_PREFIX = 'all_groups.'

# Fallback covering ClickHouse Cloud (returns 'default') and any deployment with remote_servers
# configured but no {cluster} macro. ORDER BY keeps the result stable when a node is a member of
# more than one cluster. The prefix filter uses startsWith rather than LIKE '<prefix>%': ClickHouse
# compiles a re2 regex for that LIKE pattern (bumping RegexpCreated, which surfaces as
# clickhouse.compilation.regex), whereas startsWith is a plain prefix comparison.
CLUSTER_NAME_QUERY = (
    "SELECT cluster FROM system.clusters "
    "WHERE is_local AND cluster NOT IN ({excluded}) AND NOT startsWith(cluster, '{prefix}') "
    "ORDER BY cluster LIMIT 1".format(
        excluded=', '.join(f"'{name}'" for name in BUILTIN_SAMPLE_CLUSTERS),
        prefix=CLUSTER_GROUP_PREFIX,
    )
)


# Tag identifying whether this instance is ClickHouse Cloud or self-hosted. The key and the value
# vocabulary follow the mongo integration, the other DBM check that reports a hosting model.
HOSTING_TYPE_TAG = 'hosting_type'


class HostingType:
    CLOUD = 'clickhouse-cloud'
    SELF_HOSTED = 'self-hosted'
    UNKNOWN = 'unknown'


# First hosting-type signal: the server-level cloud_mode setting, which ClickHouse Cloud ships
# enabled and self-hosted servers leave at its 0 default. Read from system.settings rather than
# calling getSetting('cloud_mode'): the function raises on the versions predating the setting
# (before 23.x), which increments FailedQuery/FailedSelectQuery and pollutes the customer's
# clickhouse.query.failed metric. Selecting from the table returns zero rows instead, no error —
# and zero rows is itself a definite negative, since Cloud only ever runs recent versions.
CLOUD_MODE_QUERY = "SELECT value FROM system.settings WHERE name = 'cloud_mode'"

# Second hosting-type signal: availability of SharedMergeTree, an engine that exists only in
# ClickHouse Cloud. Probes system.table_engines (which engines the server supports) rather than
# system.tables (which engines are in use), because a freshly provisioned Cloud service has no
# user tables yet but still lists the engine, and this avoids scanning every table. Filters with
# exact equality rather than LIKE: ClickHouse compiles a re2 regex for a LIKE pattern, bumping
# RegexpCreated, which surfaces as clickhouse.compilation.regex on the customer's own metrics.
SHARED_MERGE_TREE_QUERY = "SELECT count() FROM system.table_engines WHERE name = 'SharedMergeTree'"


def cluster_aware_query(base: dict) -> dict:
    """Build a cluster-aware variant that reads all replicas and tags each row per node.

    Derives the SELECT list and table from the base query, whose shape is always
    ``SELECT <cols> FROM system.<table>[ <trailing clause>]``.
    """
    select, _, tail = base['query'].partition(' FROM system.')
    table, sep, trailing = tail.partition(' ')
    return {
        'name': base['name'],
        'query': (
            f"{select}, hostName() AS {CLUSTER_NODE_TAG} "
            f"FROM clusterAllReplicas('default', system.{table}){sep}{trailing}"
        ),
        'columns': [*base['columns'], {'name': CLUSTER_NODE_TAG, 'type': 'tag'}],
    }


def parse_version(version: str) -> list[int]:
    return [int(v) for v in version.split('.')]
