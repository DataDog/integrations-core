# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

import re

import pytest

from datadog_checks.redisdb import Redis

from .common import HOST, PASSWORD, PORT

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_redis_auth_ok(aggregator, redis_auth):
    """
    Test the check can authenticate and connect
    """
    instance = {'host': HOST, 'port': PORT, 'password': PASSWORD}
    redis = Redis('redisdb', {}, [instance])
    redis.check(instance)
    assert aggregator.metric_names, "No metrics returned"


def test_redis_auth_empty_pass(redis_auth):
    """
    Test the check providing an empty password
    """
    instance = {'host': HOST, 'port': PORT, 'password': ''}
    redis = Redis('redisdb', {}, [instance])

    with pytest.raises(Exception, match=re.compile('authentication required|operation not permitted', re.I)):
        redis.check(instance)


def test_redis_auth_wrong_pass(redis_auth):
    """
    Test the check providing the wrong password
    """
    instance = {'host': HOST, 'port': PORT, 'password': 'badpass'}
    redis = Redis('redisdb', {}, [instance])

    try:
        redis.check(instance)
        assert 0, "Check should raise an exception"
    except Exception as e:
        assert "invalid password" in str(e).lower()
