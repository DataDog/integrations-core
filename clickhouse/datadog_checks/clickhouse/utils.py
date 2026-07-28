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
# Raises on the server side when the macro is undefined.
CLUSTER_MACRO_QUERY = "SELECT getMacro('cluster')"

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
# more than one cluster.
CLUSTER_NAME_QUERY = (
    "SELECT cluster FROM system.clusters "
    "WHERE is_local AND cluster NOT IN ({excluded}) AND cluster NOT LIKE '{prefix}%' "
    "ORDER BY cluster LIMIT 1".format(
        excluded=', '.join(f"'{name}'" for name in BUILTIN_SAMPLE_CLUSTERS),
        prefix=CLUSTER_GROUP_PREFIX,
    )
)


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
