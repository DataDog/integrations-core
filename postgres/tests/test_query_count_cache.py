# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.postgres.query_count_cache import QueryCountCache

pytestmark = [pytest.mark.unit]


def test_statement_queryid_cache_same_calls_does_not_change():
    cache = QueryCountCache(10000)
    cache.set_calls(123, 1)
    changed = cache.set_calls(123, 1)

    assert changed is False


def test_statement_queryid_cache_multiple_calls_change():
    cache = QueryCountCache(10000)
    cache.set_calls(123, 1)
    changed = cache.set_calls(123, 2)

    assert changed is True

def test_statement_queryid_cache_after_pg_stat_statement_eviction():
    cache = QueryCountCache(10000)
    cache.set_calls(123, 100)
    changed = cache.set_calls(123, 5)

    assert changed is True
