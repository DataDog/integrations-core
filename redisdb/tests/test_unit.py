# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from unittest.mock import MagicMock, patch

import mock
import pytest
import redis
from redis.exceptions import ResponseError

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics

pytestmark = pytest.mark.unit


def test_init(check, redis_instance):
    check = check(redis_instance)
    assert check.connections == {}
    assert check.last_timestamp_seen == 0


def test__get_conn(check, redis_instance):
    check = check(redis_instance)
    instance = {}

    # create a connection
    check._get_conn(instance)
    key1, conn1 = next(iter(check.connections.items()))

    # assert connection is cached
    check._get_conn(instance)
    key2, conn2 = next(iter(check.connections.items()))
    assert key2 == key1
    assert conn2 == conn1

    # disable cache and assert connection has changed
    instance['disable_connection_cache'] = True
    check._get_conn(instance)
    key2, conn2 = next(iter(check.connections.items()))
    assert key2 == key1
    assert conn2 != conn1


@pytest.mark.parametrize(
    'info, expected_calls_value, expected_usec_per_call_value, expected_tags',
    [
        pytest.param(
            {'cmdstat_lpush': {'usec_per_call': 14.00, 'usec': 56, 'calls': 4}},
            4,
            14,
            ['command:lpush', 'foo:bar'],
            id='lpush',
        ),
        pytest.param(
            # this is from a real use case in Redis >5.0 where this line can be
            # seen (notice the double ':')
            # cmdstat_host::calls=2,usec=145,usec_per_call=72.50
            {'cmdstat_host': {'usec_per_call': 72.5, 'usec': 145, ':calls': 2}},
            2,
            72.5,
            ['foo:bar', 'command:host'],
            id="cmdstat_host with double ':'",
        ),
    ],
)
def test__check_command_stats_host(
    check, aggregator, redis_instance, info, expected_calls_value, expected_usec_per_call_value, expected_tags
):
    check = check(redis_instance)
    conn = mock.MagicMock()
    conn.info.return_value = info
    check._check_command_stats(conn, ['foo:bar'])

    aggregator.assert_metric('redis.command.calls', value=expected_calls_value, count=1, tags=expected_tags)
    aggregator.assert_metric(
        'redis.command.usec_per_call', value=expected_usec_per_call_value, count=1, tags=expected_tags
    )
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test__check_total_commands_processed_not_present(check, aggregator, redis_instance):
    """
    The check shouldn't send the `redis.net.commands` metric if `total_commands_processed` is not present in `c.info`
    """
    redis_check = check(redis_instance)
    conn = mock.MagicMock()
    conn.info.return_value = {}

    # Run the check
    redis_check._check_info_fields(conn.info(), [])

    # Assert that no metrics were sent
    aggregator.assert_metric('redis.net.commands', count=0)


def test__check_total_commands_processed_present(check, aggregator, redis_instance):
    """
    The check should send the `redis.net.commands` metric if `total_commands_processed` is present in `c.info`
    """
    redis_check = check(redis_instance)
    conn = mock.MagicMock()
    conn.info.return_value = {'total_commands_processed': 1000}

    # Run the check
    redis_check._check_info_fields(conn.info(), ['test_total_commands_processed'])

    # Assert that the `redis.net.commands` metric was sent
    aggregator.assert_metric('redis.net.commands', value=1000, tags=['test_total_commands_processed'])


def test_check_all_available_config_options(check, aggregator, redis_instance, dd_run_check):
    """
    The check should should create a connection with the supported config options
    """

    connection_args = {
        'db': 1,
        'username': 'user',
        'password': 'devops-best-friend',
        'socket_timeout': 5,
        'host': 'localhost',
        'port': '6379',
        'unix_socket_path': '/path',
        'ssl': True,
        'ssl_certfile': '/path',
        'ssl_keyfile': '/path',
        'ssl_ca_certs': '/path',
        'ssl_cert_reqs': 0,
        'ssl_check_hostname': True,
    }
    redis_instance.update(connection_args)

    redis_check = check(redis_instance)
    with mock.patch('redis.Redis') as redis_conn:
        dd_run_check(redis_check)
        assert redis_conn.call_args.kwargs == connection_args


def test_slowlog_quiet_failure(check, aggregator, redis_instance):
    """
    The check should not fail if the slowlog command fails with redis.ResponseError
    """
    redis_check = check(redis_instance)

    # Mock the connection object returned by _get_conn
    mock_conn = mock.MagicMock()
    mock_conn.slowlog_get.side_effect = ResponseError('ERR unknown command `SLOWLOG`')
    mock_conn.config_get.return_value = {'slowlog-max-len': '128'}

    with mock.patch.object(redis_check, '_get_conn', return_value=mock_conn):
        redis_check._check_slowlog()
        # Assert that no metrics were sent
        aggregator.assert_metric('redis.slowlog.micros', count=0)


def test_slowlog_loud_failure(check, redis_instance):
    """
    The check should fail if the slowlog command fails for any other reason
    """
    redis_check = check(redis_instance)

    # Mock the connection object returned by _get_conn
    mock_conn = mock.MagicMock()
    mock_conn.slowlog_get.side_effect = RuntimeError('Some other error')
    mock_conn.config_get.return_value = {'slowlog-max-len': '128'}

    with mock.patch.object(redis_check, '_get_conn', return_value=mock_conn):
        with pytest.raises(RuntimeError, match='Some other error'):
            redis_check._check_slowlog()


@pytest.mark.parametrize(
    'cluster_state, expected_state_value',
    [
        pytest.param('ok', 1, id='cluster_state_ok'),
        pytest.param('fail', 0, id='cluster_state_fail'),
    ],
)
def test__check_cluster_info(check, aggregator, redis_instance, cluster_state, expected_state_value):
    redis_check = check(redis_instance)
    conn = mock.MagicMock()
    conn.cluster.return_value = {
        'cluster_state': cluster_state,
        'cluster_slots_assigned': '16384',
        'cluster_slots_ok': '16384',
        'cluster_slots_pfail': '0',
        'cluster_slots_fail': '0',
        'cluster_known_nodes': '6',
        'cluster_size': '3',
        'cluster_current_epoch': '6',
    }
    redis_check._check_cluster_info(conn, ['foo:bar'])

    conn.cluster.assert_called_once_with('info')
    aggregator.assert_metric('redis.cluster.state', value=expected_state_value, count=1, tags=['foo:bar'])
    aggregator.assert_metric('redis.cluster.slots_assigned', value=16384, count=1, tags=['foo:bar'])
    aggregator.assert_metric('redis.cluster.slots_ok', value=16384, count=1, tags=['foo:bar'])
    aggregator.assert_metric('redis.cluster.slots_pfail', value=0, count=1, tags=['foo:bar'])
    aggregator.assert_metric('redis.cluster.slots_fail', value=0, count=1, tags=['foo:bar'])
    aggregator.assert_metric('redis.cluster.known_nodes', value=6, count=1, tags=['foo:bar'])
    aggregator.assert_metric('redis.cluster.size', value=3, count=1, tags=['foo:bar'])
    aggregator.assert_metric('redis.cluster.current_epoch', value=6, count=1, tags=['foo:bar'])
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test__check_cluster_info_disabled(check, aggregator, redis_instance):
    """_check_cluster_info should swallow ResponseError (e.g. cluster support disabled)."""
    redis_check = check(redis_instance)
    conn = mock.MagicMock()
    conn.cluster.side_effect = redis.ResponseError('ERR This instance has cluster support disabled')
    redis_check._check_cluster_info(conn, ['foo:bar'])
    conn.cluster.assert_called_once_with('info')
    aggregator.assert_metric('redis.cluster.state', count=0)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test__check_cluster_info_invalid_value(check, aggregator, redis_instance):
    redis_check = check(redis_instance)
    conn = mock.MagicMock()
    conn.cluster.return_value = {
        'cluster_state': 'ok',
        'cluster_slots_assigned': 'not_a_number',
        'cluster_slots_ok': '16384',
        'cluster_slots_pfail': '0',
        'cluster_slots_fail': '0',
        'cluster_known_nodes': '6',
        'cluster_size': '3',
        'cluster_current_epoch': '6',
    }
    redis_check._check_cluster_info(conn, ['foo:bar'])
    conn.cluster.assert_called_once_with('info')
    aggregator.assert_metric('redis.cluster.slots_assigned', count=0)
    aggregator.assert_metric('redis.cluster.slots_ok', value=16384, count=1, tags=['foo:bar'])
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_info_command_fallback(check, redis_instance, caplog):
    """
    The check should default to `INFO all` and fall back to `INFO`
    """
    redis_check = check(redis_instance)

    def mock_info(*args, **kwargs):
        if kwargs.get('section') == 'all':
            raise redis.ResponseError()
        else:
            return {}

    # Mock the connection object returned by _get_conn
    mock_conn = mock.MagicMock()
    mock_conn.info = mock.MagicMock(side_effect=mock_info)

    with mock.patch.object(redis_check, '_get_conn', return_value=mock_conn):
        with caplog.at_level(logging.DEBUG):
            redis_check._check_db()
    mock_conn.info.assert_has_calls((mock.call(section='all'), mock.call(), mock.call('keyspace')))
    assert any(msg.startswith('`INFO all` command failed, falling back to `INFO`:') for msg in caplog.messages)


class TestGCPIAMInit:
    def test_gcp_iam_provider_created_when_enabled(self, check):
        instance = {
            'host': 'memorystore.googleapis.com',
            'port': 6380,
            'gcp': {'managed_authentication': {'enabled': True}},
        }
        with patch('datadog_checks.redisdb.redisdb.GCPIAMTokenProvider') as mock_provider_cls:
            redis_check = check(instance)
            mock_provider_cls.assert_called_once_with(None)
            assert redis_check._gcp_token_provider is mock_provider_cls.return_value

    def test_gcp_iam_provider_uses_service_account_when_set(self, check):
        instance = {
            'host': 'memorystore.googleapis.com',
            'port': 6380,
            'gcp': {
                'managed_authentication': {
                    'enabled': True,
                    'service_account': 'datadog@my-project.iam.gserviceaccount.com',
                }
            },
        }
        with patch('datadog_checks.redisdb.redisdb.GCPIAMTokenProvider') as mock_provider_cls:
            redis_check = check(instance)
            mock_provider_cls.assert_called_once_with('datadog@my-project.iam.gserviceaccount.com')

    def test_gcp_iam_provider_is_none_when_disabled(self, check, redis_instance):
        redis_check = check(redis_instance)
        assert redis_check._gcp_token_provider is None

    def test_raises_config_error_when_password_and_iam_both_set(self, check):
        instance = {
            'host': 'memorystore.googleapis.com',
            'port': 6380,
            'password': 'secret',
            'gcp': {'managed_authentication': {'enabled': True}},
        }
        with patch('datadog_checks.redisdb.redisdb.GCPIAMTokenProvider'):
            with pytest.raises(ConfigurationError, match="password"):
                check(instance)

    def test_raises_config_error_when_username_and_iam_both_set(self, check):
        instance = {
            'host': 'memorystore.googleapis.com',
            'port': 6380,
            'username': 'someuser',
            'gcp': {'managed_authentication': {'enabled': True}},
        }
        with patch('datadog_checks.redisdb.redisdb.GCPIAMTokenProvider'):
            with pytest.raises(ConfigurationError, match="username"):
                check(instance)

    def test_ssl_warning_when_iam_enabled_without_ssl(self, check, caplog):
        import logging
        instance = {
            'host': 'memorystore.googleapis.com',
            'port': 6380,
            'gcp': {'managed_authentication': {'enabled': True}},
        }
        with patch('datadog_checks.redisdb.redisdb.GCPIAMTokenProvider'):
            with caplog.at_level(logging.WARNING):
                check(instance)
        assert any("plaintext" in msg for msg in caplog.messages)

    def test_no_ssl_warning_when_ssl_is_set(self, check, caplog):
        import logging
        instance = {
            'host': 'memorystore.googleapis.com',
            'port': 6380,
            'ssl': True,
            'gcp': {'managed_authentication': {'enabled': True}},
        }
        with patch('datadog_checks.redisdb.redisdb.GCPIAMTokenProvider'):
            with caplog.at_level(logging.WARNING):
                check(instance)
        assert not any("plaintext" in msg for msg in caplog.messages)


class TestGCPIAMGetConn:
    def _make_iam_check(self, check):
        instance = {
            'host': 'memorystore.googleapis.com',
            'port': 6380,
            'gcp': {'managed_authentication': {'enabled': True}},
        }
        mock_provider = MagicMock()
        mock_provider.username = "default"
        mock_provider.get_token.return_value = "iam-token-abc"
        mock_provider.is_token_expired.return_value = False
        with patch('datadog_checks.redisdb.redisdb.GCPIAMTokenProvider', return_value=mock_provider):
            redis_check = check(instance)
        redis_check._gcp_token_provider = mock_provider
        return redis_check, mock_provider

    def test_get_conn_injects_iam_credentials(self, check):
        redis_check, mock_provider = self._make_iam_check(check)
        with patch('redis.Redis') as mock_redis_cls:
            redis_check._get_conn(redis_check.instance)
            call_kwargs = mock_redis_cls.call_args.kwargs
            assert call_kwargs['username'] == 'default'
            assert call_kwargs['password'] == 'iam-token-abc'

    def test_get_conn_evicts_all_connections_when_token_expired(self, check):
        redis_check, mock_provider = self._make_iam_check(check)

        mock_conn_a = MagicMock()
        mock_conn_b = MagicMock()
        redis_check.connections[('memorystore.googleapis.com', 6380, None)] = mock_conn_a
        redis_check.connections[('memorystore.googleapis.com', 6380, 1)] = mock_conn_b

        mock_provider.is_token_expired.return_value = True

        with patch('redis.Redis'):
            redis_check._get_conn(redis_check.instance)

        mock_conn_a.connection_pool.disconnect.assert_called_once()
        mock_conn_b.connection_pool.disconnect.assert_called_once()
        assert len(redis_check.connections) == 1

    def test_get_conn_does_not_evict_when_token_not_expired(self, check):
        redis_check, mock_provider = self._make_iam_check(check)

        mock_conn = MagicMock()
        key = ('memorystore.googleapis.com', 6380, None)
        redis_check.connections[key] = mock_conn
        mock_provider.is_token_expired.return_value = False

        with patch('redis.Redis'):
            redis_check._get_conn(redis_check.instance)

        mock_conn.connection_pool.disconnect.assert_not_called()


class TestGCPIAMCheckDbRetry:
    def _make_iam_check(self, check):
        instance = {
            'host': 'memorystore.googleapis.com',
            'port': 6380,
            'gcp': {'managed_authentication': {'enabled': True}},
        }
        mock_provider = MagicMock()
        mock_provider.username = "default"
        mock_provider.get_token.return_value = "iam-token-abc"
        mock_provider.is_token_expired.return_value = False
        with patch('datadog_checks.redisdb.redisdb.GCPIAMTokenProvider', return_value=mock_provider):
            redis_check = check(instance)
        redis_check._gcp_token_provider = mock_provider
        return redis_check, mock_provider

    def test_check_db_retries_on_auth_error_with_iam(self, check):
        redis_check, mock_provider = self._make_iam_check(check)
        call_count = {'n': 0}

        def run_side_effect():
            call_count['n'] += 1
            if call_count['n'] == 1:
                raise redis.AuthenticationError("token expired")

        with patch.object(redis_check, '_run_check_db', side_effect=run_side_effect):
            with patch.object(redis_check, '_force_iam_reconnect') as mock_reconnect:
                redis_check._check_db()
                assert call_count['n'] == 2
                mock_reconnect.assert_called_once()

    def test_check_db_does_not_retry_without_iam(self, check, redis_instance):
        redis_check = check(redis_instance)
        with patch.object(redis_check, '_run_check_db', side_effect=redis.AuthenticationError("bad pass")):
            with pytest.raises(redis.AuthenticationError):
                redis_check._check_db()

    def test_check_db_propagates_second_auth_error(self, check):
        redis_check, mock_provider = self._make_iam_check(check)
        with patch.object(redis_check, '_run_check_db', side_effect=redis.AuthenticationError("still bad")):
            with patch.object(redis_check, '_force_iam_reconnect'):
                with pytest.raises(redis.AuthenticationError):
                    redis_check._check_db()

    def test_force_iam_reconnect_disconnects_and_invalidates(self, check):
        redis_check, mock_provider = self._make_iam_check(check)

        mock_conn = MagicMock()
        key = redis_check._generate_instance_key(redis_check.instance)
        redis_check.connections[key] = mock_conn

        redis_check._force_iam_reconnect()

        mock_conn.connection_pool.disconnect.assert_called_once()
        assert key not in redis_check.connections
        mock_provider.invalidate.assert_called_once()
