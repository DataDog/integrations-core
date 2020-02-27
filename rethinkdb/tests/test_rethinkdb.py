# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import copy
from typing import Iterator, Set

import pytest
import rethinkdb

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.rethinkdb import RethinkDBCheck
from datadog_checks.rethinkdb._types import Instance, Metric

from .cluster import temporarily_disconnect_server
from .common import (
    CLUSTER_STATISTICS_METRICS,
    CONNECT_SERVER_NAME,
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
    TABLE_STATUS_SERVICE_CHECKS,
    TABLE_STATUS_SHARDS_METRICS,
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

    # NOTE: system jobs metrics are not asserted here because they are only emitted when the cluster is
    # changing (eg. an index is being created, or data is being rebalanced across servers), which is hard to
    # test without introducing flakiness.

    aggregator.assert_all_metrics_covered()

    service_check_tags = ['server:{}'.format(CONNECT_SERVER_NAME)]
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK, count=1, tags=service_check_tags)

    for service_check in TABLE_STATUS_SERVICE_CHECKS:
        tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_service_check(service_check, RethinkDBCheck.OK, count=1, tags=tags)


@pytest.mark.integration
@pytest.mark.parametrize('server_with_data', list(HEROES_TABLE_SERVERS))
@pytest.mark.usefixtures('dd_environment')
def test_check_with_disconnected_server(aggregator, instance, server_with_data):
    # type: (AggregatorStub, Instance, str) -> None
    """
    Verify that the check still runs to completion and sends appropriate service checks if one of the
    servers that holds data is disconnected.
    """
    check = RethinkDBCheck('rethinkdb', {}, [instance])

    with temporarily_disconnect_server(server_with_data):
        check.check(instance)

    disconnected_servers = {server_with_data}

    _assert_statistics_metrics(aggregator, disconnected_servers=disconnected_servers)
    _assert_table_status_metrics(aggregator)
    _assert_server_status_metrics(aggregator, disconnected_servers=disconnected_servers)

    aggregator.assert_all_metrics_covered()

    service_check_tags = ['server:{}'.format(CONNECT_SERVER_NAME)]
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.OK, count=1, tags=service_check_tags)

    table_status_tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]

    aggregator.assert_service_check(
        'rethinkdb.table_status.ready_for_outdated_reads', RethinkDBCheck.OK, count=1, tags=table_status_tags
    )
    aggregator.assert_service_check(
        'rethinkdb.table_status.ready_for_reads', RethinkDBCheck.WARNING, count=1, tags=table_status_tags
    )
    aggregator.assert_service_check(
        'rethinkdb.table_status.ready_for_writes', RethinkDBCheck.WARNING, count=1, tags=table_status_tags
    )
    aggregator.assert_service_check(
        'rethinkdb.table_status.all_replicas_ready', RethinkDBCheck.WARNING, count=1, tags=table_status_tags
    )


def _assert_statistics_metrics(aggregator, disconnected_servers=None):
    # type: (AggregatorStub, Set[str]) -> None
    if disconnected_servers is None:
        disconnected_servers = set()

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


def _assert_server_status_metrics(aggregator, disconnected_servers=None):
    # type: (AggregatorStub, Set[str]) -> None
    if disconnected_servers is None:
        disconnected_servers = set()

    for metric in SERVER_STATUS_METRICS:
        for server in SERVERS:
            tags = ['server:{}'.format(server)]
            count = 0 if server in disconnected_servers else 1
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=count, tags=tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_cannot_connect_unknown_host(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    instance = copy.deepcopy(instance)
    instance['host'] = 'doesnotexist'

    check = RethinkDBCheck('rethinkdb', {}, [instance])

    with pytest.raises(rethinkdb.errors.ReqlDriverError):
        check.check(instance)

    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.CRITICAL, count=1, tags=[])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connected_but_check_failed_unexpectedly(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    class Failure(Exception):
        pass

    def collect_and_fail(conn):
        # type: (rethinkdb.net.Connection) -> Iterator[Metric]
        yield {'type': 'gauge', 'name': 'rethinkdb.some.metric', 'value': 42, 'tags': []}
        raise Failure

    check = RethinkDBCheck('rethinkdb', {}, [instance])
    check.config.metric_streams = [collect_and_fail]

    with pytest.raises(Failure):
        check.check(instance)

    service_check_tags = ['server:{}'.format(CONNECT_SERVER_NAME)]
    aggregator.assert_service_check('rethinkdb.can_connect', RethinkDBCheck.CRITICAL, count=1, tags=service_check_tags)
