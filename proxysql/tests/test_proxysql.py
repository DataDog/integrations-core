import mock
import pymysql
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.errors import ConfigurationError
from datadog_checks.proxysql import ProxysqlCheck

from . import common


@pytest.mark.unit
def test_wrong_config():
    check = ProxysqlCheck('proxysql', {}, {})

    # Empty instance
    with pytest.raises(ConfigurationError, match='ProxySQL host, port, user and password are needed'):
        check.check({})

    # Only host
    with pytest.raises(ConfigurationError, match='ProxySQL host, port, user and password are needed'):
        check.check({'server': 'localhost'})

    # Missing password
    with pytest.raises(ConfigurationError, match='ProxySQL host, port, user and password are needed'):
        check.check({'server': 'localhost', 'port': 6032, 'user': 'admin'})


@pytest.mark.unit
def test_config_ok():
    check = ProxysqlCheck('proxysql', {}, {})

    connection_mock = mock.Mock()
    connection_mock.__enter__ = mock.Mock()
    connection_mock.__exit__ = mock.Mock()
    check._connect = mock.Mock(return_value=connection_mock)
    check._collect_metrics = mock.Mock()

    check.check({'server': 'localhost', 'port': 6032, 'user': 'admin', 'pass': 'admin'})

    check._connect.assert_called_once_with('localhost', 6032, 'admin', 'admin', [], 10, None)
    check._collect_metrics.assert_called_once_with(connection_mock.__enter__(), [], [])


@pytest.mark.unit
def test_fetch_stats_no_result():
    check = ProxysqlCheck('proxysql', {}, {})

    cursor_mock = mock.Mock()
    cursor_mock.execute = mock.Mock()
    cursor_mock.rowcount = 0
    connection_mock = mock.Mock()
    connection_mock.cursor = mock.Mock(return_value=cursor_mock)

    check.warning = mock.Mock()
    stats = check._fetch_stats(connection_mock, 'query', 'test_stats')

    cursor_mock.execute.assert_called_once_with('query')
    check.warning.assert_called_once_with("Failed to fetch records from %s.", 'test_stats')

    assert len(stats) == 0


@pytest.mark.unit
def test_fetch_stats_exception():
    check = ProxysqlCheck('proxysql', {}, {})

    cursor_mock = mock.Mock()
    cursor_mock.execute = mock.Mock(side_effect=pymysql.err.InternalError('Internal Error'))
    cursor_mock.rowcount = 0
    connection_mock = mock.Mock()
    connection_mock.cursor = mock.Mock(return_value=cursor_mock)

    check.warning = mock.Mock()
    stats = check._fetch_stats(connection_mock, 'query', 'test_stats')

    cursor_mock.execute.assert_called_once_with('query')
    check.warning.assert_called_once_with("ProxySQL %s unavailable at this time: %s", 'test_stats', 'Internal Error')

    assert len(stats) == 0


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_check(aggregator, dd_environment):
    c = ProxysqlCheck('proxysql', {}, {})

    # the check should send OK
    c.check(dd_environment)
    aggregator.assert_service_check('proxysql.can_connect', AgentCheck.OK)

    # the check should send CRITICAL
    instance = dd_environment.copy()
    instance['port'] = 1111
    with pytest.raises(pymysql.OperationalError, match="Can't connect to MySQL server"):
        c.check(instance)

    aggregator.assert_service_check('proxysql.can_connect', AgentCheck.CRITICAL)

    for metric in common.ALL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_not_optional_metrics(aggregator, dd_environment):
    c = ProxysqlCheck('proxysql', {}, {})

    instance = dd_environment.copy()
    instance['additional_metrics'] = []

    c.check(instance)

    for metric in common.GLOBAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_metrics_tags(aggregator, dd_environment):
    c = ProxysqlCheck('proxysql', {}, {})

    c.check(dd_environment)
    aggregator.assert_service_check('proxysql.can_connect', AgentCheck.OK)

    for metric in common.SIMPLE_TAG_METRICS:
        aggregator.assert_metric_has_tag(metric, 'application:test', count=1)

    for metric in common.COMMAND_TAGS_METRICS:
        aggregator.assert_metric_has_tag(metric, 'application:test')
        aggregator.assert_metric_has_tag_prefix(metric, 'proxysql_command')

    for metric in common.POOL_TAGS_METRICS:
        aggregator.assert_metric_has_tag(metric, 'application:test')
        aggregator.assert_metric_has_tag_prefix(metric, 'proxysql_db_node')

    for metric in common.USER_TAGS_METRICS:
        aggregator.assert_metric_has_tag(metric, 'application:test')
        aggregator.assert_metric_has_tag_prefix(metric, 'proxysql_mysql_user')

    for metric in common.QUERY_RULES_TAGS_METRICS:
        aggregator.assert_metric_has_tag(metric, 'application:test')
        aggregator.assert_metric_has_tag_prefix(metric, 'proxysql_query_rule_id')

    aggregator.assert_all_metrics_covered()
