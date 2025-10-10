# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import mock
import pytest
import redis
from redis.exceptions import ResponseError

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
