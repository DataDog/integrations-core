# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime as dt
import logging
import time
from typing import Iterator

import rethinkdb

from datadog_checks.base import AgentCheck

from ..queries import QueryEngine
from ..types import Metric

logger = logging.getLogger(__name__)


def collect_table_status(engine, conn):
    # type: (QueryEngine, rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about table statuses.

    See: https://rethinkdb.com/docs/system-tables/#table_status
    """
    logger.debug('collect_table_status')

    for table_status in engine.query_table_status(conn):
        logger.debug('table_status %r', table_status)

        table = table_status['name']
        database = table_status['db']

        tags = ['table:{}'.format(table), 'database:{}'.format(database)]

        yield {
            'type': 'service_check',
            'name': 'rethinkdb.table_status.ready_for_outdated_reads',
            'value': AgentCheck.OK if table_status['status']['ready_for_outdated_reads'] else AgentCheck.WARNING,
            'tags': tags,
        }

        yield {
            'type': 'service_check',
            'name': 'rethinkdb.table_status.ready_for_reads',
            'value': AgentCheck.OK if table_status['status']['ready_for_reads'] else AgentCheck.WARNING,
            'tags': tags,
        }

        yield {
            'type': 'service_check',
            'name': 'rethinkdb.table_status.ready_for_writes',
            'value': AgentCheck.OK if table_status['status']['ready_for_writes'] else AgentCheck.WARNING,
            'tags': tags,
        }

        yield {
            'type': 'service_check',
            'name': 'rethinkdb.table_status.all_replicas_ready',
            'value': AgentCheck.OK if table_status['status']['all_replicas_ready'] else AgentCheck.WARNING,
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.table_status.shards.total',
            'value': len(table_status['shards']),
            'tags': tags,
        }

        for index, shard in enumerate(table_status['shards']):
            shard_tags = tags + ['shard:{}'.format(index)]

            yield {
                'type': 'gauge',
                'name': 'rethinkdb.table_status.shards.replicas.total',
                'value': len(shard['replicas']),
                'tags': shard_tags,
            }

            yield {
                'type': 'gauge',
                'name': 'rethinkdb.table_status.shards.replicas.primary.total',
                'value': len(shard['primary_replicas']),
                'tags': shard_tags,
            }


def collect_server_status(engine, conn):
    # type: (QueryEngine, rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about server statuses.

    See: https://rethinkdb.com/docs/system-tables/#server_status
    """
    logger.debug('collect_server_status')

    for server_status in engine.query_server_status(conn):
        logger.debug('server_status %r', server_status)

        server = server_status['name']
        network = server_status['network']
        process = server_status['process']

        tags = ['server:{}'.format(server)]

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.server_status.network.time_connected',
            'value': _to_timestamp(network['time_connected']),
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.server_status.network.connected_to.total',
            'value': len([other for other, connected in network['connected_to'].items() if connected]),
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.server_status.network.connected_to.pending.total',
            'value': len([other for other, connected in network['connected_to'].items() if not connected]),
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.server_status.process.time_started',
            'value': _to_timestamp(process['time_started']),
            'tags': tags,
        }


def _to_timestamp(datetime):
    # type: (dt.datetime) -> float
    try:
        return datetime.timestamp()  # type: ignore  # (Mypy is run in --py2 mode.)
    except AttributeError:  # pragma: no cover
        # Python 2.
        return time.mktime(datetime.now().timetuple())
