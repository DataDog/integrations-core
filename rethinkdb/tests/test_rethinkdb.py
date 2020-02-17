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
    HEROES_TABLE_NUM_SHARDS,
    HEROES_TABLE_REPLICAS,
    HEROES_TABLE_SHARD_REPLICAS,
    REPLICA_STATISTICS_METRICS,
    SERVER_STATISTICS_METRICS,
    SERVER_TAGS,
    SERVERS,
    TABLE_STATISTICS_METRICS,
    TABLE_STATUS_METRICS,
    TABLE_STATUS_REPLICA_COUNT_METRICS,
    TABLE_STATUS_REPLICA_STATE_METRICS,
)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.check(instance)

    for metric in CLUSTER_STATISTICS_METRICS:
        aggregator.assert_metric(metric, count=1, tags=[])

    for metric in SERVER_STATISTICS_METRICS:
        for server in SERVERS:
            tags = ['server:{}'.format(server)] + SERVER_TAGS[server]
            aggregator.assert_metric(metric, count=1, tags=tags)

    for metric in TABLE_STATISTICS_METRICS:
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_metric(metric, count=1, tags=tags)

    assert len(HEROES_TABLE_REPLICAS) > 0
    NON_REPLICA_SERVERS = SERVERS - HEROES_TABLE_REPLICAS
    assert len(NON_REPLICA_SERVERS) > 0

    for metric in REPLICA_STATISTICS_METRICS:
        for server in HEROES_TABLE_REPLICAS:
            tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'server:{}'.format(server)]
            tags.extend(SERVER_TAGS[server])
            aggregator.assert_metric(metric, count=1, tags=tags)

        for server in NON_REPLICA_SERVERS:
            tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'server:{}'.format(server)]
            tags.extend(SERVER_TAGS[server])
            aggregator.assert_metric(metric, count=0, tags=tags)

    for metric in TABLE_STATUS_METRICS:
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=1, tags=tags)

    for shard in range(HEROES_TABLE_NUM_SHARDS):
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'shard:{}'.format(shard)]
        for metric in TABLE_STATUS_REPLICA_COUNT_METRICS:
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=1, tags=tags)

        for server in HEROES_TABLE_SHARD_REPLICAS[shard]:
            tags = [
                'table:{}'.format(HEROES_TABLE),
                'database:{}'.format(DATABASE),
                'shard:{}'.format(shard),
                'server:{}'.format(server),
            ]
            for metric in TABLE_STATUS_REPLICA_STATE_METRICS:
                value = 1 if metric.endswith('.ready') else 0  # All servers in our test cluster are available.
                aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, value=value, count=1, tags=tags)

    aggregator.assert_all_metrics_covered()

    service_check_tags = ['server:{}'.format(CONNECT_SERVER_NAME)]
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK, count=1, tags=service_check_tags)


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
