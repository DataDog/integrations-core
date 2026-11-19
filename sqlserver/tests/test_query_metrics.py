# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import patch

import pytest

from datadog_checks.sqlserver.query_metrics import QueryMetrics

pytestmark = pytest.mark.unit

METRICS = ['execution_count', 'total_logical_reads']


def _row(handle: str, executions: int, **kwargs) -> dict:
    return {
        'dbid': 1,
        'database_name': 'test',
        'query_signature': 'query',
        'query_hash': 'hash',
        'query_plan_hash': 'same-shape',
        'plan_handle': handle,
        'statement_start_offset': 0,
        'statement_end_offset': -1,
        'plan_generation_num': 1,
        'creation_time': '2026-11-19T10:00:00',
        'execution_count': executions,
        'total_logical_reads': executions * 10,
        **kwargs,
    }


def test_shared_plan_hash_with_idle_handle():
    # SDBM-3132: a returning handle must contribute its increment, not its lifetime total.
    state = QueryMetrics()
    assert state.compute_deltas([_row('a', 100), _row('b', 5000)], METRICS) == []
    active = state.compute_deltas([_row('a', 110)], METRICS)
    assert sum(r['execution_count'] for r in active) == 10
    assert state.compute_deltas([], METRICS) == []
    returned = state.compute_deltas([_row('a', 120), _row('b', 5020)], METRICS)
    assert sum(r['execution_count'] for r in returned) == 30
    assert sum(r['total_logical_reads'] for r in returned) == 300


def test_unknown_handle_does_not_emit_lifetime_total_after_startup():
    state = QueryMetrics()
    state.compute_deltas([_row('a', 100)], METRICS)
    rows = state.compute_deltas([_row('a', 110), _row('old-unseen', 5000)], METRICS)
    assert [(r['plan_handle'], r['execution_count']) for r in rows] == [('a', 10)]
    rows = state.compute_deltas([_row('old-unseen', 5010)], METRICS)
    assert rows[0]['execution_count'] == 10


def test_recompilation_with_larger_counters_establishes_new_baseline():
    state = QueryMetrics()
    state.compute_deltas([_row('a', 10)], METRICS)
    recompiled = _row('a', 1000, plan_generation_num=2)
    assert state.compute_deltas([recompiled], METRICS) == []
    rows = state.compute_deltas([{**recompiled, 'execution_count': 1005, 'total_logical_reads': 10050}], METRICS)
    assert rows[0]['execution_count'] == 5
    # Compilation time distinguishes a reused handle even when the generation repeats.
    reused = _row('a', 2000, plan_generation_num=2, creation_time='2026-11-19T11:00:00')
    assert state.compute_deltas([reused], METRICS) == []


def test_database_and_statement_offsets_have_independent_counters():
    state = QueryMetrics()
    rows = [
        _row('a', 10),
        _row('a', 100, dbid=2, database_name='other'),
        _row('a', 1000, statement_start_offset=100),
        _row('a', 10000, statement_end_offset=200),
    ]
    state.compute_deltas(rows, METRICS)
    advanced = [{**r, 'execution_count': r['execution_count'] + 1} for r in rows]
    assert [r['execution_count'] for r in state.compute_deltas(advanced, METRICS)] == [1, 1, 1, 1]


def test_expired_baseline_is_safe_even_when_no_empty_collection_occurs():
    state = QueryMetrics(retention=60)
    with patch('time.monotonic', return_value=0):
        state.compute_deltas([_row('a', 100)], METRICS)
    with patch('time.monotonic', return_value=60):
        assert state.compute_deltas([_row('a', 5000)], METRICS) == []
    with patch('time.monotonic', return_value=61):
        rows = state.compute_deltas([_row('a', 5010)], METRICS)
    assert rows[0]['execution_count'] == 10


def test_churn_retains_active_baseline_and_safely_baselines_evicted_handle():
    state = QueryMetrics(max_size=2)
    state.compute_deltas([_row('active', 100), _row('old', 5000)], METRICS)
    for cycle in range(1, 5):
        # New rows precede the active row, exercising eviction during collection.
        rows = state.compute_deltas([_row(f'new-{cycle}', 1000), _row('active', 100 + cycle)], METRICS)
        assert [(r['plan_handle'], r['execution_count']) for r in rows] == [('active', 1)]
        assert len(state._previous) == 2
    rows = state.compute_deltas([_row('old', 5010), _row('active', 105)], METRICS)
    assert [(r['plan_handle'], r['execution_count']) for r in rows] == [('active', 1)]


def test_decreasing_counter_rebaselines_entire_statement():
    state = QueryMetrics()
    state.compute_deltas([_row('a', 100)], METRICS)
    assert state.compute_deltas([_row('a', 110, total_logical_reads=1)], METRICS) == []
    rows = state.compute_deltas([_row('a', 111, total_logical_reads=11)], METRICS)
    assert rows[0]['execution_count'] == 1
    assert rows[0]['total_logical_reads'] == 10


def test_new_metric_column_does_not_leak_lifetime_total():
    state = QueryMetrics()
    state.compute_deltas([_row('a', 100)], ['execution_count'])
    assert state.compute_deltas([_row('a', 110)], METRICS) == []
    rows = state.compute_deltas([_row('a', 111)], METRICS)
    assert rows[0]['execution_count'] == 1
    assert rows[0]['total_logical_reads'] == 10
