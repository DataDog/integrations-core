# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base.errors import ConfigurationError

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
