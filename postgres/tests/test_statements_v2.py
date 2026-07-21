# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for the V2 statement metrics layers (DeltaDetector, ObfuscationLookup, PostgresStatementMetricsV2)."""

import json
from unittest import mock

import pytest
from semver import VersionInfo

from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.config import build_config
from datadog_checks.postgres.delta_detector import DeltaDetector
from datadog_checks.postgres.obfuscation_lookup import ObfuscationLookup
from datadog_checks.postgres.statements import (
    PG_STAT_STATEMENTS_TIMING_COLUMNS,
    PG_STAT_STATEMENTS_TIMING_COLUMNS_LT_17,
)
from datadog_checks.postgres.statements_v2 import (
    DEFAULT_PGSS_MAX,
    LIGHTWEIGHT_DESIRED_COLUMNS,
    PostgresStatementMetricsV2,
)

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


# ---------------------------------------------------------------------------
# ObfuscationLookup
# ---------------------------------------------------------------------------


class TestObfuscationLookup:
    def _make_lookup(self, maxsize=100):
        return ObfuscationLookup(maxsize=maxsize, obfuscate_options='{}')

    def test_empty_lookup_all_misses(self):
        lk = self._make_lookup()
        hits, misses = lk.lookup({(1, 1, 1), (2, 1, 1), (3, 1, 1)})
        assert hits == {}
        assert misses == {(1, 1, 1), (2, 1, 1), (3, 1, 1)}

    def test_populate_then_lookup(self):
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 2'})
        hits, misses = lk.lookup({(1, 1, 1), (2, 1, 1), (3, 1, 1)})
        assert (1, 1, 1) in hits
        assert (2, 1, 1) in hits
        assert misses == {(3, 1, 1)}
        assert hits[(1, 1, 1)].obfuscated_query is not None
        assert hits[(1, 1, 1)].query_signature is not None

    def test_hit_and_miss_counters(self):
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1'})
        lk.reset_stats()
        lk.lookup({(1, 1, 1), (2, 1, 1)})
        assert lk.hits == 1
        assert lk.misses == 1

    def test_evict_removes_pgss_key(self):
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 2'})
        lk.evict({(1, 1, 1)})
        hits, misses = lk.lookup({(1, 1, 1), (2, 1, 1)})
        assert (1, 1, 1) in misses
        assert (2, 1, 1) in hits

    def test_multiple_pgss_keys_share_signature(self):
        """Different pgss keys with the same normalized SQL share one ObfuscationResult."""
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 1'})
        hits, _ = lk.lookup({(1, 1, 1), (2, 1, 1)})
        assert hits[(1, 1, 1)].query_signature == hits[(2, 1, 1)].query_signature
        assert lk.queryid_map_size == 2
        assert lk.signature_map_size == 1

    def test_lru_eviction_on_max_size(self):
        lk = self._make_lookup(maxsize=2)
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 2, 2): 'SELECT 2', (3, 3, 3): 'SELECT 3'})
        assert lk.queryid_map_size == 2
        _, misses = lk.lookup({(1, 1, 1)})
        assert (1, 1, 1) in misses

    def test_populate_returns_results(self):
        lk = self._make_lookup()
        results = lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 2'})
        assert (1, 1, 1) in results
        assert (2, 1, 1) in results
        assert results[(1, 1, 1)].obfuscated_query is not None

    def test_evict_does_not_remove_shared_signature(self):
        """Evicting one pgss key removes tier-1 mapping but keeps tier-2 if other keys share it."""
        lk = self._make_lookup()
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 1'})
        lk.evict({(1, 1, 1)})
        hits, _ = lk.lookup({(2, 1, 1)})
        assert (2, 1, 1) in hits

    def test_lookup_updates_lru_order(self):
        lk = self._make_lookup(maxsize=2)
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 2, 2): 'SELECT 2'})
        lk.lookup({(1, 1, 1)})
        lk.populate({(3, 3, 3): 'SELECT 3'})
        hits, _ = lk.lookup({(1, 1, 1)})
        assert (1, 1, 1) in hits
        _, misses = lk.lookup({(2, 2, 2)})
        assert (2, 2, 2) in misses

    # --- negative cache (ignored keys) ---

    def test_mark_ignored_excludes_from_hits_and_misses(self):
        """A negatively-cached key is neither a hit nor a miss on lookup."""
        lk = self._make_lookup()
        lk.mark_ignored({(1, 1, 1)})
        hits, misses = lk.lookup({(1, 1, 1), (2, 1, 1)})
        assert (1, 1, 1) not in hits
        assert (1, 1, 1) not in misses
        assert misses == {(2, 1, 1)}
        assert lk.ignored_map_size == 1

    def test_ignored_keys_do_not_increment_miss_counter(self):
        lk = self._make_lookup()
        lk.mark_ignored({(1, 1, 1)})
        lk.reset_stats()
        lk.lookup({(1, 1, 1)})
        assert lk.misses == 0
        assert lk.hits == 0

    def test_evict_forgets_ignored_key(self):
        """Evicting a vanished key clears its negative-cache entry so it can be re-evaluated."""
        lk = self._make_lookup()
        lk.mark_ignored({(1, 1, 1)})
        lk.evict({(1, 1, 1)})
        assert lk.ignored_map_size == 0
        _, misses = lk.lookup({(1, 1, 1)})
        assert (1, 1, 1) in misses

    def test_ignored_keys_lru_trimmed_to_maxsize(self):
        lk = self._make_lookup(maxsize=2)
        lk.mark_ignored({(1, 1, 1), (2, 2, 2), (3, 3, 3)})
        assert lk.ignored_map_size == 2

    def test_mark_ignored_drops_stale_positive_mapping(self):
        """An ignored key must not resurface as a hit via a stale tier-1 mapping.

        Reproduces the case where a key keeps its tier-1 mapping after its tier-2
        signature was evicted: marking it ignored must drop the tier-1 entry so that,
        even after the negative entry is trimmed and the signature is repopulated by
        another key, the ignored key never produces a positive hit.
        """
        lk = self._make_lookup()
        # Two keys share the same normalized SQL (one signature).
        lk.populate({(1, 1, 1): 'SELECT 1', (2, 1, 1): 'SELECT 1'})
        assert lk.queryid_map_size == 2

        # Key (1, 1, 1) turns out to be ignorable; its tier-1 mapping must be dropped.
        lk.mark_ignored({(1, 1, 1)})
        assert (1, 1, 1) not in lk._key_to_sig

        # The shared signature is still cached (via the other key), but the ignored key
        # must not hit it.
        hits, misses = lk.lookup({(1, 1, 1)})
        assert (1, 1, 1) not in hits
        assert (1, 1, 1) not in misses


# ---------------------------------------------------------------------------
# PostgresStatementMetricsV2 — unit tests (no live database)
# ---------------------------------------------------------------------------


class TestPostgresStatementMetricsV2:
    """Unit tests for PostgresStatementMetricsV2 methods that do not require a live DB."""

    def _make(self, **overrides) -> PostgresStatementMetricsV2:
        """Construct a PostgresStatementMetricsV2 using a real InstanceConfig and a mock check."""
        outer_check = PostgreSql('postgres', {}, [{"host": "host", "username": "user"}])
        config, _ = build_config(outer_check)

        mock_check = mock.MagicMock()
        mock_check.version = VersionInfo(16, 0, 0)
        mock_check.pg_settings = {}
        mock_check.reported_hostname = 'test.host'
        mock_check._get_debug_tags.return_value = []

        v2 = PostgresStatementMetricsV2(mock_check, config)
        v2._log = mock.MagicMock()  # replace module logger so tests can assert on warnings
        v2.tags = []
        v2._tags_no_db = []

        for key, val in overrides.items():
            setattr(v2, key, val)

        return v2

    # --- payload batching ---

    def test_payload_single_batch(self):
        """Rows that fit within batch_max_content_size are returned as one payload."""
        v2 = self._make()
        wrapper = {'host': 'h', 'timestamp': 0, 'tags': []}
        rows = [{'query': 'SELECT 1', 'calls': 1}]
        payloads = v2._get_query_metrics_payloads(wrapper, rows)
        assert len(payloads) == 1
        assert json.loads(payloads[0])['postgres_rows'] == rows

    def test_payload_splits_when_too_large(self):
        """A batch exceeding batch_max_content_size is binary-split until each chunk fits."""
        v2 = self._make(batch_max_content_size=200)
        wrapper = {'host': 'h', 'timestamp': 0, 'tags': []}
        rows = [{'query': 'SELECT ' + 'x' * 50, 'calls': i} for i in range(10)]
        payloads = v2._get_query_metrics_payloads(wrapper, rows)
        assert len(payloads) > 1
        all_rows = [r for p in payloads for r in json.loads(p)['postgres_rows']]
        assert sorted(r['calls'] for r in all_rows) == list(range(10))

    def test_payload_drops_single_oversized_row(self):
        """A single row whose serialized size exceeds the limit is dropped with a warning."""
        v2 = self._make(batch_max_content_size=10)
        wrapper = {'host': 'h', 'timestamp': 0, 'tags': []}
        rows = [{'query': 'SELECT ' + 'x' * 100, 'calls': 1}]
        payloads = v2._get_query_metrics_payloads(wrapper, rows)
        assert payloads == []
        v2._log.warning.assert_called_once()
        assert 'dropped' in v2._log.warning.call_args[0][0].lower()

    # --- obfuscation text filtering ---

    @pytest.mark.parametrize(
        "sentinel",
        [
            pytest.param('<insufficient privilege>', id='insufficient_privilege'),
            pytest.param('/* DDIGNORE */ SELECT secret', id='ddignore'),
        ],
    )
    def test_resolve_obfuscations_filters_sentinel(self, sentinel):
        """Sentinel query texts are excluded from the obfuscation lookup."""
        v2 = self._make()
        key = (1, 1, 1)
        with mock.patch.object(v2, '_fetch_query_texts', return_value={key: sentinel}):
            result = v2._resolve_obfuscations({key}, set())
        assert key not in result

    def test_resolve_obfuscations_partial_filter(self):
        """Only sentinel-valued keys are filtered; valid queries still appear in the result."""
        v2 = self._make()
        bad_key = (1, 1, 1)
        good_key = (2, 1, 1)
        with mock.patch.object(
            v2,
            '_fetch_query_texts',
            return_value={bad_key: '<insufficient privilege>', good_key: 'SELECT 1'},
        ):
            result = v2._resolve_obfuscations({bad_key, good_key}, set())
        assert bad_key not in result
        assert good_key in result

    def test_resolve_obfuscations_skips_known_ddignore_keys_on_later_cycles(self):
        """A DDIGNORE key is fetched once, negative-cached, then skipped (no fetch) on later cycles."""
        v2 = self._make()
        ddignore_key = (1, 1, 1)

        with mock.patch.object(
            v2, '_fetch_query_texts', return_value={ddignore_key: '/* DDIGNORE */ SELECT 1'}
        ) as fetch:
            v2._resolve_obfuscations({ddignore_key}, set())
            assert fetch.call_count == 1
            assert ddignore_key in v2._obfuscation_lookup._ignored_keys

            # Second cycle: same key changes again but is now skipped before the fetch.
            result = v2._resolve_obfuscations({ddignore_key}, set())
            assert result == {}
            assert fetch.call_count == 1

    def test_resolve_obfuscations_does_not_fetch_when_all_keys_ignored(self):
        """When every changed key is already negative-cached, no text fetch is issued."""
        v2 = self._make()
        ddignore_key = (1, 1, 1)
        v2._obfuscation_lookup.mark_ignored({ddignore_key})
        with mock.patch.object(v2, '_fetch_query_texts') as fetch:
            result = v2._resolve_obfuscations({ddignore_key}, set())
        assert result == {}
        fetch.assert_not_called()

    def test_resolve_obfuscations_forgets_ignored_key_when_vanished(self):
        """An ignored key that vanishes from pgss is dropped from the negative cache via evict."""
        v2 = self._make()
        ddignore_key = (1, 1, 1)
        v2._obfuscation_lookup.mark_ignored({ddignore_key})
        with mock.patch.object(v2, '_fetch_query_texts', return_value={}):
            v2._resolve_obfuscations(set(), {ddignore_key})
        assert ddignore_key not in v2._obfuscation_lookup._ignored_keys

    # --- execute query cancel event ---

    def test_execute_query_raises_when_cancelled(self):
        """Setting the cancel event causes _execute_query to raise before touching the DB."""
        v2 = self._make()
        v2._cancel_event.set()
        with pytest.raises(Exception, match='[Cc]ancelled'):
            v2._execute_query('SELECT 1')
        v2._check._get_main_db.assert_not_called()

    # --- dealloc pre-V14 early return ---

    def test_emit_dealloc_skipped_before_v14(self):
        """_emit_pg_stat_statements_dealloc returns early for PG < 14."""
        v2 = self._make()
        v2._check.version = VersionInfo(13, 9, 0)
        v2._emit_pg_stat_statements_dealloc()
        v2._check.monotonic_count.assert_not_called()
        v2._check._get_main_db.assert_not_called()

    # --- sync cache sizes ---

    @pytest.mark.parametrize(
        "pg_setting, initial_maxsize, expected_maxsize",
        [
            pytest.param('2000', DEFAULT_PGSS_MAX, 2000, id='resizes_on_change'),
            pytest.param(str(DEFAULT_PGSS_MAX), DEFAULT_PGSS_MAX, DEFAULT_PGSS_MAX, id='unchanged_when_equal'),
            pytest.param(None, 9999, DEFAULT_PGSS_MAX, id='uses_default_when_absent'),
        ],
    )
    def test_sync_cache_sizes(self, pg_setting, initial_maxsize, expected_maxsize):
        """_sync_cache_sizes reconciles _obfuscation_lookup._maxsize with the live pg setting."""
        v2 = self._make()
        v2._check.pg_settings = {'pg_stat_statements.max': pg_setting} if pg_setting is not None else {}
        v2._obfuscation_lookup._maxsize = initial_maxsize
        v2._sync_cache_sizes()
        assert v2._obfuscation_lookup._maxsize == expected_maxsize

    # --- zero-derivative short-circuit ---

    def test_collect_metrics_rows_returns_empty_for_unchanged_snapshot(self):
        """When snapshot rows are present but no counter changed, _collect_metrics_rows returns []."""
        v2 = self._make()
        snapshot = [{'queryid': 1, 'dbid': 1, 'userid': 1, 'datname': 'db', 'rolname': 'r', 'calls': 10}]

        with (
            mock.patch.object(v2, '_emit_pg_stat_statements_metrics'),
            mock.patch.object(v2, '_emit_pg_stat_statements_dealloc'),
            mock.patch.object(v2, '_emit_pg_stat_statements_max_warning'),
            mock.patch.object(v2, '_sync_cache_sizes'),
            mock.patch.object(v2, '_load_lightweight_snapshot', return_value=snapshot),
        ):
            # First call: seeds DeltaDetector (no previous) → no derivatives
            assert v2._collect_metrics_rows() == []
            # Second call: identical snapshot, zero counter change → no derivatives
            assert v2._collect_metrics_rows() == []

        # Delta gauges were still emitted with value 0 on both calls
        derivative_gauge_calls = [
            c
            for c in v2._check.gauge.call_args_list
            if c[0][0] == 'dd.postgres.statement_metrics.delta.derivative_rows'
        ]
        assert all(c[0][1] == 0 for c in derivative_gauge_calls)

    # --- track_io_timing column exclusion ---

    @pytest.mark.parametrize(
        "track_io_timing, timing_cols_expected",
        [
            pytest.param('on', True, id='included_when_on'),
            pytest.param('off', False, id='excluded_when_off'),
        ],
    )
    def test_load_lightweight_snapshot_timing_columns(self, track_io_timing, timing_cols_expected):
        """Timing columns are projected only when track_io_timing='on'."""
        v2 = self._make()
        v2._check.pg_settings = {'track_io_timing': track_io_timing}
        all_columns = list(
            LIGHTWEIGHT_DESIRED_COLUMNS | PG_STAT_STATEMENTS_TIMING_COLUMNS | PG_STAT_STATEMENTS_TIMING_COLUMNS_LT_17
        )
        captured: dict = {}

        def capture_execute(query, params=(), row_factory=None):
            captured['query'] = query
            return [], None

        with (
            mock.patch.object(v2, '_get_pg_stat_statements_columns', return_value=all_columns),
            mock.patch.object(v2, '_execute_query', side_effect=capture_execute),
        ):
            v2._load_lightweight_snapshot()

        assert 'query' in captured
        timing_cols = PG_STAT_STATEMENTS_TIMING_COLUMNS | PG_STAT_STATEMENTS_TIMING_COLUMNS_LT_17
        for col in timing_cols:
            if timing_cols_expected:
                assert col in captured['query'], f"{col!r} should be projected when track_io_timing=on"
            else:
                assert col not in captured['query'], f"{col!r} should be excluded when track_io_timing=off"
