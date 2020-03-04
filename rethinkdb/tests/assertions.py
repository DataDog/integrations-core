# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Set

from datadog_checks.base.stubs.aggregator import AggregatorStub

from ._types import ServerName
from .common import (
    CLUSTER_STATISTICS_METRICS,
    CURRENT_ISSUES_METRICS,
    CURRENT_ISSUES_METRICS_SUBMITTED_ALWAYS,
    CURRENT_ISSUES_METRICS_SUBMITTED_IF_DISCONNECTED_SERVERS,
    DATABASE,
    HEROES_TABLE,
    HEROES_TABLE_PRIMARY_REPLICA,
    HEROES_TABLE_REPLICAS_BY_SHARD,
    HEROES_TABLE_SERVERS,
    REPLICA_STATISTICS_METRICS,
    SERVER_STATISTICS_METRICS,
    SERVER_STATUS_METRICS,
    SERVER_TAGS,
    SERVERS,
    TABLE_STATISTICS_METRICS,
    TABLE_STATUS_METRICS,
    TABLE_STATUS_SHARDS_METRICS,
)


def assert_metrics(aggregator, disconnected_servers=None):
    # type: (AggregatorStub, Set[ServerName]) -> None
    if disconnected_servers is None:
        disconnected_servers = set()

    _assert_config_totals_metrics(aggregator, disconnected_servers=disconnected_servers)
    _assert_statistics_metrics(aggregator, disconnected_servers=disconnected_servers)
    _assert_table_status_metrics(aggregator)
    _assert_server_status_metrics(aggregator, disconnected_servers=disconnected_servers)
    _assert_current_issues_metrics(aggregator, disconnected_servers=disconnected_servers)

    # NOTE: system jobs metrics are not asserted here because they are only emitted when the cluster is
    # changing (eg. an index is being created, or data is being rebalanced across servers), which is hard to
    # test without introducing flakiness.


def _assert_config_totals_metrics(aggregator, disconnected_servers):
    # type: (AggregatorStub, Set[ServerName]) -> None
    aggregator.assert_metric('rethinkdb.server.total', count=1, value=len(SERVERS) - len(disconnected_servers))
    aggregator.assert_metric('rethinkdb.database.total', count=1, value=1)
    aggregator.assert_metric('rethinkdb.database.table.total', count=1, value=1, tags=['database:{}'.format(DATABASE)])
    aggregator.assert_metric(
        'rethinkdb.table.secondary_index.total', count=1, value=1, tags=['table:{}'.format(HEROES_TABLE)]
    )


def _assert_statistics_metrics(aggregator, disconnected_servers):
    # type: (AggregatorStub, Set[ServerName]) -> None
    for metric in CLUSTER_STATISTICS_METRICS:
        aggregator.assert_metric(metric, count=1, tags=[])

    for server in SERVERS:
        tags = ['server:{}'.format(server)] + SERVER_TAGS[server]
        for metric in SERVER_STATISTICS_METRICS:
            count = 0 if server in disconnected_servers else 1
            aggregator.assert_metric(metric, count=count, tags=tags)

    for metric in TABLE_STATISTICS_METRICS:
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_metric(metric, count=1, tags=tags)

    for server in HEROES_TABLE_SERVERS:
        tags = [
            'table:{}'.format(HEROES_TABLE),
            'database:{}'.format(DATABASE),
            'server:{}'.format(server),
        ] + SERVER_TAGS[server]

        for metric in REPLICA_STATISTICS_METRICS:
            if server in disconnected_servers:
                aggregator.assert_metric(metric, count=0, tags=tags)
                continue

            # Assumption: cluster is stable (not currently rebalancing), so only these two states can exist.
            state = 'waiting_for_primary' if HEROES_TABLE_PRIMARY_REPLICA in disconnected_servers else 'ready'
            state_tag = 'state:{}'.format(state)
            aggregator.assert_metric(metric, count=1, tags=tags + [state_tag])


def _assert_table_status_metrics(aggregator):
    # type: (AggregatorStub) -> None
    for metric in TABLE_STATUS_METRICS:
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=1, tags=tags)

    for shard in HEROES_TABLE_REPLICAS_BY_SHARD:
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'shard:{}'.format(shard)]

        for metric in TABLE_STATUS_SHARDS_METRICS:
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=1, tags=tags)


def _assert_server_status_metrics(aggregator, disconnected_servers):
    # type: (AggregatorStub, Set[ServerName]) -> None
    for metric in SERVER_STATUS_METRICS:
        for server in SERVERS:
            tags = ['server:{}'.format(server)]
            count = 0 if server in disconnected_servers else 1
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=count, tags=tags)


def _assert_current_issues_metrics(aggregator, disconnected_servers):
    # type: (AggregatorStub, Set[ServerName]) -> None
    for metric in CURRENT_ISSUES_METRICS:
        if metric in CURRENT_ISSUES_METRICS_SUBMITTED_ALWAYS:
            count = 1
        elif disconnected_servers and metric in CURRENT_ISSUES_METRICS_SUBMITTED_IF_DISCONNECTED_SERVERS:
            count = 1
        else:
            count = 0

        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=count, tags=[])
