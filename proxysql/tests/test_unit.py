# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base.errors import ConfigurationError

from .conftest import get_check


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
