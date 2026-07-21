# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from unittest.mock import Mock, patch

import pymysql
import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.connections import (
    AWSTokenProvider,
    MySQLConnectionArgs,
    MySQLConnectionManager,
    TokenProvider,
)

from . import common

pytestmark = pytest.mark.unit


class FakeTokenProvider(TokenProvider):
    def __init__(self, ttl_seconds, **kwargs):
        super().__init__(**kwargs)
        self.calls = 0
        self._ttl = ttl_seconds

    def _fetch_token(self):
        self.calls += 1
        return "token{}".format(self.calls), time.time() + self._ttl


def _make_manager(connection_args=None):
    check = Mock()
    check.tag_manager.get_tags.return_value = []
    check._get_debug_tags.return_value = []
    check.reported_hostname = 'test-host'
    args = connection_args or MySQLConnectionArgs(host='localhost', port=3306, user='u', password='p')
    return check, MySQLConnectionManager(check, args)


# ---------------------------------------------------------------------------
# TokenProvider
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'ttl_seconds, expected_second_token, expected_calls',
    [
        pytest.param(1000, "token1", 1, id='cached_within_ttl'),
        pytest.param(0, "token2", 2, id='refreshed_after_expiry'),
    ],
)
def test_token_provider_caching(ttl_seconds, expected_second_token, expected_calls):
    provider = FakeTokenProvider(ttl_seconds=ttl_seconds, skew_seconds=0)

    assert provider.get_token() == "token1"
    assert provider.get_token() == expected_second_token
    assert provider.calls == expected_calls


@patch('datadog_checks.mysql.aws.generate_rds_iam_token')
def test_aws_token_provider_fetches_iam_token(mock_generate_token):
    mock_generate_token.return_value = "iam_token_123"
    provider = AWSTokenProvider(
        host='mydb.us-east-1.rds.amazonaws.com',
        port=3306,
        username='datadog',
        region='us-east-1',
        role_arn='arn:aws:iam::123456789012:role/DatadogRole',
    )

    assert provider.get_token() == "iam_token_123"
    mock_generate_token.assert_called_once_with(
        host='mydb.us-east-1.rds.amazonaws.com',
        port=3306,
        username='datadog',
        region='us-east-1',
        role_arn='arn:aws:iam::123456789012:role/DatadogRole',
    )


# ---------------------------------------------------------------------------
# MySQLConnectionArgs
# ---------------------------------------------------------------------------


def test_connection_args_regular_password():
    kwargs = MySQLConnectionArgs(host='h', port=3306, user='u', password='p').as_kwargs()

    assert kwargs['user'] == 'u'
    assert kwargs['password'] == 'p'
    assert kwargs['host'] == 'h'
    assert kwargs['port'] == 3306
    assert kwargs['autocommit'] is True


def test_connection_args_uses_token_provider_for_password():
    provider = Mock()
    provider.get_token.return_value = 'fresh_token'
    kwargs = MySQLConnectionArgs(host='h', user='u', password='static', token_provider=provider).as_kwargs()

    assert kwargs['password'] == 'fresh_token'
    provider.get_token.assert_called_once()


def test_connection_args_unix_socket_overrides_host():
    kwargs = MySQLConnectionArgs(host='h', unix_socket='/tmp/mysql.sock', user='u', password='p').as_kwargs()

    assert kwargs['unix_socket'] == '/tmp/mysql.sock'
    assert 'host' not in kwargs


def test_connection_args_defaults_file_short_circuits():
    kwargs = MySQLConnectionArgs(defaults_file='/etc/my.cnf', host='h', user='u', password='p').as_kwargs()

    assert kwargs['read_default_file'] == '/etc/my.cnf'
    assert 'user' not in kwargs
    assert 'password' not in kwargs
    assert 'host' not in kwargs


# ---------------------------------------------------------------------------
# MySQLConnectionManager
# ---------------------------------------------------------------------------


@patch('datadog_checks.mysql.connections.pymysql')
def test_manager_creates_connection_lazily(mock_pymysql):
    _, manager = _make_manager()

    with manager.get_connection('main') as conn:
        assert conn is mock_pymysql.connect.return_value

    assert mock_pymysql.connect.call_count == 1


@patch('datadog_checks.mysql.connections.pymysql')
def test_manager_reuses_live_connection(mock_pymysql):
    conn = mock_pymysql.connect.return_value
    conn.ping.return_value = None  # alive
    _, manager = _make_manager()

    with manager.get_connection('main') as first:
        pass
    with manager.get_connection('main') as second:
        pass

    assert first is second
    assert mock_pymysql.connect.call_count == 1
    conn.ping.assert_called_once_with(reconnect=False)


@patch('datadog_checks.mysql.connections.pymysql')
def test_manager_recreates_dead_connection(mock_pymysql):
    dead, alive = Mock(name='dead'), Mock(name='alive')
    dead.ping.side_effect = Exception("connection lost")
    mock_pymysql.connect.side_effect = [dead, alive]
    _, manager = _make_manager()

    with manager.get_connection('main') as first:
        assert first is dead
    with manager.get_connection('main') as second:
        assert second is alive

    assert mock_pymysql.connect.call_count == 2
    dead.close.assert_called_once()


@patch('datadog_checks.mysql.connections.pymysql')
def test_manager_keeps_separate_connection_per_key(mock_pymysql):
    mock_pymysql.connect.side_effect = [Mock(name='a'), Mock(name='b')]
    _, manager = _make_manager()

    with manager.get_connection('statement-metrics') as a, manager.get_connection('query-activity') as b:
        assert a is not b

    assert mock_pymysql.connect.call_count == 2


@patch('datadog_checks.mysql.connections.pymysql')
def test_manager_close_all_closes_every_connection(mock_pymysql):
    conn_a, conn_b = Mock(name='a'), Mock(name='b')
    mock_pymysql.connect.side_effect = [conn_a, conn_b]
    _, manager = _make_manager()

    with manager.get_connection('a'):
        pass
    with manager.get_connection('b'):
        pass

    manager.close_all()

    conn_a.close.assert_called_once()
    conn_b.close.assert_called_once()


@patch('datadog_checks.mysql.connections.pymysql')
def test_manager_closes_connection_when_session_setup_fails(mock_pymysql):
    conn = mock_pymysql.connect.return_value
    conn.cursor.return_value.execute.side_effect = Exception("permission denied")
    check, manager = _make_manager()

    with pytest.raises(Exception):
        with manager.get_connection('main'):
            pass

    conn.close.assert_called_once()
    check.count.assert_called_with(
        "dd.mysql.db.error",
        1,
        tags=["error:Exception"],
        hostname='test-host',
    )


@patch('datadog_checks.mysql.connections.pymysql')
def test_manager_emits_error_and_reraises_on_connect_failure(mock_pymysql):
    mock_pymysql.connect.side_effect = pymysql.err.OperationalError(2003, "Can't connect to MySQL server")
    check, manager = _make_manager()

    with pytest.raises(pymysql.err.OperationalError):
        with manager.get_connection('main'):
            pass

    check.count.assert_called_with(
        "dd.mysql.db.error",
        1,
        tags=["error:OperationalError"],
        hostname='test-host',
    )


@patch('datadog_checks.mysql.connections.pymysql')
def test_manager_refreshes_token_on_reconnect(mock_pymysql):
    # ttl=0 forces the provider to mint a new token on every fetch
    provider = FakeTokenProvider(ttl_seconds=0, skew_seconds=0)
    args = MySQLConnectionArgs(host='h', port=3306, user='u', password='static', token_provider=provider)
    check, _ = _make_manager()
    manager = MySQLConnectionManager(check, args)

    dead, alive = Mock(name='dead'), Mock(name='alive')
    dead.ping.side_effect = Exception("connection lost")
    mock_pymysql.connect.side_effect = [dead, alive]

    with manager.get_connection('main') as first:
        assert first is dead
    with manager.get_connection('main') as second:
        assert second is alive

    # The rebuilt connection authenticates with a freshly minted token, not the original one.
    assert provider.calls == 2
    assert mock_pymysql.connect.call_args_list[0].kwargs['password'] == 'token1'
    assert mock_pymysql.connect.call_args_list[1].kwargs['password'] == 'token2'


# ---------------------------------------------------------------------------
# Check wiring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'role_arn, token',
    [
        pytest.param(None, "iam_token_123", id='no_role_arn'),
        pytest.param('arn:aws:iam::123456789012:role/DatadogRole', "iam_token_456", id='with_role_arn'),
    ],
)
@patch('datadog_checks.mysql.aws.generate_rds_iam_token')
def test_build_connection_args_with_aws_managed_auth(mock_generate_token, role_arn, token):
    mock_generate_token.return_value = token
    managed_authentication = {'enabled': True}
    if role_arn is not None:
        managed_authentication['role_arn'] = role_arn
    instance = {
        'host': 'mydb.us-east-1.rds.amazonaws.com',
        'port': 3306,
        'user': 'datadog',
        'aws': {
            'managed_authentication': managed_authentication,
            'region': 'us-east-1',
            'instance_endpoint': 'mydb.us-east-1.rds.amazonaws.com',
        },
    }

    check = MySql(common.CHECK_NAME, {}, [instance])
    kwargs = check.build_connection_args().as_kwargs()

    assert kwargs['user'] == 'datadog'
    assert kwargs['password'] == token
    mock_generate_token.assert_called_once_with(
        host='mydb.us-east-1.rds.amazonaws.com',
        port=3306,
        username='datadog',
        region='us-east-1',
        role_arn=role_arn,
    )


def test_build_connection_args_without_managed_auth():
    instance = {
        'host': 'localhost',
        'port': 3306,
        'user': 'datadog',
        'pass': 'my_password',
    }

    check = MySql(common.CHECK_NAME, {}, [instance])
    kwargs = check.build_connection_args().as_kwargs()

    assert kwargs['user'] == 'datadog'
    assert kwargs['password'] == 'my_password'
    assert check._token_provider is None


@pytest.mark.parametrize(
    'instance, expected_enabled',
    [
        pytest.param(
            {
                'host': 'mydb.us-east-1.rds.amazonaws.com',
                'user': 'datadog',
                'aws': {
                    'managed_authentication': {'enabled': True},
                    'region': 'us-east-1',
                    'instance_endpoint': 'mydb.us-east-1.rds.amazonaws.com',
                },
            },
            True,
            id='enabled',
        ),
        pytest.param(
            {'host': 'localhost', 'user': 'datadog', 'pass': 'my_password'},
            False,
            id='no_aws_config',
        ),
        pytest.param(
            {
                'host': 'mydb.us-east-1.rds.amazonaws.com',
                'user': 'datadog',
                'aws': {
                    'managed_authentication': {'enabled': False},
                    'region': 'us-east-1',
                    'instance_endpoint': 'mydb.us-east-1.rds.amazonaws.com',
                },
            },
            False,
            id='explicitly_disabled',
        ),
    ],
)
def test_uses_aws_managed_auth_flag(instance, expected_enabled):
    check = MySql(common.CHECK_NAME, {}, [instance])

    assert check._uses_aws_managed_auth is expected_enabled
    if expected_enabled:
        assert isinstance(check._token_provider, AWSTokenProvider)
    else:
        assert check._token_provider is None


# ---------------------------------------------------------------------------
# _connect() behavior
# ---------------------------------------------------------------------------


def _basic_instance():
    return {
        'host': 'localhost',
        'username': 'dog',
        'password': 'dog',
        'port': 13306,
        'disable_generic_tags': True,
    }


@patch('datadog_checks.mysql.connections.pymysql')
def test_connect_emits_ok_and_keeps_connection_persistent(mock_pymysql, aggregator):
    conn = mock_pymysql.connect.return_value
    check = MySql(common.CHECK_NAME, {}, [_basic_instance()])
    check._resolved_hostname = 'stubbed.hostname'

    with check._connect() as first:
        assert first is conn
    with check._connect() as second:
        assert second is conn

    # The main connection is created once and reused across check runs (no fresh-per-run handshake),
    # and it is never closed on context-manager exit.
    assert mock_pymysql.connect.call_count == 1
    conn.close.assert_not_called()
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK)


@pytest.mark.parametrize(
    'error_code, message, expect_ssl_warning',
    [
        pytest.param(1045, "Access denied for user", True, id='access_denied_without_ssl'),
        pytest.param(2003, "Can't connect to MySQL server", False, id='connection_refused'),
    ],
)
@patch('datadog_checks.mysql.connections.pymysql')
def test_connect_critical_service_check(mock_pymysql, aggregator, error_code, message, expect_ssl_warning):
    mock_pymysql.connect.side_effect = pymysql.err.OperationalError(error_code, message)
    check = MySql(common.CHECK_NAME, {}, [_basic_instance()])
    check._resolved_hostname = 'stubbed.hostname'
    check.log = Mock()

    with pytest.raises(pymysql.err.OperationalError):
        with check._connect():
            pass

    aggregator.assert_service_check('mysql.can_connect', status=MySql.CRITICAL)
    warned = any('Access denied error (1045)' in str(call.args[0]) for call in check.log.warning.call_args_list)
    assert warned is expect_ssl_warning
