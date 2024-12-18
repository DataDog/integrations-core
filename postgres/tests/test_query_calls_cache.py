# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.postgres.query_calls_cache import QueryCallsCache

pytestmark = [pytest.mark.unit]


def test_statement_queryid_cache_same_calls_does_not_change():
    cache = QueryCallsCache()
    cache.set_calls([{'queryid': 123, 'calls': 1}])
    cache.set_calls([{'queryid': 123, 'calls': 1}])

    assert cache.called_queryids == set()


def test_statement_queryid_cache_multiple_calls_change():
    cache = QueryCallsCache()
    cache.set_calls([{'queryid': 123, 'calls': 1}])
    cache.set_calls([{'queryid': 123, 'calls': 2}])

    assert cache.called_queryids == {123}


def test_statement_queryid_cache_after_pg_stat_statement_eviction():
    cache = QueryCallsCache()
    cache.set_calls([{'queryid': 123, 'calls': 100}])
    cache.set_calls([{'queryid': 123, 'calls': 5}])

    assert cache.called_queryids == {123}


def test_statement_queryid_cache_snapshot_eviction():
    cache = QueryCallsCache()
    cache.set_calls([{'queryid': 123, 'calls': 100}])
    cache.set_calls([{'queryid': 124, 'calls': 5}])

    assert cache.cache.get(123, None) is None


def test_statement_queryid_multiple_inserts():
    cache = QueryCallsCache()
    cache.set_calls([{'queryid': 123, 'calls': 100}, {'queryid': 124, 'calls': 5}])

    assert cache.cache[123] == 100
    assert cache.cache[124] == 5
