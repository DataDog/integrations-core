# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import copy
from typing import Iterator

import pytest
import rethinkdb

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.rethinkdb import RethinkDBCheck
from datadog_checks.rethinkdb._types import Instance, Metric

from .common import (
    CLUSTER_STATISTICS_METRICS,
    CONNECT_SERVER_NAME,
    DATABASE,
    HEROES_TABLE,
    HEROES_TABLE_REPLICAS_BY_SHARD,
    HEROES_TABLE_SERVERS,
    QUERY_JOBS_METRICS,
    REPLICA_STATISTICS_METRICS,
    SERVER_STATISTICS_METRICS,
    SERVER_STATUS_METRICS,
    SERVER_TAGS,
    SERVERS,
    TABLE_STATISTICS_METRICS,
    TABLE_STATUS_METRICS,
    TABLE_STATUS_SHARDS_METRICS,
    TABLE_STATUS_SHARDS_REPLICA_STATE_METRICS,
)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check(instance)

    _assert_statistics_metrics(aggregator)
    _assert_table_status_metrics(aggregator)
    _assert_server_status_metrics(aggregator)
    _assert_system_jobs_metrics(aggregator)

    aggregator.assert_all_metrics_covered()

    service_check_tags = ['server:{}'.format(CONNECT_SERVER_NAME)]
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK, count=1, tags=service_check_tags)


def _assert_statistics_metrics(aggregator):
    # type: (AggregatorStub) -> None

    # Cluster.
    for metric in CLUSTER_STATISTICS_METRICS:
        aggregator.assert_metric(metric, count=1, tags=[])

    # Servers.
    for server in SERVERS:
        for metric in SERVER_STATISTICS_METRICS:
            tags = ['server:{}'.format(server)] + SERVER_TAGS[server]
            aggregator.assert_metric(metric, count=1, tags=tags)

    # Tables.
    for metric in TABLE_STATISTICS_METRICS:
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_metric(metric, count=1, tags=tags)

    # Replicas (table/server pairs).
    for replica_server in HEROES_TABLE_SERVERS:
        for metric in REPLICA_STATISTICS_METRICS:
            tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'server:{}'.format(replica_server)]
            tags.extend(SERVER_TAGS[replica_server])
            aggregator.assert_metric(metric, count=1, tags=tags)

    # Ensure non-replica servers haven't yielded replica statistics.
    for non_replica_server in SERVERS - HEROES_TABLE_SERVERS:
        for metric in REPLICA_STATISTICS_METRICS:
            tags = [
                'table:{}'.format(HEROES_TABLE),
                'database:{}'.format(DATABASE),
                'server:{}'.format(non_replica_server),
            ]
            tags.extend(SERVER_TAGS[non_replica_server])
            aggregator.assert_metric(metric, count=0, tags=tags)


def _assert_table_status_metrics(aggregator):
    # type: (AggregatorStub) -> None

    # Status of tables.
    for metric in TABLE_STATUS_METRICS:
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=1, tags=tags)

    # Status of shards.
    for shard, servers in HEROES_TABLE_REPLICAS_BY_SHARD.items():
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'shard:{}'.format(shard)]

        for metric in TABLE_STATUS_SHARDS_METRICS:
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=1, tags=tags)

        for server in servers:
            tags = [
                'table:{}'.format(HEROES_TABLE),
                'database:{}'.format(DATABASE),
                'shard:{}'.format(shard),
                'server:{}'.format(server),
            ]

            for metric in TABLE_STATUS_SHARDS_REPLICA_STATE_METRICS:
                # Assumption: all replicas in the cluster are ready, i.e. no rebalancing is in progress.
                value = 1 if metric.endswith('.state.ready') else 0
                aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, value=value, count=1, tags=tags)


def _assert_server_status_metrics(aggregator):
    # type: (AggregatorStub) -> None
    for metric in SERVER_STATUS_METRICS:
        for server in SERVERS:
            tags = ['server:{}'.format(server)]
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=1, tags=tags)


def _assert_system_jobs_metrics(aggregator):
    # type: (AggregatorStub) -> None
    for metric in QUERY_JOBS_METRICS:
        # NOTE: these metrics are emitted because the query issued to collect system jobs metrics is
        # included in system jobs themselves.
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE)

    # NOTE: other system jobs metrics are not covered here because they are only emitted when the cluster is
    # changing (eg. an index is being created, or data is being rebalanced across servers), which is hard to
    # test without introducing flakiness.


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_cannot_connect_unknown_host(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    instance = copy.deepcopy(instance)
    instance['host'] = 'doesnotexist'

    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check(instance)

    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.CRITICAL, count=1, tags=[])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connected_but_check_failed(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    def collect_and_fail(conn):
        # type: (rethinkdb.net.Connection) -> Iterator[Metric]
        yield {'type': 'gauge', 'name': 'rethinkdb.some.metric', 'value': 42, 'tags': []}
        raise RuntimeError('Oops!')

    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check._metric_collectors.append(collect_and_fail)
    check.check(instance)

    service_check_tags = ['server:{}'.format(CONNECT_SERVER_NAME)]
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.CRITICAL, count=1, tags=service_check_tags)
