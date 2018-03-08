# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals
from distutils.version import StrictVersion

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
    for name in aggregator.metric_names:
        if name in DB_TAGGED_METRICS:
            aggregator.assert_metric(name, tags=expected_db)
        else:
            aggregator.assert_metric(name, tags=expected)

    # in the old tests these was explicitly asserted, keeping it like that
    assert 'redis.net.commands' in aggregator.metric_names
    version = db.info().get('redis_version')
    if StrictVersion(version) >= StrictVersion('2.6.0'):
        # instantaneous_ops_per_sec info is only available on redis>=2.6
        assert 'redis.net.instantaneous_ops_per_sec' in aggregator.metric_names


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
    found = False
    for m in aggregator.metrics('redis.command.calls'):
        if 'command:info' in m.tags:
            found = True
            break
    assert found
