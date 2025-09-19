# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import pytest

from datadog_checks.base.utils.db.timed_cache import TimedCache


class TestTimedCache:
    def test_set_and_get_item(self):
        cache = TimedCache(600)  # Using a longer interval for most tests to avoid automatic clearing during testing
        cache['test_key'] = 'test_value'
        assert cache['test_key'] == 'test_value', "The value retrieved should match the value set."

    def test_get_with_default(self):
        cache = TimedCache(600)
        assert (
            cache.get('nonexistent', 'default') == 'default'
        ), "Should return the default value when the key is not found."

    def test_item_deletion(self):
        cache = TimedCache(600)
        cache['test_key'] = 'test_value'
        del cache['test_key']
        with pytest.raises(KeyError):
            _ = cache['test_key']  # Attempting to access deleted key should raise KeyError

    def test_expire(self):
        cache = TimedCache(1)  # Set a short interval for testing auto-clearing
        cache['test_key'] = 'test_value'
        assert cache, "The cache should not be empty immediately after setting an item."
        time.sleep(2)  # Wait enough time for the cache to clear itself
        assert cache.is_expired() is True, "The cache should be expired after the interval has passed."
        cache.clear()
        cache['test_key'] = 'test_value'
        assert cache, "The cache ttl should be reset."

    # Optionally, you can add a test to verify that multiple items are handled correctly.
    def test_multiple_items(self):
        cache = TimedCache(600)
        items = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        for k, v in items.items():
            cache[k] = v
        for k, v in items.items():
            assert cache[k] == v, "Each item should be retrievable and match the set value."
