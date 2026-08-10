# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for DeltaDetector."""

from datadog_checks.base.utils.db.delta_detector import DeltaDetector

METRIC_COLS = frozenset({'calls', 'total_exec_time', 'rows', 'shared_blks_hit'})


def row_key(row):
    """Key the test rows, which are modelled on a pg_stat_statements snapshot."""
    return row['queryid'], row['dbid'], row['userid']


class TestDeltaDetector:
    def _make_detector(self):
        return DeltaDetector(metric_columns=METRIC_COLS, key=row_key, execution_indicators=frozenset({'calls'}))

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
        dd = self._make_detector()
        rows = [self._make_row(101, calls=10, rows=100)]
        result = dd.compute(rows)
        assert result.derivative_rows == []
        assert result.changed_keys == set()

    def test_second_cycle_returns_derivatives_for_changed_rows(self):
        dd = self._make_detector()
        dd.compute([self._make_row(101, calls=10, rows=100)])

        result = dd.compute([self._make_row(101, calls=15, rows=150)])
        assert len(result.derivative_rows) == 1
        dr = result.derivative_rows[0]
        assert dr['calls'] == 5
        assert dr['rows'] == 50
        assert dr['queryid'] == 101
        assert (101, 1, 1) in result.changed_keys

    def test_unchanged_rows_are_not_emitted(self):
        dd = self._make_detector()
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
        dd = self._make_detector()
        dd.compute([self._make_row(101, calls=10, rows=100)])
        result = dd.compute([self._make_row(101, calls=5, rows=50)])
        assert result.derivative_rows == []

    def test_returning_key_is_rebaselined(self):
        """A key that leaves the snapshot loses its baseline, so its counters are not diffed
        against a stale one when it comes back."""
        dd = self._make_detector()
        dd.compute([self._make_row(101, calls=10), self._make_row(102, calls=20)])
        dd.compute([self._make_row(101, calls=15)])

        result = dd.compute([self._make_row(101, calls=16), self._make_row(102, calls=25)])
        assert [row['queryid'] for row in result.derivative_rows] == [101]

    def test_execution_indicator_required(self):
        dd = self._make_detector()
        dd.compute([self._make_row(101, calls=10, total_exec_time=100.0)])
        result = dd.compute([self._make_row(101, calls=10, total_exec_time=105.0)])
        assert result.derivative_rows == []

    def test_new_key_is_not_in_changed_set(self):
        dd = self._make_detector()
        dd.compute([self._make_row(101, calls=10)])
        result = dd.compute([self._make_row(101, calls=15), self._make_row(102, calls=5)])
        assert (101, 1, 1) in result.changed_keys
        assert (102, 1, 1) not in result.changed_keys

    def test_duplicate_key_rows_are_merged(self):
        dd = self._make_detector()
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
        dd = self._make_detector()
        dd.compute([self._make_row(101, calls=10)])
        dd.reset()
        result = dd.compute([self._make_row(101, calls=15)])
        assert result.derivative_rows == []

    def test_collapse_does_not_mutate_input_rows(self):
        dd = self._make_detector()
        rows = [
            self._make_row(101, calls=8, rows=60),
            self._make_row(101, calls=7, rows=55),
        ]
        before = [dict(row) for row in rows]
        dd.compute(rows)
        assert rows == before

    def test_key_callable_determines_the_counter_series(self):
        """Rows are grouped by whatever the key callable returns, not by any fixed column set."""
        dd = DeltaDetector(metric_columns=METRIC_COLS, key=lambda row: row['queryid'])
        # Same queryid under two different dbids collapses into one series.
        dd.compute([self._make_row(101, dbid=1, calls=10), self._make_row(101, dbid=2, calls=5)])
        result = dd.compute([self._make_row(101, dbid=1, calls=12), self._make_row(101, dbid=2, calls=8)])
        assert len(result.derivative_rows) == 1
        assert result.derivative_rows[0]['calls'] == 5
        assert result.changed_keys == {101}
