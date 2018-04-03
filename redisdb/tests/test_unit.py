# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

from datadog_checks.redisdb import Redis


def test_init():
    check = Redis('redisdb', {}, {}, None)
    assert check.connections == {}
    assert len(check.last_timestamp_seen) == 0
