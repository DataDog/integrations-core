# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from tests.conftest import PROXYSQL_VERSION

from datadog_checks.base import AgentCheck
from datadog_checks.errors import ConfigurationError
from datadog_checks.proxysql import ProxysqlCheck

from .common import (
    ALL_METRICS,
    COMMANDS_COUNTERS_METRICS,
    CONNECTION_POOL_METRICS,
    GLOBAL_METRICS,
    MEMORY_METRICS,
    QUERY_RULES_TAGS_METRICS,
    USER_TAGS_METRICS,
)


def get_check(instance):
    """Simple helper method to get a check instance from a config instance."""
    return ProxysqlCheck('proxysql', {}, [instance])


@pytest.mark.unit
def test_wrong_config(dd_run_check, instance_basic):
    # Empty instance
    with pytest.raises(ConfigurationError, match='ProxySQL host, port, username and password are needed'):
        dd_run_check(get_check({}))

    # Only host
    with pytest.raises(ConfigurationError, match='ProxySQL host, port, username and password are needed'):
        dd_run_check(get_check({'host': 'localhost'}))

    # Missing password
    with pytest.raises(ConfigurationError, match='ProxySQL host, port, username and password are needed'):
        dd_run_check(get_check({'host': 'localhost', 'port': 6032, 'username': 'admin'}))

    # Wrong additional metrics group
    with pytest.raises(
        ConfigurationError,
        match="There is no additional metric group called 'foo' for the ProxySQL integration, it should be one of ",
    ):
        instance_basic['additional_metrics'].append('foo')
        dd_run_check(get_check(instance_basic))


@pytest.mark.unit
def test_config_ok(dd_run_check):
    check = get_check({'host': 'localhost', 'port': 6032, 'username': 'admin', 'password': 'admin'})
    connect_mock, query_executor_mock = mock.MagicMock(), mock.MagicMock()

    check.connect = connect_mock
    check._query_manager.executor = query_executor_mock

    dd_run_check(check)

    connect_mock.assert_called_once()
    assert query_executor_mock.call_count == 2


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_checks_ok(aggregator, instance_basic, dd_run_check):
    # Connection pool metrics submit the per-backend status service check
    instance_basic['additional_metrics'].append('connection_pool_metrics')
    check = get_check(instance_basic)
    dd_run_check(check)

    aggregator.assert_service_check(
        'proxysql.can_connect', AgentCheck.OK, tags=['server:localhost', 'port:6032', 'application:test']
    )
    aggregator.assert_service_check(
        'proxysql.backend.status',
        AgentCheck.OK,
        tags=['application:test', 'hostgroup:0', 'srv_host:db', 'srv_port:3306'],
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
        ([], GLOBAL_METRICS, [],),
        (['command_counters_metrics'], COMMANDS_COUNTERS_METRICS, ['sql_command']),
        (['connection_pool_metrics'], CONNECTION_POOL_METRICS, ['hostgroup', 'srv_host', 'srv_port']),
        (['users_metrics'], USER_TAGS_METRICS, ['username']),
        (['memory_metrics'], MEMORY_METRICS, []),
        (['query_rules_metrics'], QUERY_RULES_TAGS_METRICS, ['rule_id'],),
    ),
    ids=('global', 'command_counters', 'connection_pool', 'users', 'memory', 'query_rules'),
)
def test_metric(aggregator, instance_basic, dd_run_check, additional_metrics, expected_metrics, tag_prefixes):
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

    raw_version = PROXYSQL_VERSION
    major, minor = raw_version.split('.')[:2]
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': mock.ANY,
        'version.raw': mock.ANY,
    }
    datadog_agent.assert_metadata('', version_metadata)


def _assert_all_metrics(aggregator):
    for metric in ALL_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_all_metrics(aggregator, instance_all_metrics, dd_run_check):
    check = get_check(instance_all_metrics)
    dd_run_check(check)
    _assert_all_metrics(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance_all_metrics):
    aggregator = dd_agent_check(instance_all_metrics, rate=True)
    _assert_all_metrics(aggregator)
