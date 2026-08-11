# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for QueryStats."""

from datadog_checks.base.utils.db.query_metrics import QueryStats

COUNTER_COLS = frozenset({'calls', 'total_exec_time', 'rows', 'shared_blks_hit'})


def row_key(row):
    """Key the test rows, which are modelled on a pg_stat_statements snapshot."""
    return row['queryid'], row['dbid'], row['userid']


class TestQueryStats:
    def _make_stats(self):
        return QueryStats(counter_columns=COUNTER_COLS, key=row_key, execution_indicators=frozenset({'calls'}))

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

    def test_first_snapshot_has_nothing_to_diff(self):
        stats = self._make_stats()
        delta = stats.diff([self._make_row(101, calls=10, rows=100)])
        assert delta.rows == []
        assert delta.changed_keys == set()

    def test_second_snapshot_returns_deltas_for_changed_rows(self):
        stats = self._make_stats()
        stats.diff([self._make_row(101, calls=10, rows=100)])

        delta = stats.diff([self._make_row(101, calls=15, rows=150)])
        assert len(delta.rows) == 1
        row = delta.rows[0]
        assert row['calls'] == 5
        assert row['rows'] == 50
        assert row['queryid'] == 101
        assert (101, 1, 1) in delta.changed_keys

    def test_unchanged_rows_are_not_emitted(self):
        stats = self._make_stats()
        stats.diff(
            [
                self._make_row(101, calls=10),
                self._make_row(102, calls=20),
            ]
        )
        delta = stats.diff(
            [
                self._make_row(101, calls=10),
                self._make_row(102, calls=25),
            ]
        )
        assert len(delta.rows) == 1
        assert delta.rows[0]['queryid'] == 102

    def test_negative_diff_discards_row(self):
        stats = self._make_stats()
        stats.diff([self._make_row(101, calls=10, rows=100)])
        delta = stats.diff([self._make_row(101, calls=5, rows=50)])
        assert delta.rows == []

    def test_returning_key_is_rebaselined(self):
        """A key that leaves the snapshot loses its baseline, so its counters are not diffed
        against a stale one when it comes back."""
        stats = self._make_stats()
        stats.diff([self._make_row(101, calls=10), self._make_row(102, calls=20)])
        stats.diff([self._make_row(101, calls=15)])

        delta = stats.diff([self._make_row(101, calls=16), self._make_row(102, calls=25)])
        assert [row['queryid'] for row in delta.rows] == [101]

    def test_execution_indicator_required(self):
        stats = self._make_stats()
        stats.diff([self._make_row(101, calls=10, total_exec_time=100.0)])
        delta = stats.diff([self._make_row(101, calls=10, total_exec_time=105.0)])
        assert delta.rows == []

    def test_new_key_is_not_in_changed_set(self):
        stats = self._make_stats()
        stats.diff([self._make_row(101, calls=10)])
        delta = stats.diff([self._make_row(101, calls=15), self._make_row(102, calls=5)])
        assert (101, 1, 1) in delta.changed_keys
        assert (102, 1, 1) not in delta.changed_keys

    def test_duplicate_key_rows_are_merged(self):
        stats = self._make_stats()
        stats.diff([self._make_row(101, calls=10, rows=100)])
        delta = stats.diff(
            [
                self._make_row(101, calls=8, rows=60),
                self._make_row(101, calls=7, rows=55),
            ]
        )
        assert len(delta.rows) == 1
        assert delta.rows[0]['calls'] == 5
        assert delta.rows[0]['rows'] == 15

    def test_reset_clears_state(self):
        stats = self._make_stats()
        stats.diff([self._make_row(101, calls=10)])
        stats.reset()
        delta = stats.diff([self._make_row(101, calls=15)])
        assert delta.rows == []

    def test_collapse_does_not_mutate_input_rows(self):
        stats = self._make_stats()
        snapshot = [
            self._make_row(101, calls=8, rows=60),
            self._make_row(101, calls=7, rows=55),
        ]
        before = [dict(row) for row in snapshot]
        stats.diff(snapshot)
        assert snapshot == before

    def test_key_callable_determines_the_counter_series(self):
        """Rows are grouped by whatever the key callable returns, not by any fixed column set."""
        stats = QueryStats(counter_columns=COUNTER_COLS, key=lambda row: row['queryid'])
        # Same queryid under two different dbids collapses into one series.
        stats.diff([self._make_row(101, dbid=1, calls=10), self._make_row(101, dbid=2, calls=5)])
        delta = stats.diff([self._make_row(101, dbid=1, calls=12), self._make_row(101, dbid=2, calls=8)])
        assert len(delta.rows) == 1
        assert delta.rows[0]['calls'] == 5
        assert delta.changed_keys == {101}
