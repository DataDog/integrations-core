# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import pytest

from datadog_checks.redisdb import Redis

from .common import PORT, PASSWORD, HOST


@pytest.mark.integration
def test_redis_auth_ok(aggregator, redis_auth):
    """
    Test the check can authenticate and connect
    """
    redis = Redis('redisdb', {}, {})
    instance = {
        'host': HOST,
        'port': PORT,
        'password': PASSWORD,
    }
    redis.check(instance)
    assert aggregator.metric_names, "No metrics returned"


@pytest.mark.integration
def test_redis_auth_empty_pass(aggregator, redis_auth):
    """
    Test the check providing an empty password
    """
    redis = Redis('redisdb', {}, {})
    instance = {
        'host': HOST,
        'port': PORT,
        'password': ''
    }

    try:
        redis.check(instance)
        assert 0, "Check should raise an exception"
    except Exception as e:
        pre28_err = "noauth authentication required"
        post28_err = "operation not permitted"
        assert pre28_err in str(e).lower() or post28_err in str(e).lower()


@pytest.mark.integration
def test_redis_auth_wrong_pass(aggregator, redis_auth):
    """
    Test the check providing the wrong password
    """
    redis = Redis('redisdb', {}, {})
    instance = {
        'host': HOST,
        'port': PORT,
        'password': 'badpass'
    }

    try:
        redis.check(instance)
        assert 0, "Check should raise an exception"
    except Exception as e:
        assert "invalid password" in str(e).lower()
