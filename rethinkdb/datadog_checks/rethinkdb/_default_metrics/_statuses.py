# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

import itertools
from typing import Iterator

import rethinkdb

from .._queries import query_server_status, query_table_status
from .._types import Metric, ReplicaState


def collect_status_metrics(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about server and table statuses.

    See: https://rethinkdb.com/docs/system-tables/#status-tables
    """
    metrics = itertools.chain(_collect_table_status_metrics(conn), _collect_server_status_metrics(conn))

    for metric in metrics:
        yield metric


def _collect_table_status_metrics(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    for table_status in query_table_status(conn):
        table = table_status['name']
        database = table_status['db']

        tags = ['table:{}'.format(table), 'database:{}'.format(database)]

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.table_status.ready_for_outdated_reads',
            'value': 1 if table_status['status']['ready_for_outdated_reads'] else 0,
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.table_status.ready_for_reads',
            'value': 1 if table_status['status']['ready_for_reads'] else 0,
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.table_status.ready_for_writes',
            'value': 1 if table_status['status']['ready_for_writes'] else 0,
            'tags': tags,
        }

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.table_status.all_replicas_ready',
            'value': 1 if table_status['status']['all_replicas_ready'] else 0,
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

            for replica in shard['replicas']:
                server = replica['server']
                replica_tags = shard_tags + ['server:{}'.format(server)]

                # Helper function to benefit from type checking on 'ReplicaState' literals.
                def _replica_state(state):
                    # type: (ReplicaState) -> Metric
                    return {
                        'type': 'gauge',
                        'name': 'rethinkdb.table_status.shards.replicas.state.{}'.format(state),
                        'value': 1 if replica['state'] == state else 0,
                        'tags': replica_tags,
                    }

                yield _replica_state('ready')
                yield _replica_state('transitioning')
                yield _replica_state('backfilling')
                yield _replica_state('disconnected')
                yield _replica_state('waiting_for_primary')
                yield _replica_state('waiting_for_quorum')


def _collect_server_status_metrics(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    for server in query_server_status(conn):
        name = server['name']
        network = server['network']
        process = server['process']

        tags = ['server:{}'.format(name)]

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.server_status.network.time_connected',
            'value': network['time_connected'].timestamp(),
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
            'value': process['time_started'].timestamp(),
            'tags': tags,
        }
