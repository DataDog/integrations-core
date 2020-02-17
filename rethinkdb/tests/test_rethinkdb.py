# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import copy
from typing import Iterator, List, TypedDict

import pytest
import rethinkdb

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.rethinkdb import RethinkDBCheck
from datadog_checks.rethinkdb._types import Instance, Metric

from .common import (
    BACKFILL_JOBS_METRICS,
    CLUSTER_STATISTICS_METRICS,
    CONNECT_SERVER_NAME,
    DATABASE,
    HEROES_TABLE,
    HEROES_TABLE_REPLICAS_BY_SHARD,
    HEROES_TABLE_SERVER_INITIAL,
    HEROES_TABLE_SERVERS_REPLICATED,
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
from .cluster import setup_cluster_ensuring_all_default_metrics_are_emitted

Context = TypedDict('Context', {'backfilling_servers': List[str]})


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance):
    # type: (AggregatorStub, Instance) -> None
    check = RethinkDBCheck('rethinkdb', {}, [instance])

    with setup_cluster_ensuring_all_default_metrics_are_emitted():
        check.check(instance)

    context = {'backfilling_servers': []}  # type: Context

    _assert_statistics_metrics(aggregator)
    _assert_table_status_metrics(aggregator, context=context)

    assert context['backfilling_servers'], (
        'Expected backfilling to be ongoing for at least one replica. '
        'Aborting, as otherwise backfill metrics would not be covered.'
    )

    _assert_server_status_metrics(aggregator)
    _assert_system_jobs_metrics(aggregator, context=context)

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
    for replica_server in HEROES_TABLE_SERVERS_REPLICATED:
        for metric in REPLICA_STATISTICS_METRICS:
            tags = ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'server:{}'.format(replica_server)]
            tags.extend(SERVER_TAGS[replica_server])
            aggregator.assert_metric(metric, count=1, tags=tags)

    # Ensure non-replica servers haven't yielded replica statistics.
    for non_replica_server in SERVERS - HEROES_TABLE_SERVERS_REPLICATED:
        for metric in REPLICA_STATISTICS_METRICS:
            tags = [
                'table:{}'.format(HEROES_TABLE),
                'database:{}'.format(DATABASE),
                'server:{}'.format(non_replica_server),
            ]
            tags.extend(SERVER_TAGS[non_replica_server])
            aggregator.assert_metric(metric, count=0, tags=tags)


def _assert_table_status_metrics(aggregator, context):
    # type: (AggregatorStub, Context) -> None

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
                # Due to 'setup_cluster()', RethinkDB should currently be backfilling data from
                # the initial server to the new replicas.
                value = 1 if metric.endswith('.state.backfilling') else 0
                try:
                    aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, value=value, count=1, tags=tags)
                except AssertionError:  # pragma: no cover
                    # Depending on timing, the server may already be ready. Fine! Re-assert to limit flakiness.
                    value = 1 if metric.endswith('.state.ready') else 0
                    aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=1, tags=tags)
                else:
                    context['backfilling_servers'].append(server)


def _assert_server_status_metrics(aggregator):
    # type: (AggregatorStub) -> None
    for metric in SERVER_STATUS_METRICS:
        for server in SERVERS:
            tags = ['server:{}'.format(server)]
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=1, tags=tags)


def _assert_system_jobs_metrics(aggregator, context):
    # type: (AggregatorStub, Context) -> None

    # Query jobs.
    for metric in QUERY_JOBS_METRICS:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE)

    # Backfill jobs.
    for metric in BACKFILL_JOBS_METRICS:
        for server in context['backfilling_servers']:
            tags = [
                'database:{}'.format(DATABASE),
                'table:{}'.format(HEROES_TABLE),
                'destination_server:{}'.format(server),
                'source_server:{}'.format(HEROES_TABLE_SERVER_INITIAL),
                'server:{}'.format(server),
                'server:{}'.format(HEROES_TABLE_SERVER_INITIAL),
            ]
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=1, tags=tags)


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
