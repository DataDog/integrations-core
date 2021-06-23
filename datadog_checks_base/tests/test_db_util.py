# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

from datadog_checks.base.utils.db.utils import RateLimitingTTLCache


def test_ratelimiting_ttl_cache():
    ttl = 0.1
    cache = RateLimitingTTLCache(maxsize=5, ttl=ttl)

    for i in range(5):
        assert cache.acquire(i), "cache is empty so the first set of keys should pass"
    for i in range(5, 10):
        assert not cache.acquire(i), "cache is full so we do not expect any more new keys to pass"
    for i in range(5):
        assert not cache.acquire(i), "none of the first set of keys should pass because they're still under TTL"

    assert len(cache) == 5, "cache should be at the max size"
    time.sleep(ttl * 2)
    assert len(cache) == 0, "cache should be empty after the TTL has kicked in"

    for i in range(5, 10):
        assert cache.acquire(i), "cache should be empty again so these keys should go in OK"
