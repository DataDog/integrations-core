# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
Declarations used for type checking our code, including our manipulation of JSON documents returned by RethinkDB.
"""

from typing import Any, List, Literal, Tuple, TypedDict

# Lightweight shim to decouple collection functions from the check class.
Metric = TypedDict(
    'Metric', {'type': Literal['gauge', 'monotonic_count'], 'name': str, 'value': float, 'tags': List[str]}
)


# Configuration documents.
# See: https://rethinkdb.com/docs/system-tables/#configuration-tables

Server = TypedDict('Server', {'id': str, 'name': str, 'cache_size_mb': str, 'tags': List[str]})

Table = TypedDict('Table', {'id': str, 'name': str, 'db': str})  # TODO: more fields


# System statistics documents.
# See: https://rethinkdb.com/docs/system-stats/

ClusterQueryEngine = TypedDict(
    'ClusterQueryEngine', {'queries_per_sec': int, 'read_docs_per_sec': int, 'written_docs_per_sec': int},
)

ClusterStats = TypedDict('ClusterStats', {'id': Tuple[Literal['cluster']], 'query_engine': ClusterQueryEngine})

ServerQueryEngine = TypedDict(
    'ServerQueryEngine',
    {
        'client_connections': int,
        'clients_active': int,
        'queries_per_sec': int,
        'queries_total': int,
        'read_docs_per_sec': int,
        'read_docs_total': int,
        'written_docs_per_sec': int,
        'written_docs_total': int,
    },
)

ServerStats = TypedDict(
    'ServerStats', {'id': Tuple[Literal['server'], str], 'server': str, 'query_engine': ServerQueryEngine},
)

TableQueryEngine = TypedDict('TableQueryEngine', {'read_docs_per_sec': int, 'written_docs_per_sec': int})

TableStats = TypedDict(
    'TableStats', {'id': Tuple[Literal['table'], str], 'table': str, 'db': str, 'query_engine': TableQueryEngine},
)


# ReQL command results.
# See: https://rethinkdb.com/api/python/

# NOTE: Ideally 'left' and 'right' would be generics here, but this isn't supported by 'TypedDict' yet.
# See: https://github.com/python/mypy/issues/3863
EqJoinRow = TypedDict('EqJoinRow', {'left': Any, 'right': Any})
