# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from six import iteritems

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
    key1, conn1 = next(iteritems(check.connections))

    # assert connection is cached
    check._get_conn(instance)
    key2, conn2 = next(iteritems(check.connections))
    assert key2 == key1
    assert conn2 == conn1

    # disable cache and assert connection has changed
    instance['disable_connection_cache'] = True
    check._get_conn(instance)
    key2, conn2 = next(iteritems(check.connections))
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
    redis_check._check_total_commands_processed(conn.info(), [])

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
    redis_check._check_total_commands_processed(conn.info(), ['test_total_commands_processed'])

    # Assert that the `redis.net.commands` metric was sent
    aggregator.assert_metric('redis.net.commands', value=1000, tags=['test_total_commands_processed'])
