# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.proxysql import ProxysqlCheck

from .common import create_query_manager, mock_executor
from .conftest import get_check


@pytest.mark.unit
def test_empty_instance(dd_run_check):
    with pytest.raises(ConfigurationError, match='ProxySQL host, port, username and password are needed'):
        dd_run_check(get_check({}))


@pytest.mark.unit
def test_only_host(dd_run_check):
    with pytest.raises(ConfigurationError, match='ProxySQL host, port, username and password are needed'):
        dd_run_check(get_check({'host': 'localhost'}))


@pytest.mark.unit
def test_missing_password(dd_run_check):
    with pytest.raises(ConfigurationError, match='ProxySQL host, port, username and password are needed'):
        dd_run_check(get_check({'host': 'localhost', 'port': 6032, 'username': 'admin'}))


@pytest.mark.unit
def test_wrong_additional_metrics_group(dd_run_check, instance_basic):
    with pytest.raises(
        ConfigurationError,
        match="There is no additional metric group called 'foo' for the ProxySQL integration, it should be one of ",
    ):
        instance_basic['additional_metrics'].append('foo')
        dd_run_check(get_check(instance_basic))


@pytest.mark.parametrize(
    'executor_value, expected_status',
    [
        pytest.param('ONLINE', AgentCheck.OK, id='ONLINE'),
        pytest.param('SHUNNED', AgentCheck.CRITICAL, id='SHUNNED'),
        pytest.param('OFFLINE_SOFT', AgentCheck.WARNING, id='OFFLINE_SOFT'),
        pytest.param('OFFLINE_HARD', AgentCheck.CRITICAL, id='OFFLINE_HARD'),
        pytest.param('SHUNNED_REPLICATION_LAG', AgentCheck.CRITICAL, id='SHUNNED_REPLICATION_LAG'),
    ],
)
@pytest.mark.unit
def test_service_checks_mapping(aggregator, instance_basic, dd_run_check, executor_value, expected_status):
    check = get_check(instance_basic)
    con = mock.MagicMock()
    cursor = mock.MagicMock()
    con.cursor.return_value = cursor
    check.connect = con

    check._query_manager = create_query_manager(
        {
            'name': 'test query',
            'query': 'foo',
            'columns': [
                {
                    'name': 'proxysql.backend.status',
                    'type': 'service_check',
                    'status_map': {
                        'ONLINE': 'OK',
                        'SHUNNED': 'CRITICAL',
                        'OFFLINE_SOFT': 'WARNING',
                        'OFFLINE_HARD': 'CRITICAL',
                        'SHUNNED_REPLICATION_LAG': 'CRITICAL',
                    },
                },
            ],
        },
        executor=mock_executor([[executor_value]]),
    )
    check._query_manager.compile_queries()

    dd_run_check(check)
    aggregator.assert_service_check("proxysql.backend.status", expected_status)


@pytest.mark.unit
def test_config_ok(dd_run_check, instance_basic):
    check = get_check(instance_basic)
    connect_mock, query_executor_mock = mock.MagicMock(), mock.MagicMock()

    check.connect = connect_mock
    check._query_manager.executor = query_executor_mock

    dd_run_check(check)

    connect_mock.assert_called_once()
    assert query_executor_mock.call_count == 2


@pytest.mark.unit
def test_tls_config_ok(dd_run_check, instance_basic_tls):
    with mock.patch('datadog_checks.base.utils.tls.ssl') as ssl:
        with mock.patch('datadog_checks.proxysql.proxysql.pymysql') as pymysql:
            check = get_check(instance_basic_tls)

            # mock TLS context
            tls_context = mock.MagicMock()
            ssl.SSLContext.return_value = tls_context

            # mock query executor
            query_executor_mock = mock.MagicMock()
            check._query_manager.executor = query_executor_mock

            # mock behavior of db
            mock_db = mock.MagicMock()
            mock_db.close.return_value = True
            pymysql.connect.return_value = mock_db

            dd_run_check(check)

            assert check.tls_verify is True
            assert tls_context.check_hostname is True
            assert check._connection is not None


@pytest.mark.parametrize(
    'extra_config, expected_http_kwargs',
    [
        pytest.param(
            {'validate_hostname': False}, {'tls_validate_hostname': False}, id='legacy validate_hostname param'
        ),
    ],
)
def test_tls_config_legacy(extra_config, expected_http_kwargs, instance_all_metrics):
    instance = instance_all_metrics
    instance.update(extra_config)
    c = ProxysqlCheck('proxysql', {}, [instance])
    c.get_tls_context()  # need to call this for config values to be saved by _tls_context_wrapper
    actual_options = {k: v for k, v in c._tls_context_wrapper.config.items() if k in expected_http_kwargs}
    assert expected_http_kwargs == actual_options


@pytest.mark.unit
def test_missing_port_defaults_to_zero_and_fails_validation():
    # Kills the core/NumberReplacer mutants at proxysql.py:48 (port default 0 -> 1/-1); 0 is falsy so
    # validation must still fail when host, username and password are present but port is omitted.
    with pytest.raises(ConfigurationError, match='ProxySQL host, port, username and password are needed'):
        ProxysqlCheck('proxysql', {}, [{'host': 'localhost', 'username': 'admin', 'password': 'pass'}])


@pytest.mark.unit
def test_tls_verify_defaults_to_false(instance_basic):
    # Kills the core/ReplaceFalseWithTrue mutant at proxysql.py:55 (tls_verify default False -> True).
    check = get_check(instance_basic)
    assert check.tls_verify is False


@pytest.mark.unit
def test_connect_timeout_defaults_to_10(instance_basic):
    # Kills the core/NumberReplacer mutants at proxysql.py:57 (connect_timeout default 10 -> 9/11).
    check = get_check(instance_basic)
    assert check.connect_timeout == 10


@pytest.mark.unit
def test_execute_query_raw_returns_empty_list_when_rowcount_is_zero(instance_basic):
    # Kills the core/ReplaceComparisonOperator and NumberReplacer mutants at proxysql.py:92
    # (`cursor.rowcount < 1`); with no rows fetched the method must return an empty list.
    check = get_check(instance_basic)
    cursor = mock.MagicMock()
    cursor.rowcount = 0
    check._connection = mock.MagicMock()
    check._connection.cursor.return_value = cursor

    assert check.execute_query_raw('select 1') == []


@pytest.mark.unit
def test_execute_query_raw_returns_rows_when_rowcount_is_one(instance_basic):
    # Kills the core/ReplaceComparisonOperator and NumberReplacer mutants at proxysql.py:92
    # (`cursor.rowcount < 1`); exactly one row must still be fetched, not treated as empty.
    check = get_check(instance_basic)
    cursor = mock.MagicMock()
    cursor.rowcount = 1
    cursor.fetchall.return_value = [('row',)]
    check._connection = mock.MagicMock()
    check._connection.cursor.return_value = cursor

    assert check.execute_query_raw('select 1') == [('row',)]


@pytest.mark.unit
def test_execute_query_raw_returns_rows_when_rowcount_is_two(instance_basic):
    # Kills the core/ReplaceComparisonOperator_Lt_NotEq mutant at proxysql.py:92
    # (`cursor.rowcount < 1` -> `!= 1`); several rows must be returned as-is.
    check = get_check(instance_basic)
    cursor = mock.MagicMock()
    cursor.rowcount = 2
    cursor.fetchall.return_value = [('row1',), ('row2',)]
    check._connection = mock.MagicMock()
    check._connection.cursor.return_value = cursor

    assert check.execute_query_raw('select 1') == [('row1',), ('row2',)]


@pytest.mark.unit
def test_connect_failure_marks_service_check_critical(aggregator, instance_basic):
    # Kills the core/ExceptionReplacer mutant at proxysql.py:121 (except Exception ->
    # except CosmicRayTestingException); a generic connection error must still be caught.
    check = get_check(instance_basic)
    with mock.patch('datadog_checks.proxysql.proxysql.pymysql') as pymysql_mock:
        pymysql_mock.connect.side_effect = Exception('boom')
        with pytest.raises(Exception, match='boom'):
            with check.connect():
                pass

    aggregator.assert_service_check('proxysql.can_connect', AgentCheck.CRITICAL)


@pytest.mark.unit
def test_connect_closes_db_connection_on_success(instance_basic):
    # Kills the core/AddNot mutant at proxysql.py:128 (`if db` -> `if not db`); a
    # successfully opened connection must be closed on exit.
    check = get_check(instance_basic)
    mock_db = mock.MagicMock()
    with mock.patch('datadog_checks.proxysql.proxysql.pymysql') as pymysql_mock:
        pymysql_mock.connect.return_value = mock_db
        with check.connect():
            pass

    mock_db.close.assert_called_once()
