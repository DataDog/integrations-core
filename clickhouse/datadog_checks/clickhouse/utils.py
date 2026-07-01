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


def cluster_aware_query(base: dict, select: str, table: str, where: str = '') -> dict:
    """Build a cluster-aware variant that reads all replicas and tags each row per node."""
    tail = f' {where}' if where else ''
    return {
        'name': base['name'],
        'query': (
            f"SELECT {select}, hostName() AS {CLUSTER_NODE_TAG} "
            f"FROM clusterAllReplicas('default', system.{table}){tail}"
        ),
        'columns': [*base['columns'], {'name': CLUSTER_NODE_TAG, 'type': 'tag'}],
    }


def parse_version(version: str) -> list[int]:
    return [int(v) for v in version.split('.')]
