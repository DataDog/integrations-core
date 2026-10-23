# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from collections.abc import Callable, Iterator

import mock
import pytest
import redis
from redis.exceptions import ResponseError

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.redisdb import Redis

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
        'client_name': 'datadog-agent',
    }
    redis_instance.update(connection_args)

    redis_check = check(redis_instance)
    with mock.patch('redis.Redis') as redis_conn:
        dd_run_check(redis_check)
        # RESP2 is pinned by the check rather than taken from the client default
        assert redis_conn.call_args.kwargs == connection_args | {'protocol': 2}


@pytest.fixture
def config_connection(redis_instance: dict) -> Iterator[mock.Mock]:
    redis_instance.pop('keys')
    with mock.patch('redis.Redis') as redis_client:
        conn = redis_client.return_value
        conn.info.return_value = {'role': 'master', 'connected_clients': 2}
        conn.slowlog_get.side_effect = [
            [{'start_time': timestamp, 'duration': 42, 'command': b'GET key'}] for timestamp in range(1, 4)
        ]
        yield conn


@pytest.mark.parametrize('slowlog_limit', [None, 256])
def test_disable_config_get(
    check: Callable[[dict], Redis],
    redis_instance: dict,
    config_connection: mock.Mock,
    aggregator: AggregatorStub,
    slowlog_limit: int | None,
):
    redis_instance['disable_config_get'] = True
    if slowlog_limit is not None:
        redis_instance['slowlog-max-len'] = slowlog_limit
    redis_check = check(redis_instance)

    for _ in range(2):
        redis_check.check(redis_instance)

    config_connection.config_get.assert_not_called()
    assert config_connection.slowlog_get.call_args_list == [mock.call(slowlog_limit or 128)] * 2
    aggregator.assert_metric('redis.net.maxclients', count=0)
    aggregator.assert_metric('redis.net.clients', value=2, count=2)
    aggregator.assert_metric('redis.slowlog.micros', value=42, count=2)


@pytest.mark.parametrize('rejected_parameter', ['maxclients', 'slowlog-max-len'])
def test_config_get_response_error(
    check: Callable[[dict], Redis],
    redis_instance: dict,
    config_connection: mock.Mock,
    aggregator: AggregatorStub,
    caplog: pytest.LogCaptureFixture,
    rejected_parameter: str,
):
    # Regression: https://datadoghq.atlassian.net/browse/AI-7311
    error = ResponseError('ERR CONFIG is restricted')
    responses = [error] if rejected_parameter == 'maxclients' else [{'maxclients': '1000'}, error]
    config_connection.config_get.side_effect = responses
    redis_instance['disable_connection_cache'] = True
    redis_check = check(redis_instance)

    with caplog.at_level(logging.WARNING):
        for _ in range(3):
            redis_check.check(redis_instance)

    expected_calls = [mock.call('maxclients')]
    if rejected_parameter == 'slowlog-max-len':
        expected_calls.append(mock.call('slowlog-max-len'))
    assert config_connection.config_get.call_args_list == expected_calls
    assert config_connection.slowlog_get.call_args_list == [mock.call(128)] * 3
    aggregator.assert_metric('redis.net.maxclients', count=int(rejected_parameter == 'slowlog-max-len'))
    aggregator.assert_metric('redis.net.clients', value=2, count=3)
    aggregator.assert_metric('redis.slowlog.micros', value=42, count=3)
    assert len(caplog.records) == 1
    assert 'disable_config_get' in caplog.messages[0]
    assert 'ERR CONFIG is restricted' in caplog.messages[0]


@pytest.mark.parametrize(
    'server_limit, configured_limit, expected_limit',
    [(64, None, 64), (256, None, 128), (64, 256, 256)],
)
def test_config_get_metrics(
    check: Callable[[dict], Redis],
    redis_instance: dict,
    config_connection: mock.Mock,
    aggregator: AggregatorStub,
    server_limit: int,
    configured_limit: int | None,
    expected_limit: int,
):
    if configured_limit is not None:
        redis_instance['slowlog-max-len'] = configured_limit
    responses = [{'maxclients': '1000'}]
    expected_calls = [mock.call('maxclients')]
    if configured_limit is None:
        responses.append({'slowlog-max-len': str(server_limit)})
        expected_calls.append(mock.call('slowlog-max-len'))
    config_connection.config_get.side_effect = responses * 2
    redis_check = check(redis_instance)

    for _ in range(2):
        redis_check.check(redis_instance)

    assert config_connection.config_get.call_args_list == expected_calls * 2
    assert config_connection.slowlog_get.call_args_list == [mock.call(expected_limit)] * 2
    aggregator.assert_metric('redis.net.maxclients', value=1000, count=2)
    aggregator.assert_metric('redis.slowlog.micros', value=42, count=2)


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


def test_empty_db_in_keyspace(check, aggregator, redis_instance):
    """
    Redis-compatible servers such as Dragonfly report empty databases in INFO keyspace (keys=0)
    """
    redis_check = check(redis_instance)
    conn = mock.MagicMock()
    conn.info.return_value = {'db0': {'keys': 0, 'expires': 0}, 'db1': {'keys': 4, 'expires': 1}}
    conn.config_get.return_value = {}

    with mock.patch.object(redis_check, '_get_conn', return_value=conn):
        redis_check._check_db()

    aggregator.assert_metric('redis.persist', value=0, tags=redis_check.tags + ['redis_db:db0'])
    aggregator.assert_metric('redis.persist.percent', count=0, tags=redis_check.tags + ['redis_db:db0'])
    aggregator.assert_metric('redis.expires.percent', count=0, tags=redis_check.tags + ['redis_db:db0'])
    aggregator.assert_metric('redis.persist.percent', value=75, tags=redis_check.tags + ['redis_db:db1'])
    aggregator.assert_metric('redis.expires.percent', value=25, tags=redis_check.tags + ['redis_db:db1'])
