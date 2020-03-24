# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Set

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import ServiceCheckStatus
from datadog_checks.rethinkdb.types import Instance

from .common import (
    CLUSTER_STATISTICS_METRICS,
    CONFIG_METRICS,
    CURRENT_ISSUE_TYPES_SUBMITTED_IF_DISCONNECTED_SERVERS,
    CURRENT_ISSUES_METRICS,
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
    TAGS,
)
from .types import ServerName


def assert_service_checks(aggregator, instance, connect_status=AgentCheck.OK, disconnected_servers=None):
    # type: (AggregatorStub, Instance, ServiceCheckStatus, Set[ServerName]) -> None
    connect_tags = TAGS + ['host:{}'.format(instance['host']), 'port:{}'.format(instance['port'])]
    aggregator.assert_service_check('rethinkdb.can_connect', connect_status, count=1, tags=connect_tags)

    for service_check in TABLE_STATUS_SERVICE_CHECKS:
        count = 0 if connect_status == AgentCheck.CRITICAL else 1

        if disconnected_servers:
            status = AgentCheck.OK if service_check.endswith('ready_for_outdated_reads') else AgentCheck.WARNING
        else:
            status = AgentCheck.OK

        tags = TAGS + ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]

        aggregator.assert_service_check(service_check, status, count=count, tags=tags)


def assert_metrics(aggregator, disconnected_servers=None):
    # type: (AggregatorStub, Set[ServerName]) -> None
    if disconnected_servers is None:
        disconnected_servers = set()

    _assert_config_metrics(aggregator, disconnected_servers=disconnected_servers)
    _assert_statistics_metrics(aggregator, disconnected_servers=disconnected_servers)
    _assert_table_status_metrics(aggregator)
    _assert_server_status_metrics(aggregator, disconnected_servers=disconnected_servers)
    _assert_current_issues_metrics(aggregator, disconnected_servers=disconnected_servers)

    # NOTE: system jobs metrics are not asserted here because they are only emitted when the cluster is
    # changing (eg. an index is being created, or data is being rebalanced across servers), which is hard to
    # test without introducing flakiness.


def _assert_config_metrics(aggregator, disconnected_servers):
    # type: (AggregatorStub, Set[ServerName]) -> None
    for metric, typ, value, tags in CONFIG_METRICS:
        if callable(value):
            value = value(disconnected_servers)
        aggregator.assert_metric(metric, metric_type=typ, count=1, tags=TAGS + tags, value=value)


def _assert_statistics_metrics(aggregator, disconnected_servers):
    # type: (AggregatorStub, Set[ServerName]) -> None
    for metric, typ in CLUSTER_STATISTICS_METRICS:
        aggregator.assert_metric(metric, metric_type=typ, count=1, tags=TAGS)

    for server in SERVERS:
        tags = TAGS + ['server:{}'.format(server)] + SERVER_TAGS[server]
        for metric, typ in SERVER_STATISTICS_METRICS:
            count = 0 if server in disconnected_servers else 1
            aggregator.assert_metric(metric, metric_type=typ, count=count, tags=tags)

    for metric, typ in TABLE_STATISTICS_METRICS:
        tags = TAGS + ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_metric(metric, metric_type=typ, count=1, tags=tags)

    for server in HEROES_TABLE_SERVERS:
        tags = (
            TAGS
            + ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'server:{}'.format(server)]
            + SERVER_TAGS[server]
        )

        for metric, typ in REPLICA_STATISTICS_METRICS:
            if server in disconnected_servers:
                aggregator.assert_metric(metric, count=0, tags=tags)
                continue

            # Assumption: cluster is stable (not currently rebalancing), so only these two states can exist.
            state = 'waiting_for_primary' if HEROES_TABLE_PRIMARY_REPLICA in disconnected_servers else 'ready'
            state_tag = 'state:{}'.format(state)
            aggregator.assert_metric(metric, metric_type=typ, count=1, tags=tags + [state_tag])


def _assert_table_status_metrics(aggregator):
    # type: (AggregatorStub) -> None
    for metric, typ in TABLE_STATUS_METRICS:
        tags = TAGS + ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE)]
        aggregator.assert_metric(metric, metric_type=typ, count=1, tags=tags)

    for shard in HEROES_TABLE_REPLICAS_BY_SHARD:
        tags = TAGS + ['table:{}'.format(HEROES_TABLE), 'database:{}'.format(DATABASE), 'shard:{}'.format(shard)]

        for metric, typ in TABLE_STATUS_SHARDS_METRICS:
            aggregator.assert_metric(metric, metric_type=typ, count=1, tags=tags)


def _assert_server_status_metrics(aggregator, disconnected_servers):
    # type: (AggregatorStub, Set[ServerName]) -> None
    for metric, typ in SERVER_STATUS_METRICS:
        for server in SERVERS:
            tags = TAGS + ['server:{}'.format(server)]
            count = 0 if server in disconnected_servers else 1
            aggregator.assert_metric(metric, metric_type=typ, count=count, tags=tags)


def _assert_current_issues_metrics(aggregator, disconnected_servers):
    # type: (AggregatorStub, Set[ServerName]) -> None
    for metric, typ in CURRENT_ISSUES_METRICS:
        if disconnected_servers:
            for issue_type in CURRENT_ISSUE_TYPES_SUBMITTED_IF_DISCONNECTED_SERVERS:
                tags = TAGS + ['issue_type:{}'.format(issue_type)]
                aggregator.assert_metric(metric, metric_type=typ, count=1, tags=tags)
        else:
            aggregator.assert_metric(metric, metric_type=typ, count=0)
