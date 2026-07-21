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


def node_tag(node: str) -> str:
    """Build the per-node tag (``clickhouse_node:<node>``) attached to node-scoped data."""
    return f"{CLUSTER_NODE_TAG}:{node}"


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
