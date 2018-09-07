# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals
from distutils.version import StrictVersion
from copy import deepcopy

from datadog_checks.redisdb import Redis
import pytest
import mock
import redis

from .common import PORT, PASSWORD, HOST


# Following metrics are tagged by db
DB_TAGGED_METRICS = [
    'redis.persist.percent',
    'redis.expires.percent',
    'redis.persist',
    'redis.keys',
    'redis.expires',
]

STAT_METRICS = [
    'redis.command.calls',
    'redis.command.usec_per_call'
]


@pytest.mark.integration
def test_redis_default(aggregator, redis_auth, redis_instance):
    """

    """
    db = redis.Redis(port=PORT, db=14, password=PASSWORD, host=HOST)
    db.flushdb()
    db.lpush("test_list", 1)
    db.lpush("test_list", 2)
    db.lpush("test_list", 3)
    db.set("key1", "value")
    db.set("key2", "value")
    db.setex("expirekey", "expirevalue", 1000)

    redis_check = Redis('redisdb', {}, {})
    redis_check.check(redis_instance)

    # check the aggregator received some metrics
    assert aggregator.metric_names, "No metrics returned"

    # check those metrics have the right tags
    expected = ['foo:bar', 'redis_host:{}'.format(HOST), 'redis_port:6379', 'redis_role:master']
    expected_db = expected + ['redis_db:db14']

    assert aggregator.metric_names
    for name in aggregator.metric_names:
        if name in DB_TAGGED_METRICS:
            aggregator.assert_metric(name, tags=expected_db)
        elif name != 'redis.key.length':
            aggregator.assert_metric(name, tags=expected)

    aggregator.assert_metric('redis.key.length', 3, count=1, tags=expected + ['key:test_list'])

    # in the old tests these was explicitly asserted, keeping it like that
    assert 'redis.net.commands' in aggregator.metric_names
    version = db.info().get('redis_version')
    if StrictVersion(version) >= StrictVersion('2.6.0'):
        # instantaneous_ops_per_sec info is only available on redis>=2.6
        assert 'redis.net.instantaneous_ops_per_sec' in aggregator.metric_names
    db.flushdb()


@pytest.mark.integration
def test_service_check(aggregator, redis_auth, redis_instance):
    """

    """
    redis_check = Redis('redisdb', {}, {})
    redis_check.check(redis_instance)

    assert len(aggregator.service_checks('redis.can_connect')) == 1
    sc = aggregator.service_checks('redis.can_connect')[0]
    assert sc.tags == ['foo:bar', 'redis_host:{}'.format(HOST), 'redis_port:6379', 'redis_role:master']


@pytest.mark.integration
def test_service_metadata(redis_instance):
    """
    The Agent toolkit doesn't support service_metadata yet, so we use Mock
    """
    redis_check = Redis('redisdb', {}, {})
    redis_check._collect_metadata = mock.MagicMock()
    redis_check.check(redis_instance)
    redis_check._collect_metadata.assert_called_once()


@pytest.mark.integration
def test_redis_command_stats(aggregator, redis_instance):
    db = redis.Redis(port=PORT, db=14, password=PASSWORD, host=HOST)
    version = db.info().get('redis_version')
    if StrictVersion(version) < StrictVersion('2.6.0'):
        # Command stats only works with Redis >= 2.6.0
        return

    redis_instance['command_stats'] = True
    redis_check = Redis('redisdb', {}, {})
    redis_check.check(redis_instance)

    for name in STAT_METRICS:
        aggregator.assert_metric(name)

    # Check the command stats for INFO, since we know we've called it
    for m in aggregator.metrics('redis.command.calls'):
        if 'command:info' in m.tags:
            found = True
            break
    else:
        found = False

    assert found


@pytest.mark.integration
def test__check_key_lengths_misconfig(aggregator, redis_instance):
    """
    The check shouldn't send anything if misconfigured
    """
    redis_check = Redis('redisdb', {}, {})
    c = redis_check._get_conn(redis_instance)

    # `keys` param is missing
    del redis_instance['keys']
    redis_check._check_key_lengths(c, redis_instance, [])
    assert len(list(aggregator.metrics('redis.key.length'))) == 0

    # `keys` is not a list
    redis_instance['keys'] = 'FOO'
    redis_check._check_key_lengths(c, redis_instance, [])
    assert len(list(aggregator.metrics('redis.key.length'))) == 0

    # `keys` is an empty list
    redis_instance['keys'] = []
    redis_check._check_key_lengths(c, redis_instance, [])
    assert len(list(aggregator.metrics('redis.key.length'))) == 0


@pytest.mark.integration
def test__check_key_lengths_single_db(aggregator, redis_instance):
    """
    Keys are stored in multiple databases but we collect data from
    one database only
    """
    redis_check = Redis('redisdb', {}, {})
    tmp = deepcopy(redis_instance)

    # fill db 0
    tmp['db'] = 0
    conn = redis_check._get_conn(tmp)
    conn.flushdb()
    conn.lpush('test_foo', 'value1')
    conn.lpush('test_foo', 'value2')

    # fill db 3
    tmp['db'] = 3
    conn = redis_check._get_conn(tmp)
    conn.flushdb()
    conn.lpush('test_foo', 'value3')
    conn.lpush('test_foo', 'value4')

    # collect only from 3
    redis_instance['db'] = 3
    redis_check._check_key_lengths(conn, redis_instance, [])

    # metric should be only one, not regarding the number of databases
    aggregator.assert_metric('redis.key.length', count=1)

    # that single metric should have value=2
    aggregator.assert_metric('redis.key.length', value=2)


@pytest.mark.integration
def test__check_key_lengths_multi_db(aggregator, redis_instance):
    """
    Keys are stored across different databases
    """
    redis_check = Redis('redisdb', {}, {})
    c = redis_check._get_conn(redis_instance)
    tmp = deepcopy(redis_instance)

    # also add a specific key to the instance
    redis_instance['keys'].append('missing_key')

    # fill db 0
    tmp['db'] = 0
    conn = redis_check._get_conn(tmp)
    conn.flushdb()
    conn.lpush('test_foo', 'value1')
    conn.lpush('test_foo', 'value2')
    conn.lpush('test_bar', 'value1')

    # fill db 3
    tmp['db'] = 3
    conn = redis_check._get_conn(tmp)
    conn.flushdb()
    conn.lpush('test_foo', 'value3')
    conn.lpush('test_foo', 'value4')

    redis_check._check_key_lengths(c, redis_instance, [])
    aggregator.assert_metric('redis.key.length', count=3)
    aggregator.assert_metric('redis.key.length', value=4, tags=['key:test_foo'])
    aggregator.assert_metric('redis.key.length', value=1, tags=['key:test_bar'])
    aggregator.assert_metric('redis.key.length', value=0, tags=['key:missing_key'])
