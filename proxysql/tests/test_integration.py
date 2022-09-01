# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck

from .common import (
    BACKENDS_METRICS,
    COMMANDS_COUNTERS_METRICS,
    CONNECTION_POOL_METRICS,
    GLOBAL_METRICS,
    MEMORY_METRICS,
    QUERY_RULES_TAGS_METRICS,
    USER_TAGS_METRICS,
)
from .conftest import _assert_all_metrics, _assert_metadata, get_check


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_checks_ok(aggregator, instance_basic, dd_run_check):
    # Connection pool metrics submit the per-backend status service check
    instance_basic['additional_metrics'].append('connection_pool_metrics')
    check = get_check(instance_basic)
    dd_run_check(check)

    aggregator.assert_service_check(
        'proxysql.can_connect',
        AgentCheck.OK,
        tags=['proxysql_server:localhost', 'proxysql_port:6032', 'application:test'],
    )
    aggregator.assert_service_check(
        'proxysql.backend.status',
        AgentCheck.OK,
        tags=[
            'proxysql_server:localhost',
            'proxysql_port:6032',
            'application:test',
            'hostgroup:0',
            'srv_host:db',
            'srv_port:3306',
        ],
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_server_down(aggregator, instance_basic, dd_run_check):
    instance_basic['port'] = 111
    check = get_check(instance_basic)

    with pytest.raises(Exception, match="OperationalError.*Can't connect to MySQL server on"):
        dd_run_check(check)

    aggregator.assert_service_check('proxysql.can_connect', AgentCheck.CRITICAL)
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    ('additional_metrics', 'expected_metrics', 'tag_prefixes'),
    (
        ([], GLOBAL_METRICS, []),
        (['command_counters_metrics'], COMMANDS_COUNTERS_METRICS, ['sql_command']),
        (['connection_pool_metrics'], CONNECTION_POOL_METRICS, ['hostgroup', 'srv_host', 'srv_port']),
        (['users_metrics'], USER_TAGS_METRICS, ['username']),
        (['memory_metrics'], MEMORY_METRICS, []),
        (['backends_metrics'], BACKENDS_METRICS, ['hostgroup', 'status']),
        (['query_rules_metrics'], QUERY_RULES_TAGS_METRICS, ['rule_id']),
    ),
    ids=('global', 'command_counters', 'connection_pool', 'users', 'memory', 'backends', 'query_rules'),
)
def test_additional_metric(
    aggregator, instance_basic, dd_run_check, additional_metrics, expected_metrics, tag_prefixes
):
    instance_basic['additional_metrics'] = additional_metrics

    check = get_check(instance_basic)

    # Remove global metrics collection if needed:
    if additional_metrics:
        check._query_manager.queries.pop(0)

    dd_run_check(check)
    for metric in expected_metrics:
        aggregator.assert_metric(metric)
        for prefix in tag_prefixes:
            aggregator.assert_metric_has_tag_prefix(metric, prefix)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
def test_metadata(datadog_agent, dd_run_check, instance_basic):
    check = get_check(instance_basic)
    dd_run_check(check)
    _assert_metadata(datadog_agent)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_all_metrics(aggregator, instance_all_metrics, dd_run_check):
    check = get_check(instance_all_metrics)
    dd_run_check(check)
    _assert_all_metrics(aggregator)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_all_metrics_stats_user(aggregator, instance_stats_user, dd_run_check):
    check = get_check(instance_stats_user)
    dd_run_check(check)
    _assert_all_metrics(aggregator)
