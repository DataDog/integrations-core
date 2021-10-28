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
