# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator, List, Tuple

from datadog_checks.base import AgentCheck
from datadog_checks.base.types import ServiceCheckStatus

from ..connections import Connection
from ..queries import QueryEngine
from ..types import ServerStatus, TableStatus
from ._base import DocumentMetricCollector

logger = logging.getLogger(__name__)


def transform_status(status):
    # type: (bool) -> ServiceCheckStatus
    return AgentCheck.OK if status else AgentCheck.WARNING


class TableStatusCollector(DocumentMetricCollector[TableStatus]):
    """
    Collect metrics about table statuses.

    See: https://rethinkdb.com/docs/system-tables/#table_status
    """

    name = 'table_status'
    group = 'table_status'

    metrics = [
        {'type': 'service_check', 'path': 'status.ready_for_outdated_reads', 'modifier': 'ok_warning'},
        {'type': 'service_check', 'path': 'status.ready_for_reads', 'modifier': 'ok_warning'},
        {'type': 'service_check', 'path': 'status.ready_for_writes', 'modifier': 'ok_warning'},
        {'type': 'service_check', 'path': 'status.all_replicas_ready', 'modifier': 'ok_warning'},
        {'type': 'gauge', 'path': 'shards', 'modifier': 'total'},
    ]

    enumerations = [
        {
            'path': 'shards',
            'index_tag': 'shard',
            'metrics': [
                {'type': 'gauge', 'path': 'replicas', 'modifier': 'total'},
                {'type': 'gauge', 'path': 'primary_replicas', 'modifier': 'total'},
            ],
        }
    ]

    def iter_documents(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Tuple[TableStatus, List[str]]]
        for table_status in engine.query_table_status(conn):
            tags = ['table:{}'.format(table_status['name']), 'database:{}'.format(table_status['db'])]
            yield table_status, tags


class ServerStatusCollector(DocumentMetricCollector[ServerStatus]):
    """
    Collect metrics about server statuses.

    See: https://rethinkdb.com/docs/system-tables/#server_status
    """

    name = 'server_status'
    group = 'server_status'

    metrics = [
        {'type': 'gauge', 'path': 'network.time_connected', 'modifier': 'timestamp'},
        {
            'type': 'gauge',
            'path': 'network.connected_to',
            'modifier': {
                'name': 'total',
                'map': lambda value: [other for other, connected in value.items() if connected],
            },
        },
        {
            'type': 'gauge',
            'path': 'network.connected_to',
            'name': 'network.not_connected_to',
            'modifier': {
                'name': 'total',
                'map': lambda value: [other for other, connected in value.items() if not connected],
            },
        },
        {'type': 'gauge', 'path': 'process.time_started', 'modifier': 'timestamp'},
    ]

    def iter_documents(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Tuple[ServerStatus, List[str]]]
        for server_status in engine.query_server_status(conn):
            tags = ['server:{}'.format(server_status['name'])]
            yield server_status, tags


collect_table_status = TableStatusCollector()
collect_server_status = ServerStatusCollector()
