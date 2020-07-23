# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

import random

import pytest
import redis

from datadog_checks.redisdb import Redis

from .common import HOST, PASSWORD, PORT

TEST_KEY = "testkey"

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_slowlog(aggregator, redis_instance):
    db = redis.Redis(port=PORT, db=14, password=PASSWORD, host=HOST)

    # Tweaking Redis's config to have the test run faster
    db.config_set('slowlog-log-slower-than', 0)
    db.flushdb()

    # Generate some slow commands
    for _ in range(100):
        db.lpush(TEST_KEY, random.random())
    db.sort(TEST_KEY)

    assert db.slowlog_len() > 0

    redis_check = Redis('redisdb', {}, [redis_instance])
    redis_check.check(redis_instance)

    expected_tags = ['foo:bar', 'redis_host:{}'.format(HOST), 'redis_port:6379', 'command:LPUSH']
    aggregator.assert_metric('redis.slowlog.micros', tags=expected_tags)


def test_custom_slowlog(aggregator, redis_instance):
    redis_instance['slowlog-max-len'] = 1

    db = redis.Redis(port=PORT, db=14, password=PASSWORD, host=HOST)

    # Tweaking Redis's config to have the test run faster
    db.config_set('slowlog-log-slower-than', 0)
    db.flushdb()

    # Generate some slow commands
    for _ in range(100):
        db.lpush(TEST_KEY, random.random())
    db.sort(TEST_KEY)

    assert db.slowlog_len() > 0

    redis_check = Redis('redisdb', {}, [redis_instance])
    redis_check.check(redis_instance)

    # Let's check that we didn't put more than one slowlog entry in the
    # payload, as specified in the above agent configuration
    assert len(aggregator.metrics('redis.slowlog.micros')) == 1
