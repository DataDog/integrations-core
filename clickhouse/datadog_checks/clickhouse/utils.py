# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from dataclasses import dataclass

from clickhouse_connect.driver.exceptions import OperationalError

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


def quote_string(value: str) -> str:
    """Render a SQL string literal, escaping a cluster name that arrives as server-supplied data."""
    escaped = value.replace('\\', '\\\\').replace("'", "\\'")
    return f"'{escaped}'"


def cluster_all_replicas(cluster: str, table: str) -> str:
    """Reference a system table on every replica of a cluster.

    Only Cloud names its cluster 'default'; a literal 'default' either raises UNKNOWN_CLUSTER or,
    against the stock localhost-only 'default' cluster, silently returns the local node alone.
    """
    return f"clusterAllReplicas({quote_string(cluster)}, system.{table})"


# The node serving the current connection. Read per emission rather than cached, since behind a
# single endpoint the connection can land on a different node after any reconnect.
CONNECT_NODE_QUERY = "SELECT hostName()"


def cluster_nodes_query(cluster: str) -> str:
    """Query listing every replica of a cluster currently serving traffic, one row per node.

    skip_unavailable_shards keeps one unreachable node from failing the whole fan-out.
    """
    return f"SELECT hostName() FROM {cluster_all_replicas(cluster, 'one')} SETTINGS skip_unavailable_shards=1"


HOSTING_TYPE_TAG = 'hosting_type'


class HostingType:
    CLOUD = 'clickhouse-cloud'
    SELF_HOSTED = 'self-hosted'
    UNKNOWN = 'unknown'


# system.settings avoids raising on versions predating cloud_mode (before 23.x).
CLOUD_MODE_QUERY = "SELECT value FROM system.settings WHERE name = 'cloud_mode'"

# table_engines lists supported engines even before any tables exist; exact match avoids a LIKE regex compile.
SHARED_MERGE_TREE_QUERY = "SELECT count() FROM system.table_engines WHERE name = 'SharedMergeTree'"


class TopologyProbe:
    CLUSTER_MACRO = 'cluster_macro'
    CLUSTER_NAME = 'cluster_name'
    CLOUD_MODE = 'cloud_mode'
    SHARED_MERGE_TREE = 'shared_merge_tree'
    CONNECT_NODE = 'connect_node'
    NODES = 'nodes'


class ProbeErrorKind:
    DENIED = 'denied'
    UNKNOWN_CLUSTER = 'unknown_cluster'
    AUTHENTICATION_FAILED = 'authentication_failed'
    TIMEOUT = 'timeout'
    CONNECTION = 'connection'
    ERROR = 'error'


class DbmCollectionStatus:
    ACTIVE = 'active'
    BLOCKED = 'blocked'
    DEGRADED = 'degraded'


DBM_BLOCKED_REASON_MISSING_GRANTS = 'missing_grants'

REMOTE_GRANT = 'REMOTE ON *.*'

PROBE_DEFAULT_GRANTS = {
    TopologyProbe.CLUSTER_MACRO: 'SELECT ON system.macros',
    TopologyProbe.CLUSTER_NAME: 'SELECT ON system.clusters',
    TopologyProbe.CLOUD_MODE: 'SELECT ON system.settings',
    TopologyProbe.SHARED_MERGE_TREE: 'SELECT ON system.table_engines',
    TopologyProbe.NODES: REMOTE_GRANT,
}

MISSING_GRANT_PATTERN = re.compile(r"necessary to have (?:the )?grant (?P<privilege>.+?) ON (?P<target>[^\s(]+)")
GRANT_COLUMN_LIST = re.compile(r'\([^)]*\)')


@dataclass(frozen=True)
class ProbeError:
    kind: str
    grants: tuple[str, ...] = ()
    message: str = ''


def missing_grants(message: str) -> tuple[str, ...]:
    """The table-level grants an ACCESS_DENIED message names, one per privilege, sorted.

    Column lists are dropped, and the REMOTE table function grant is reported in one spelling
    whether the server phrases it as `REMOTE ON *.*` or `READ ON REMOTE`.
    """
    match = MISSING_GRANT_PATTERN.search(message)
    if match is None:
        return ()
    target = match['target'].rstrip('.')
    grants = set()
    for privilege in GRANT_COLUMN_LIST.sub('', match['privilege']).split(','):
        privilege = privilege.strip()
        if 'REMOTE' in (privilege, target):
            grants.add(REMOTE_GRANT)
        elif privilege:
            grants.add(f'{privilege} ON {target}')
    return tuple(sorted(grants))


def classify_probe_error(probe: str, error: Exception) -> ProbeError:
    """Why a topology probe failed. Only ACCESS_DENIED is `denied`; every other failure keeps its own kind."""
    message = str(error)
    lowered = message.lower()
    if 'code: 497' in lowered or 'access_denied' in lowered or 'not enough privileges' in lowered:
        default_grants = (PROBE_DEFAULT_GRANTS[probe],) if probe in PROBE_DEFAULT_GRANTS else ()
        return ProbeError(ProbeErrorKind.DENIED, missing_grants(message) or default_grants, message)
    if 'code: 701' in lowered or 'cluster_doesnt_exist' in lowered or 'requested cluster' in lowered:
        return ProbeError(ProbeErrorKind.UNKNOWN_CLUSTER, message=message)
    if 'code: 516' in lowered or 'authentication_failed' in lowered:
        return ProbeError(ProbeErrorKind.AUTHENTICATION_FAILED, message=message)
    if isinstance(error, TimeoutError) or 'timeout' in lowered or 'timed out' in lowered:
        return ProbeError(ProbeErrorKind.TIMEOUT, message=message)
    if isinstance(error, OperationalError) and 'code: ' not in lowered:
        return ProbeError(ProbeErrorKind.CONNECTION, message=message)
    return ProbeError(ProbeErrorKind.ERROR, message=message)


def cluster_aware_query(base: dict, cluster: str) -> dict:
    """Build a cluster-aware variant that reads all replicas of a cluster and tags each row per node.

    Derives the SELECT list and table from the base query, whose shape is always
    ``SELECT <cols> FROM system.<table>[ <trailing clause>]``.
    """
    select, _, tail = base['query'].partition(' FROM system.')
    table, sep, trailing = tail.partition(' ')
    return {
        'name': base['name'],
        'query': (
            f"{select}, hostName() AS {CLUSTER_NODE_TAG} FROM {cluster_all_replicas(cluster, table)}{sep}{trailing}"
        ),
        'columns': [*base['columns'], {'name': CLUSTER_NODE_TAG, 'type': 'tag'}],
    }


LEADING_DIGITS = re.compile(r'\d+')


def parse_version(version: str) -> list[int]:
    parts = []
    for segment in version.split('.'):
        match = LEADING_DIGITS.match(segment)
        # do not include non-numeric version segments (e.g. Altinity's `altinityfips` suffix)
        if match is None:
            break
        parts.append(int(match.group()))
    return parts
