# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals
import random

from datadog_checks.redisdb import Redis
import redis
import pytest

from .common import PORT, PASSWORD, HOST


TEST_KEY = "testkey"


@pytest.mark.integration
def test_slowlog(aggregator, redis_instance):
    db = redis.Redis(port=PORT, db=14, password=PASSWORD, host=HOST)

    # Tweaking Redis's config to have the test run faster
    db.config_set('slowlog-log-slower-than', 0)
    db.flushdb()

    # Generate some slow commands
    for i in range(100):
        db.lpush(TEST_KEY, random.random())
    db.sort(TEST_KEY)

    assert db.slowlog_len() > 0

    redis_check = Redis('redisdb', {}, {})
    redis_check.check(redis_instance)

    expected_tags = ['foo:bar', 'redis_host:{}'.format(HOST), 'redis_port:6379', 'command:LPUSH']
    aggregator.assert_metric('redis.slowlog.micros', tags=expected_tags)


@pytest.mark.integration
def test_custom_slowlog(aggregator, redis_instance):
    redis_instance['slowlog-max-len'] = 1

    db = redis.Redis(port=PORT, db=14, password=PASSWORD, host=HOST)

    # Tweaking Redis's config to have the test run faster
    db.config_set('slowlog-log-slower-than', 0)
    db.flushdb()

    # Generate some slow commands
    for i in range(100):
        db.lpush(TEST_KEY, random.random())
    db.sort(TEST_KEY)

    assert db.slowlog_len() > 0

    redis_check = Redis('redisdb', {}, {})
    redis_check.check(redis_instance)

    # Let's check that we didn't put more than one slowlog entry in the
    # payload, as specified in the above agent configuration
    assert len(aggregator.metrics('redis.slowlog.micros')) == 1
