# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

from datadog_checks.redisdb import Redis


def test_init():
    check = Redis('redisdb', {}, {}, None)
    assert check.connections == {}
    assert len(check.last_timestamp_seen) == 0


def test__get_conn():
    check = Redis('redisdb', {}, {}, None)
    instance = {}

    # create a connection
    check._get_conn(instance)
    key1, conn1 = next(check.connections.iteritems())

    # assert connection is cached
    check._get_conn(instance)
    key2, conn2 = next(check.connections.iteritems())
    assert key2 == key1
    assert conn2 == conn1

    # disable cache and assert connection has changed
    instance['disable_connection_cache'] = True
    check._get_conn(instance)
    key2, conn2 = next(check.connections.iteritems())
    assert key2 == key1
    assert conn2 != conn1
