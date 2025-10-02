# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from unittest.mock import Mock, patch

import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.util import ManagedAuthConnectionMixin

from . import common

pytestmark = pytest.mark.unit


class MockAsyncJob(ManagedAuthConnectionMixin):
    """Mock async job class for testing the mixin."""

    def __init__(self, connection_args_provider, uses_managed_auth):
        self._connection_args_provider = connection_args_provider
        self._uses_managed_auth = uses_managed_auth
        self._db_created_at = 0
        self._db = None
        self._close_count = 0

    def _close_db_conn(self):
        if self._db:
            self._close_count += 1
            self._db = None


@patch('datadog_checks.mysql.util.connect_with_session_variables')
def test_mixin_no_managed_auth(mock_connect):
    """Test that mixin does not reconnect when managed auth is disabled."""
    mock_connect.return_value = Mock()
    provider = Mock(return_value={'user': 'test', 'passwd': 'pass'})
    job = MockAsyncJob(provider, uses_managed_auth=False)

    # Get connection
    conn1 = job._get_db_connection()
    assert conn1 is not None
    assert provider.call_count == 1

    # Should return same connection without reconnecting
    conn2 = job._get_db_connection()
    assert conn2 is conn1
    assert provider.call_count == 1
    assert job._close_count == 0


@patch('datadog_checks.mysql.util.connect_with_session_variables')
def test_mixin_managed_auth_initial_connection(mock_connect):
    """Test that mixin creates connection on first call with managed auth."""
    mock_connect.return_value = Mock()
    provider = Mock(return_value={'user': 'test', 'passwd': 'token123'})
    job = MockAsyncJob(provider, uses_managed_auth=True)

    conn = job._get_db_connection()

    assert conn is not None
    assert provider.call_count == 1
    assert job._db_created_at > 0


@patch('datadog_checks.mysql.util.connect_with_session_variables')
def test_mixin_managed_auth_cached_connection(mock_connect):
    """Test that mixin returns cached connection when TTL not expired."""
    mock_connect.return_value = Mock()
    provider = Mock(return_value={'user': 'test', 'passwd': 'token123'})
    job = MockAsyncJob(provider, uses_managed_auth=True)

    # Get connection
    conn1 = job._get_db_connection()
    created_at = job._db_created_at

    # Get connection again immediately (within TTL)
    conn2 = job._get_db_connection()

    assert conn2 is conn1
    assert provider.call_count == 1
    assert job._close_count == 0
    assert job._db_created_at == created_at


@patch('datadog_checks.mysql.util.ManagedAuthConnectionMixin.MANAGED_AUTH_RECONNECT_INTERVAL', 1)
@patch('datadog_checks.mysql.util.connect_with_session_variables')
def test_mixin_managed_auth_reconnect_after_ttl(mock_connect):
    """Test that mixin reconnects after TTL expires."""
    mock_connect.side_effect = [Mock(), Mock()]  # Two different connections
    provider = Mock(return_value={'user': 'test', 'passwd': 'new_token'})
    job = MockAsyncJob(provider, uses_managed_auth=True)

    # Get initial connection
    conn1 = job._get_db_connection()
    assert conn1 is not None
    assert provider.call_count == 1

    # Wait for TTL to expire
    time.sleep(1.1)

    # Get connection again - should reconnect
    conn2 = job._get_db_connection()
    assert conn2 is not None
    assert conn2 is not conn1
    assert provider.call_count == 2
    assert job._close_count == 1


def test_mixin_should_reconnect_no_connection():
    """Test that _should_reconnect_for_managed_auth returns False when no connection exists."""
    provider = Mock()
    job = MockAsyncJob(provider, uses_managed_auth=True)

    assert job._should_reconnect_for_managed_auth() is False


@patch('datadog_checks.mysql.util.connect_with_session_variables')
def test_mixin_should_reconnect_ttl_not_expired(mock_connect):
    """Test that _should_reconnect_for_managed_auth returns False when TTL not expired."""
    mock_connect.return_value = Mock()
    provider = Mock(return_value={'user': 'test', 'passwd': 'token'})
    job = MockAsyncJob(provider, uses_managed_auth=True)

    job._get_db_connection()

    assert job._should_reconnect_for_managed_auth() is False


@patch('datadog_checks.mysql.util.ManagedAuthConnectionMixin.MANAGED_AUTH_RECONNECT_INTERVAL', 0.1)
@patch('datadog_checks.mysql.util.connect_with_session_variables')
def test_mixin_should_reconnect_ttl_expired(mock_connect):
    """Test that _should_reconnect_for_managed_auth returns True when TTL expired."""
    mock_connect.return_value = Mock()
    provider = Mock(return_value={'user': 'test', 'passwd': 'token'})
    job = MockAsyncJob(provider, uses_managed_auth=True)

    job._get_db_connection()
    time.sleep(0.2)

    assert job._should_reconnect_for_managed_auth() is True


@patch('datadog_checks.mysql.mysql.aws.generate_rds_iam_token')
def test_get_connection_args_with_aws_managed_auth(mock_generate_token):
    """Test that _get_connection_args generates IAM token for AWS managed auth."""
    mock_generate_token.return_value = "iam_token_123"

    instance = {
        'host': 'mydb.us-east-1.rds.amazonaws.com',
        'port': 3306,
        'user': 'datadog',
        'aws': {
            'managed_authentication': {'enabled': True},
            'region': 'us-east-1',
            'instance_endpoint': 'mydb.us-east-1.rds.amazonaws.com',
        },
    }

    check = MySql(common.CHECK_NAME, {}, [instance])
    connection_args = check._get_connection_args()

    assert connection_args['user'] == 'datadog'
    assert connection_args['passwd'] == 'iam_token_123'
    mock_generate_token.assert_called_once_with(
        host='mydb.us-east-1.rds.amazonaws.com',
        port=3306,
        username='datadog',
        region='us-east-1',
        role_arn=None,
    )


@patch('datadog_checks.mysql.mysql.aws.generate_rds_iam_token')
def test_get_connection_args_with_aws_managed_auth_and_role_arn(mock_generate_token):
    """Test that _get_connection_args passes role_arn when provided."""
    mock_generate_token.return_value = "iam_token_456"

    instance = {
        'host': 'mydb.us-east-1.rds.amazonaws.com',
        'port': 3306,
        'user': 'datadog',
        'aws': {
            'managed_authentication': {
                'enabled': True,
                'role_arn': 'arn:aws:iam::123456789012:role/DatadogRole',
            },
            'region': 'us-east-1',
            'instance_endpoint': 'mydb.us-east-1.rds.amazonaws.com',
        },
    }

    check = MySql(common.CHECK_NAME, {}, [instance])
    connection_args = check._get_connection_args()

    assert connection_args['passwd'] == 'iam_token_456'
    mock_generate_token.assert_called_once_with(
        host='mydb.us-east-1.rds.amazonaws.com',
        port=3306,
        username='datadog',
        region='us-east-1',
        role_arn='arn:aws:iam::123456789012:role/DatadogRole',
    )


def test_get_connection_args_without_managed_auth():
    """Test that _get_connection_args uses regular password when managed auth disabled."""
    instance = {
        'host': 'localhost',
        'port': 3306,
        'user': 'datadog',
        'pass': 'my_password',
    }

    check = MySql(common.CHECK_NAME, {}, [instance])
    connection_args = check._get_connection_args()

    assert connection_args['user'] == 'datadog'
    assert connection_args['passwd'] == 'my_password'


def test_uses_aws_managed_auth_flag_true():
    """Test that _uses_aws_managed_auth flag is set correctly when enabled."""
    instance = {
        'host': 'mydb.us-east-1.rds.amazonaws.com',
        'user': 'datadog',
        'aws': {
            'managed_authentication': {'enabled': True},
            'region': 'us-east-1',
            'instance_endpoint': 'mydb.us-east-1.rds.amazonaws.com',
        },
    }

    check = MySql(common.CHECK_NAME, {}, [instance])

    assert check._uses_aws_managed_auth is True


def test_uses_aws_managed_auth_flag_false():
    """Test that _uses_aws_managed_auth flag is False when not using AWS managed auth."""
    instance = {
        'host': 'localhost',
        'user': 'datadog',
        'pass': 'my_password',
    }

    check = MySql(common.CHECK_NAME, {}, [instance])

    assert check._uses_aws_managed_auth is False


def test_uses_aws_managed_auth_flag_false_when_disabled():
    """Test that _uses_aws_managed_auth flag is False when explicitly disabled."""
    instance = {
        'host': 'mydb.us-east-1.rds.amazonaws.com',
        'user': 'datadog',
        'aws': {
            'managed_authentication': {'enabled': False},
            'region': 'us-east-1',
            'instance_endpoint': 'mydb.us-east-1.rds.amazonaws.com',
        },
    }

    check = MySql(common.CHECK_NAME, {}, [instance])

    assert check._uses_aws_managed_auth is False
