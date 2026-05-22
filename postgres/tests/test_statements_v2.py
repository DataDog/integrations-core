# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for the V2 statement metrics layers (DeltaDetector, ObfuscationLookup)."""

from datadog_checks.postgres.delta_detector import DeltaDetector
from datadog_checks.postgres.obfuscation_lookup import ObfuscationLookup

METRIC_COLS = frozenset({'calls', 'total_exec_time', 'rows', 'shared_blks_hit'})


# ---------------------------------------------------------------------------
# DeltaDetector
# ---------------------------------------------------------------------------


class TestDeltaDetector:
    def _make_row(self, queryid, dbid=1, userid=1, datname='mydb', rolname='myrole', **counters):
        row = {
            'queryid': queryid,
            'dbid': dbid,
            'userid': userid,
            'datname': datname,
            'rolname': rolname,
            'calls': 0,
            'total_exec_time': 0.0,
            'rows': 0,
            'shared_blks_hit': 0,
        }
        row.update(counters)
        return row

    def test_first_cycle_returns_no_derivatives(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        rows = [self._make_row(101, calls=10, rows=100)]
        result = dd.compute(rows)
        assert result.derivative_rows == []
        assert result.changed_queryids == set()

    def test_second_cycle_returns_derivatives_for_changed_rows(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10, rows=100)])

        result = dd.compute([self._make_row(101, calls=15, rows=150)])
        assert len(result.derivative_rows) == 1
        dr = result.derivative_rows[0]
        assert dr['calls'] == 5
        assert dr['rows'] == 50
        assert dr['queryid'] == 101
        assert 101 in result.changed_queryids

    def test_unchanged_rows_are_not_emitted(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        rows = [
            self._make_row(101, calls=10),
            self._make_row(102, calls=20),
        ]
        dd.compute(rows)
        rows_same = [
            self._make_row(101, calls=10),
            self._make_row(102, calls=25),
        ]
        result = dd.compute(rows_same)
        assert len(result.derivative_rows) == 1
        assert result.derivative_rows[0]['queryid'] == 102

    def test_negative_diff_discards_row(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10, rows=100)])
        result = dd.compute([self._make_row(101, calls=5, rows=50)])
        assert result.derivative_rows == []

    def test_vanished_queryids_detected(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10), self._make_row(102, calls=20)])
        result = dd.compute([self._make_row(101, calls=15)])
        assert 102 in result.vanished_queryids

    def test_execution_indicator_required(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10, total_exec_time=100.0)])
        result = dd.compute([self._make_row(101, calls=10, total_exec_time=105.0)])
        assert result.derivative_rows == []

    def test_new_queryid_is_not_in_changed_set(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10)])
        result = dd.compute([self._make_row(101, calls=15), self._make_row(102, calls=5)])
        assert 101 in result.changed_queryids
        assert 102 not in result.changed_queryids

    def test_duplicate_queryid_rows_are_merged(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10, rows=100)])
        rows = [
            self._make_row(101, calls=8, rows=60),
            self._make_row(101, calls=7, rows=55),
        ]
        result = dd.compute(rows)
        assert len(result.derivative_rows) == 1
        assert result.derivative_rows[0]['calls'] == 5
        assert result.derivative_rows[0]['rows'] == 15

    def test_reset_clears_state(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10)])
        dd.reset()
        result = dd.compute([self._make_row(101, calls=15)])
        assert result.derivative_rows == []


# ---------------------------------------------------------------------------
# ObfuscationLookup
# ---------------------------------------------------------------------------


class TestObfuscationLookup:
    def _make_lookup(self, maxsize=100):
        return ObfuscationLookup(maxsize=maxsize, obfuscate_options='{}')

    def test_empty_lookup_all_misses(self):
        lk = self._make_lookup()
        hits, misses = lk.lookup({1, 2, 3})
        assert hits == {}
        assert misses == {1, 2, 3}

    def test_populate_then_lookup(self):
        lk = self._make_lookup()
        lk.populate({1: 'SELECT 1', 2: 'SELECT 2'})
        hits, misses = lk.lookup({1, 2, 3})
        assert 1 in hits
        assert 2 in hits
        assert misses == {3}
        assert hits[1].obfuscated_query is not None
        assert hits[1].query_signature is not None

    def test_hit_and_miss_counters(self):
        lk = self._make_lookup()
        lk.populate({1: 'SELECT 1'})
        lk.reset_stats()
        lk.lookup({1, 2})
        assert lk.hits == 1
        assert lk.misses == 1

    def test_evict_removes_queryid(self):
        lk = self._make_lookup()
        lk.populate({1: 'SELECT 1', 2: 'SELECT 2'})
        lk.evict({1})
        hits, misses = lk.lookup({1, 2})
        assert 1 in misses
        assert 2 in hits

    def test_multiple_queryids_share_signature(self):
        """Different queryids with the same normalized SQL share one ObfuscationResult."""
        lk = self._make_lookup()
        lk.populate({1: 'SELECT 1', 2: 'SELECT 1'})
        hits, _ = lk.lookup({1, 2})
        assert hits[1].query_signature == hits[2].query_signature
        assert lk.queryid_map_size == 2
        assert lk.signature_map_size == 1

    def test_lru_eviction_on_max_size(self):
        lk = self._make_lookup(maxsize=2)
        lk.populate({1: 'SELECT 1', 2: 'SELECT 2', 3: 'SELECT 3'})
        assert lk.queryid_map_size == 2
        _, misses = lk.lookup({1})
        assert 1 in misses

    def test_populate_returns_results(self):
        lk = self._make_lookup()
        results = lk.populate({1: 'SELECT 1', 2: 'SELECT 2'})
        assert 1 in results
        assert 2 in results
        assert results[1].obfuscated_query is not None

    def test_evict_does_not_remove_shared_signature(self):
        """Evicting a queryid removes tier-1 mapping but keeps tier-2 if other queryids share it."""
        lk = self._make_lookup()
        lk.populate({1: 'SELECT 1', 2: 'SELECT 1'})
        lk.evict({1})
        hits, _ = lk.lookup({2})
        assert 2 in hits

    def test_lookup_updates_lru_order(self):
        lk = self._make_lookup(maxsize=2)
        lk.populate({1: 'SELECT 1', 2: 'SELECT 2'})
        lk.lookup({1})
        lk.populate({3: 'SELECT 3'})
        hits, _ = lk.lookup({1})
        assert 1 in hits
        _, misses = lk.lookup({2})
        assert 2 in misses
