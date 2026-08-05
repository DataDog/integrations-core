# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for DeltaDetector."""

from datadog_checks.base.utils.db.delta_detector import DeltaDetector

METRIC_COLS = frozenset({'calls', 'total_exec_time', 'rows', 'shared_blks_hit'})


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
        assert result.changed_pgss_keys == set()

    def test_second_cycle_returns_derivatives_for_changed_rows(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10, rows=100)])

        result = dd.compute([self._make_row(101, calls=15, rows=150)])
        assert len(result.derivative_rows) == 1
        dr = result.derivative_rows[0]
        assert dr['calls'] == 5
        assert dr['rows'] == 50
        assert dr['queryid'] == 101
        assert (101, 1, 1) in result.changed_pgss_keys

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

    def test_vanished_pgss_keys_detected(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10), self._make_row(102, calls=20)])
        result = dd.compute([self._make_row(101, calls=15)])
        assert (102, 1, 1) in result.vanished_pgss_keys

    def test_execution_indicator_required(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10, total_exec_time=100.0)])
        result = dd.compute([self._make_row(101, calls=10, total_exec_time=105.0)])
        assert result.derivative_rows == []

    def test_new_queryid_is_not_in_changed_set(self):
        dd = DeltaDetector(metric_columns=METRIC_COLS, execution_indicators=frozenset({'calls'}))
        dd.compute([self._make_row(101, calls=10)])
        result = dd.compute([self._make_row(101, calls=15), self._make_row(102, calls=5)])
        assert (101, 1, 1) in result.changed_pgss_keys
        assert (102, 1, 1) not in result.changed_pgss_keys

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
