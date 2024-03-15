# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.postgres.query_count_cache import QueryCountCache

pytestmark = [pytest.mark.unit]


def test_statement_queryid_cache_initial_doesnt_change():
    cache = QueryCountCache()
    changed = cache.set_calls(123, 1)

    assert changed is False


def test_statement_queryid_cache_multiple_calls_change():
    cache = QueryCountCache()
    cache.set_calls(123, 1)
    changed = cache.set_calls(123, 2)

    assert changed is True


def test_statement_queryid_cache_eviction():
    cache = QueryCountCache()
    cache.set_calls(123, 1)
    changed = cache.set_calls(123, 2)

    assert changed is True
