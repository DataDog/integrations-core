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
    HEROES_TABLE_REPLICAS,
    REPLICA_STATISTICS_METRICS,
    SERVER_STATISTICS_METRICS,
    SERVER_TAGS,
    SERVERS,
    TABLE_STATISTICS_METRICS,
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

    for metric in REPLICA_STATISTICS_METRICS:
        for server in HEROES_TABLE_REPLICAS:
            tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'server:{}'.format(server)]
            tags.extend(SERVER_TAGS[server])
            aggregator.assert_metric(metric, count=1, tags=tags)

        for server in SERVERS:
            if server not in HEROES_TABLE_REPLICAS:
                tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'server:{}'.format(server)]
                tags.extend(SERVER_TAGS[server])
                # Make sure servers that aren't replicas for the table don't yield metrics.
                aggregator.assert_metric(metric, count=0, tags=tags)

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
