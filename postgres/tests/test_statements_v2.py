# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for PostgresStatementMetricsV2.

The diffing and caching primitives it builds on are covered in
``datadog_checks_base/tests/base/utils/db/query_metrics/``; what belongs here is the Postgres
specifics layered on top and the wiring between them.
"""

import json
from unittest import mock

import pytest
from semver import VersionInfo

from datadog_checks.base.utils.db.query_metrics import TextKind
from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.config import build_config
from datadog_checks.postgres.statements import (
    PG_STAT_STATEMENTS_TIMING_COLUMNS,
    PG_STAT_STATEMENTS_TIMING_COLUMNS_LT_17,
)
from datadog_checks.postgres.statements_v2 import (
    DEFAULT_PGSS_MAX,
    LIGHTWEIGHT_DESIRED_COLUMNS,
    PostgresStatementMetricsV2,
    classify_query_text,
)


@pytest.mark.parametrize(
    "text, expected_kind",
    [
        pytest.param('/* DDIGNORE */ SELECT secret', TextKind.EXCLUDED, id='ddignore'),
        pytest.param('<insufficient privilege>', TextKind.UNAVAILABLE, id='insufficient_privilege'),
        pytest.param('SELECT city FROM persons', TextKind.STATEMENT, id='ordinary_statement'),
    ],
)
def test_classify_query_text(text, expected_kind):
    """The kind a text maps to decides whether the resolver ever asks for that key again.

    EXCLUDED is a permanent verdict, so misclassifying a privilege error as excluded would drop the
    statement forever once the grant arrives; the reverse would re-fetch the Agent's own queries on
    every cycle. The shared resolver's tests use a stand-in classifier, so this mapping is only
    pinned here.
    """
    assert classify_query_text(text) is expected_kind


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

    # --- resolver wiring ---

    def test_resolve_obfuscations_applies_the_postgres_classifier(self):
        """The collector hands its own fetcher and classifier to the shared resolver.

        One call covering both a sentinel and an ordinary statement shows the classifier reaching the
        resolver per key; how each kind is then cached or retried belongs to the resolver's own tests.
        """
        v2 = self._make()
        bad_key = (1, 1, 1)
        good_key = (2, 1, 1)
        keys = {bad_key, good_key}
        with mock.patch.object(
            v2,
            '_fetch_query_texts',
            return_value={bad_key: '<insufficient privilege>', good_key: 'SELECT 1'},
        ):
            result = v2._resolve_obfuscations(keys, keys)
        assert bad_key not in result
        assert good_key in result

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
        """_sync_cache_sizes reconciles the cache bound with the live pg_stat_statements.max setting."""
        v2 = self._make()
        v2._check.pg_settings = {'pg_stat_statements.max': pg_setting} if pg_setting is not None else {}
        v2._obfuscation_lookup.maxsize = initial_maxsize
        v2._sync_cache_sizes()
        assert v2._obfuscation_lookup.maxsize == expected_maxsize

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
            # First call: seeds the counter baseline (no previous) → no derivatives
            assert v2._collect_metrics_rows() == []
            # Second call: identical snapshot, zero counter change → no derivatives
            assert v2._collect_metrics_rows() == []

        gauge_names = [c[0][0] for c in v2._check.gauge.call_args_list]

        # Delta gauges were still emitted with value 0 on both calls
        derivative_gauge_calls = [
            c
            for c in v2._check.gauge.call_args_list
            if c[0][0] == 'dd.postgres.statement_metrics.delta.derivative_rows'
        ]
        assert all(c[0][1] == 0 for c in derivative_gauge_calls)

        # Resolution still ran, which is what prunes cache entries for statements that have left
        # pg_stat_statements; skipping it on quiet cycles would let the cache grow unbounded.
        assert gauge_names.count('dd.postgres.statement_metrics.lookup.dropped') == 2

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
