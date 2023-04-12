# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

import re

import pytest

from .common import HOST, PASSWORD, PORT

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_redis_auth_ok(aggregator, dd_run_check, check, redis_auth):
    """
    Test the check can authenticate and connect
    """
    instance = {'host': HOST, 'port': PORT, 'password': PASSWORD}
    redis = check(instance)
    dd_run_check(redis)
    assert aggregator.metric_names, "No metrics returned"


def test_redis_auth_empty_pass(dd_run_check, check, redis_auth):
    """
    Test the check providing an empty password
    """
    instance = {'host': HOST, 'port': PORT, 'password': ''}
    redis = check(instance)

    with pytest.raises(Exception, match=re.compile('authentication required|operation not permitted', re.I)):
        dd_run_check(redis, extract_message=True)


def test_redis_auth_wrong_pass(dd_run_check, check, redis_auth):
    """
    Test the check providing the wrong password
    """
    instance = {'host': HOST, 'port': PORT, 'password': 'badpass'}
    redis = check(instance)

    try:
        dd_run_check(redis, extract_message=True)
        assert 0, "Check should raise an exception"
    except Exception as e:
        msg = str(e).lower()
        assert ("invalid password" in msg) or ("wrongpass" in msg) or ("invalid username-password pair" in msg)
