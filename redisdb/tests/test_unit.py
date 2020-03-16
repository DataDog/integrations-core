# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
from six import iteritems


def test_init(check):
    assert check.connections == {}
    assert len(check.last_timestamp_seen) == 0


def test__get_conn(check):
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


def test__check_command_stats_host(check, aggregator):
    conn = mock.MagicMock()
    conn.info.return_value = {
        # this is from a real use case in Redis >5.0 where this line can be
        # seen (notice the double ':')
        # cmdstat_host::calls=2,usec=145,usec_per_call=72.50
        'cmdstat_host': {'usec_per_call': 72.5, 'usec': 145, ':calls': 2}
    }
    check._check_command_stats(conn, ['foo:bar'])

    expected_tags = ['foo:bar', 'command:host']
    aggregator.assert_metric('redis.command.calls', value=2, count=1, tags=expected_tags)
    aggregator.assert_metric('redis.command.usec_per_call', value=72.5, count=1, tags=expected_tags)

    aggregator.reset()

    # test a normal command, too
    conn.info.return_value = {'cmdstat_lpush': {'usec_per_call': 14.00, 'usec': 56, 'calls': 4}}
    check._check_command_stats(conn, ['foo:bar'])

    expected_tags = ['foo:bar', 'command:lpush']
    aggregator.assert_metric('redis.command.calls', value=4, count=1, tags=expected_tags)
    aggregator.assert_metric('redis.command.usec_per_call', value=14.00, count=1, tags=expected_tags)
