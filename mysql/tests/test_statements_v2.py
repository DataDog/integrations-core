# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for the V2 statement metrics layers (DeltaDetector, ObfuscationLookup, MySQLStatementMetricsV2)."""

import logging
import time
from concurrent.futures.thread import ThreadPoolExecutor

import mock
import pymysql
import pytest

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.serialization import json
from datadog_checks.mysql import MySql
from datadog_checks.mysql.delta_detector import DeltaDetector
from datadog_checks.mysql.obfuscation_lookup import ObfuscationLookup
from datadog_checks.mysql.statements import METRICS_COLUMNS, MySQLStatementMetrics
from datadog_checks.mysql.statements_v2 import (
    DEFAULT_DIGESTS_SIZE,
    MySQLStatementMetricsV2,
    _digest_delta_key,
    _prepared_delta_key,
)

from . import common

pytestmark = pytest.mark.unit

CLOSE_TO_ZERO_INTERVAL = 0.0000001

METRIC_COLS = frozenset({'count_star', 'sum_timer_wait', 'sum_rows_sent'})


@pytest.fixture
def dbm_instance(instance_complex):
    instance_complex['dbm'] = True
    instance_complex['disable_generic_tags'] = False
    instance_complex['query_samples'] = {'enabled': False}
    instance_complex['query_metrics'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': CLOSE_TO_ZERO_INTERVAL,
        'incremental_query_metrics': True,
    }
    instance_complex['query_activity'] = {'enabled': False}
    instance_complex['collect_settings'] = {'enabled': False}
    return instance_complex


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


# ---------------------------------------------------------------------------
# DeltaDetector
# ---------------------------------------------------------------------------


class TestDeltaDetector:
    def _make(self, key=_digest_delta_key, execution_indicators=frozenset({'count_star'})):
        return DeltaDetector(metric_columns=METRIC_COLS, key=key, execution_indicators=execution_indicators)

    def _row(self, digest, schema_name='testdb', **counters):
        row = {
            'schema_name': schema_name,
            'digest': digest,
            'count_star': 0,
            'sum_timer_wait': 0,
            'sum_rows_sent': 0,
            'last_seen': '2026-01-01 00:00:00',
        }
        row.update(counters)
        return row

    def test_first_cycle_returns_no_derivatives(self):
        dd = self._make()
        result = dd.compute([self._row('d1', count_star=10, sum_rows_sent=100)])
        assert result.derivative_rows == []
        assert result.changed_keys == set()

    def test_second_cycle_returns_derivatives_for_changed_rows(self):
        dd = self._make()
        dd.compute([self._row('d1', count_star=10, sum_rows_sent=100)])
        result = dd.compute([self._row('d1', count_star=15, sum_rows_sent=150)])

        assert len(result.derivative_rows) == 1
        derivative = result.derivative_rows[0]
        assert derivative['count_star'] == 5
        assert derivative['sum_rows_sent'] == 50
        # Non-metric columns are passed through untouched.
        assert derivative['digest'] == 'd1'
        assert derivative['schema_name'] == 'testdb'
        assert result.changed_keys == {('testdb', 'd1')}

    def test_unchanged_rows_are_not_emitted(self):
        dd = self._make()
        dd.compute([self._row('d1', count_star=10), self._row('d2', count_star=20)])
        result = dd.compute([self._row('d1', count_star=10), self._row('d2', count_star=25)])
        assert [row['digest'] for row in result.derivative_rows] == ['d2']

    def test_negative_diff_discards_row(self):
        dd = self._make()
        dd.compute([self._row('d1', count_star=10, sum_rows_sent=100)])
        result = dd.compute([self._row('d1', count_star=5, sum_rows_sent=50)])
        assert result.derivative_rows == []

    def test_execution_indicator_required(self):
        """A row whose count_star is flat did not execute, whatever the other counters say."""
        dd = self._make()
        dd.compute([self._row('d1', count_star=10, sum_timer_wait=100)])
        result = dd.compute([self._row('d1', count_star=10, sum_timer_wait=200)])
        assert result.derivative_rows == []

    def test_new_key_is_baselined_not_emitted(self):
        dd = self._make()
        dd.compute([self._row('d1', count_star=10)])
        result = dd.compute([self._row('d1', count_star=15), self._row('d2', count_star=5000)])
        assert result.changed_keys == {('testdb', 'd1')}

    def test_vanished_keys_detected(self):
        dd = self._make()
        dd.compute([self._row('d1', count_star=10), self._row('d2', count_star=20)])
        result = dd.compute([self._row('d1', count_star=15)])
        assert result.vanished_keys == {('testdb', 'd2')}

    def test_same_digest_in_different_schemas_are_separate_series(self):
        """The digest table aggregates per (schema, digest), so each pair keeps its own baseline."""
        dd = self._make()
        dd.compute([self._row('d1', schema_name='a', count_star=10), self._row('d1', schema_name='b', count_star=10)])
        result = dd.compute(
            [self._row('d1', schema_name='a', count_star=15), self._row('d1', schema_name='b', count_star=10)]
        )
        assert result.changed_keys == {('a', 'd1')}
        assert result.derivative_rows[0]['count_star'] == 5

    def test_rows_sharing_a_key_are_summed(self):
        dd = self._make()
        dd.compute([self._row('d1', count_star=10, sum_rows_sent=100)])
        result = dd.compute(
            [self._row('d1', count_star=8, sum_rows_sent=60), self._row('d1', count_star=7, sum_rows_sent=55)]
        )
        assert len(result.derivative_rows) == 1
        assert result.derivative_rows[0]['count_star'] == 5
        assert result.derivative_rows[0]['sum_rows_sent'] == 15

    def test_collapse_does_not_mutate_input_rows(self):
        dd = self._make()
        rows = [self._row('d1', count_star=8), self._row('d1', count_star=7)]
        dd.compute(rows)
        assert [row['count_star'] for row in rows] == [8, 7]

    def test_reset_clears_state(self):
        dd = self._make()
        dd.compute([self._row('d1', count_star=10)])
        dd.reset()
        assert dd.compute([self._row('d1', count_star=15)]).derivative_rows == []

    def test_prepared_key_includes_signature(self):
        """A recycled object_instance_begin carrying different text must not diff against the old series."""
        dd = self._make(key=_prepared_delta_key)

        def row(instance_id, signature, count_star):
            return {
                'schema_name': 'testdb',
                'digest': None,
                '_dd_statement_id': instance_id,
                'query_signature': signature,
                'count_star': count_star,
                'sum_timer_wait': 0,
                'sum_rows_sent': 0,
            }

        dd.compute([row(1001, 'sig-a', 100)])
        result = dd.compute([row(1001, 'sig-b', 5000)])
        assert result.derivative_rows == []


# ---------------------------------------------------------------------------
# ObfuscationLookup
# ---------------------------------------------------------------------------


class TestObfuscationLookup:
    def _make(self, maxsize=100):
        return ObfuscationLookup(maxsize=maxsize, obfuscate_options='{}')

    def test_empty_lookup_all_misses(self):
        lk = self._make()
        hits, misses = lk.lookup({'d1', 'd2', 'd3'})
        assert hits == {}
        assert misses == {'d1', 'd2', 'd3'}

    def test_populate_then_lookup(self):
        lk = self._make()
        results, failures = lk.populate({'d1': 'SELECT 1', 'd2': 'SELECT 2'})
        assert failures == set()
        assert set(results) == {'d1', 'd2'}

        hits, misses = lk.lookup({'d1', 'd2', 'd3'})
        assert set(hits) == {'d1', 'd2'}
        assert misses == {'d3'}
        assert hits['d1'].obfuscated_statement is not None
        assert hits['d1'].query_signature is not None

    def test_hit_and_miss_counters(self):
        lk = self._make()
        lk.populate({'d1': 'SELECT 1'})
        lk.reset_stats()
        lk.lookup({'d1', 'd2'})
        assert lk.hits == 1
        assert lk.misses == 1

    def test_evict_removes_digest(self):
        lk = self._make()
        lk.populate({'d1': 'SELECT 1', 'd2': 'SELECT 2'})
        lk.evict({'d1'})
        hits, misses = lk.lookup({'d1', 'd2'})
        assert misses == {'d1'}
        assert 'd2' in hits

    def test_multiple_digests_share_signature(self):
        """Digests that normalize to one statement share a single cached result."""
        lk = self._make()
        lk.populate({'d1': 'SELECT 1', 'd2': 'SELECT 1'})
        hits, _ = lk.lookup({'d1', 'd2'})
        assert hits['d1'].query_signature == hits['d2'].query_signature
        assert lk.digest_map_size == 2
        assert lk.signature_map_size == 1

    def test_evict_does_not_remove_shared_signature(self):
        lk = self._make()
        lk.populate({'d1': 'SELECT 1', 'd2': 'SELECT 1'})
        lk.evict({'d1'})
        hits, _ = lk.lookup({'d2'})
        assert 'd2' in hits

    def test_lru_eviction_on_max_size(self):
        lk = self._make(maxsize=2)
        lk.populate({'d1': 'SELECT 1', 'd2': 'SELECT 2', 'd3': 'SELECT 3'})
        assert lk.digest_map_size == 2
        _, misses = lk.lookup({'d1'})
        assert misses == {'d1'}

    def test_lookup_updates_lru_order(self):
        lk = self._make(maxsize=2)
        lk.populate({'d1': 'SELECT 1', 'd2': 'SELECT 2'})
        lk.lookup({'d1'})
        lk.populate({'d3': 'SELECT 3'})
        hits, _ = lk.lookup({'d1'})
        assert 'd1' in hits
        _, misses = lk.lookup({'d2'})
        assert misses == {'d2'}

    def test_maxsize_setter_trims_immediately(self):
        lk = self._make(maxsize=10)
        lk.populate({'d1': 'SELECT 1', 'd2': 'SELECT 2', 'd3': 'SELECT 3'})
        lk.mark_ignored({'i1', 'i2', 'i3'})
        lk.maxsize = 1
        assert lk.maxsize == 1
        assert lk.digest_map_size == 1
        assert lk.signature_map_size == 1
        assert lk.ignored_map_size == 1

    def test_maxsize_setter_growing_does_not_evict(self):
        lk = self._make(maxsize=2)
        lk.populate({'d1': 'SELECT 1', 'd2': 'SELECT 2'})
        lk.maxsize = 100
        assert lk.digest_map_size == 2

    # --- negative cache (ignored digests) ---

    def test_mark_ignored_excludes_from_hits_and_misses(self):
        lk = self._make()
        lk.mark_ignored({'d1'})
        hits, misses = lk.lookup({'d1', 'd2'})
        assert 'd1' not in hits
        assert misses == {'d2'}
        assert lk.ignored_map_size == 1

    def test_ignored_digests_do_not_move_counters(self):
        lk = self._make()
        lk.mark_ignored({'d1'})
        lk.reset_stats()
        lk.lookup({'d1'})
        assert lk.hits == 0
        assert lk.misses == 0

    def test_evict_forgets_ignored_digest(self):
        lk = self._make()
        lk.mark_ignored({'d1'})
        lk.evict({'d1'})
        assert lk.ignored_map_size == 0
        _, misses = lk.lookup({'d1'})
        assert misses == {'d1'}

    def test_ignored_digests_lru_trimmed_to_maxsize(self):
        lk = self._make(maxsize=2)
        lk.mark_ignored({'d1', 'd2', 'd3'})
        assert lk.ignored_map_size == 2

    def test_mark_ignored_drops_stale_positive_mapping(self):
        """An ignored digest must not resurface as a hit via a stale tier-1 mapping."""
        lk = self._make()
        lk.populate({'d1': 'SELECT 1', 'd2': 'SELECT 1'})
        lk.mark_ignored({'d1'})
        hits, misses = lk.lookup({'d1'})
        assert 'd1' not in hits
        assert 'd1' not in misses

    def test_populate_reports_obfuscation_failures(self, datadog_agent):
        """A digest whose text cannot be obfuscated is reported so the caller can negative-cache it."""
        lk = self._make()
        with mock.patch.object(datadog_agent, 'obfuscate_sql', side_effect=Exception('boom')):
            results, failures = lk.populate({'d1': 'SELECT 1'})
        assert results == {}
        assert failures == {'d1'}


# ---------------------------------------------------------------------------
# MySQLStatementMetricsV2
# ---------------------------------------------------------------------------


NORMALIZED_QUERY = 'SELECT * FROM `employees` WHERE `id` = ?'
QUERY_SIGNATURE = compute_sql_signature(NORMALIZED_QUERY)


def _snapshot_row(digest, count_star, schema_name='testdb'):
    row = {
        'schema_name': schema_name,
        'digest': digest,
        'last_seen': '2026-01-01 00:00:00',
    }
    row.update(dict.fromkeys(METRICS_COLUMNS, 0))
    row['count_star'] = count_star
    return row


def _prepared_row(instance_id, count_star, sql_text='SELECT * FROM employees WHERE id = ?', schema_name='testdb'):
    row = {
        '_dd_statement_id': instance_id,
        'schema_name': schema_name,
        'digest': None,
        'digest_text': sql_text,
        'last_seen': '2026-01-01 00:00:00',
    }
    row.update(dict.fromkeys(METRICS_COLUMNS, 0))
    row['count_star'] = count_star
    return row


class TestMySQLStatementMetricsV2:
    @pytest.fixture(autouse=True)
    def _obfuscate(self, datadog_agent):
        """Route the obfuscator FFI to a stub and expose the call count to tests."""
        with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
            mock_agent.side_effect = lambda query, options=None: json.dumps({'query': NORMALIZED_QUERY, 'metadata': {}})
            self.obfuscate_sql = mock_agent
            yield mock_agent

    def _make(self, dbm_instance):
        check = MySql(common.CHECK_NAME, {}, [dbm_instance])
        job = check._statement_metrics
        job._collect_prepared_statements = False
        return check, job

    def test_check_selects_v2_when_flag_enabled(self, dbm_instance):
        check = MySql(common.CHECK_NAME, {}, [dbm_instance])
        assert isinstance(check._statement_metrics, MySQLStatementMetricsV2)

    def test_check_selects_v1_by_default(self, dbm_instance):
        del dbm_instance['query_metrics']['incremental_query_metrics']
        check = MySql(common.CHECK_NAME, {}, [dbm_instance])
        assert isinstance(check._statement_metrics, MySQLStatementMetrics)
        assert not isinstance(check._statement_metrics, MySQLStatementMetricsV2)

    def test_first_cycle_baselines_and_emits_nothing(self, dbm_instance):
        _, job = self._make(dbm_instance)
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', return_value=[_snapshot_row('d1', 100)]),
            mock.patch.object(job, '_fetch_digest_texts', return_value={}) as fetch,
        ):
            assert job._collect_per_statement_metrics([]) == []
        # Nothing executed during the interval, so no text is fetched at all.
        fetch.assert_not_called()

    def test_second_cycle_emits_only_changed_digests(self, dbm_instance):
        _, job = self._make(dbm_instance)
        snapshots = iter(
            [
                [_snapshot_row('d1', 100), _snapshot_row('d2', 200)],
                [_snapshot_row('d1', 110), _snapshot_row('d2', 200)],
            ]
        )
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}) as fetch,
        ):
            assert job._collect_per_statement_metrics([]) == []
            rows = job._collect_per_statement_metrics([])

        # d2 was flat, so its text is never requested or obfuscated.
        assert fetch.call_args[0][0] == {'d1'}
        assert len(rows) == 1
        assert rows[0]['count_star'] == 10
        assert rows[0]['query_signature'] == QUERY_SIGNATURE
        assert rows[0]['digest_text'] == NORMALIZED_QUERY

    def test_cached_digest_is_not_refetched_or_reobfuscated(self, dbm_instance):
        _, job = self._make(dbm_instance)
        snapshots = iter(
            [
                [_snapshot_row('d1', 100)],
                [_snapshot_row('d1', 110)],
                [_snapshot_row('d1', 120)],
            ]
        )
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}) as fetch,
        ):
            job._collect_per_statement_metrics([])
            job._collect_per_statement_metrics([])
            obfuscate_calls_after_first_resolve = self.obfuscate_sql.call_count
            rows = job._collect_per_statement_metrics([])

        assert fetch.call_count == 1
        assert self.obfuscate_sql.call_count == obfuscate_calls_after_first_resolve
        assert rows[0]['count_star'] == 10

    def test_one_digest_across_schemas_is_obfuscated_once(self, dbm_instance):
        """digest_text is a function of the digest, so schemas sharing a digest share a cache entry."""
        _, job = self._make(dbm_instance)
        schemas = ('a', 'b', 'c')
        snapshots = iter(
            [
                [_snapshot_row('d1', 100, schema_name=s) for s in schemas],
                [_snapshot_row('d1', 110, schema_name=s) for s in schemas],
            ]
        )
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}) as fetch,
        ):
            job._collect_per_statement_metrics([])
            self.obfuscate_sql.reset_mock()
            rows = job._collect_per_statement_metrics([])

        assert fetch.call_args[0][0] == {'d1'}
        assert self.obfuscate_sql.call_count == 1
        # Each schema still reports its own row.
        assert len(rows) == 3
        assert {row['schema_name'] for row in rows} == set(schemas)

    def test_explain_digests_are_fetched_once_then_skipped(self, dbm_instance):
        """EXPLAIN text can only be recognized after resolution, so it is negative-cached."""
        _, job = self._make(dbm_instance)
        snapshots = iter(
            [
                [_snapshot_row('d1', 100)],
                [_snapshot_row('d1', 110)],
                [_snapshot_row('d1', 120)],
            ]
        )
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'EXPLAIN SELECT 1'}) as fetch,
        ):
            job._collect_per_statement_metrics([])
            assert job._collect_per_statement_metrics([]) == []
            assert job._collect_per_statement_metrics([]) == []

        assert fetch.call_count == 1
        assert 'd1' in job._obfuscation_lookup._ignored_digests

    def test_obfuscation_failures_are_negative_cached(self, dbm_instance):
        """A digest's text never changes, so a failed obfuscation is never retried."""
        _, job = self._make(dbm_instance)
        snapshots = iter(
            [
                [_snapshot_row('d1', 100)],
                [_snapshot_row('d1', 110)],
                [_snapshot_row('d1', 120)],
            ]
        )
        self.obfuscate_sql.side_effect = Exception('boom')
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}) as fetch,
        ):
            job._collect_per_statement_metrics([])
            assert job._collect_per_statement_metrics([]) == []
            assert job._collect_per_statement_metrics([]) == []

        assert fetch.call_count == 1
        assert 'd1' in job._obfuscation_lookup._ignored_digests

    def test_digest_is_kept_while_live_in_another_schema(self, dbm_instance):
        _, job = self._make(dbm_instance)
        snapshots = iter(
            [
                [_snapshot_row('d1', 100, schema_name='a'), _snapshot_row('d1', 100, schema_name='b')],
                [_snapshot_row('d1', 110, schema_name='b')],
            ]
        )
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}),
        ):
            job._collect_per_statement_metrics([])
            job._collect_per_statement_metrics([])

        # Schema 'a' vanished but 'b' still runs the digest, so the cached text survives.
        assert 'd1' in job._obfuscation_lookup._digest_to_sig

    def test_fully_vanished_digest_is_evicted(self, dbm_instance):
        _, job = self._make(dbm_instance)
        snapshots = iter(
            [
                [_snapshot_row('d1', 100), _snapshot_row('d2', 100)],
                [_snapshot_row('d1', 110), _snapshot_row('d2', 110)],
                [_snapshot_row('d1', 120)],
            ]
        )
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1', 'd2': 'SELECT 2'}),
        ):
            job._collect_per_statement_metrics([])
            job._collect_per_statement_metrics([])
            assert 'd2' in job._obfuscation_lookup._digest_to_sig
            job._collect_per_statement_metrics([])

        assert 'd2' not in job._obfuscation_lookup._digest_to_sig

    def test_lookup_gauges_report_hit_rate(self, dbm_instance):
        check, job = self._make(dbm_instance)
        snapshots = iter(
            [
                [_snapshot_row('d1', 100)],
                [_snapshot_row('d1', 110)],
                [_snapshot_row('d1', 120)],
            ]
        )
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}),
            mock.patch.object(check, 'gauge') as gauge,
        ):
            job._collect_per_statement_metrics([])
            job._collect_per_statement_metrics([])
            job._collect_per_statement_metrics([])

        def values(name):
            return [call[0][1] for call in gauge.call_args_list if call[0][0] == name]

        # Cycle 1 resolves nothing; cycle 2 misses on the cold cache; cycle 3 hits.
        assert values('dd.mysql.statement_metrics.lookup.misses') == [1, 0]
        assert values('dd.mysql.statement_metrics.lookup.hits') == [0, 1]
        assert values('dd.mysql.statement_metrics.delta.changed_digests') == [0, 1, 1]
        assert values('dd.mysql.statement_metrics.delta.derivative_rows') == [0, 1, 1]

    def test_prepared_statements_merge_with_digest_rows(self, dbm_instance):
        _, job = self._make(dbm_instance)
        job._collect_prepared_statements = True
        snapshots = iter([[_snapshot_row('d1', 100)], [_snapshot_row('d1', 110)]])
        prepared = iter([[_prepared_row(1001, 100)], [_prepared_row(1001, 105)]])

        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_query_prepared_statements', side_effect=prepared),
            mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}),
        ):
            assert job._collect_per_statement_metrics([]) == []
            rows = job._collect_per_statement_metrics([])

        # Both sources normalize to the same signature and schema, so they merge into one row.
        assert len(rows) == 1
        assert rows[0]['query_signature'] == QUERY_SIGNATURE
        assert rows[0]['count_star'] == 15
        assert '_dd_statement_id' not in rows[0]

    def test_prepared_statements_skipped_when_disabled(self, dbm_instance):
        _, job = self._make(dbm_instance)
        snapshots = iter([[_snapshot_row('d1', 100)], [_snapshot_row('d1', 110)]])
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_query_prepared_statements') as prepared,
            mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}),
        ):
            job._collect_per_statement_metrics([])
            job._collect_per_statement_metrics([])
        prepared.assert_not_called()

    def test_unresolvable_digest_is_dropped_from_output(self, dbm_instance):
        """A digest whose text cannot be fetched produces no row rather than an unlabeled one."""
        _, job = self._make(dbm_instance)
        snapshots = iter([[_snapshot_row('d1', 100)], [_snapshot_row('d1', 110)]])
        with (
            mock.patch.object(job, '_get_statement_count'),
            mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
            mock.patch.object(job, '_fetch_digest_texts', return_value={}),
        ):
            job._collect_per_statement_metrics([])
            assert job._collect_per_statement_metrics([]) == []

    @pytest.mark.parametrize(
        "digests_size, expected_maxsize",
        [
            pytest.param('20000', 20000, id='uses_reported_size'),
            pytest.param('-1', DEFAULT_DIGESTS_SIZE, id='falls_back_when_autosized'),
            pytest.param(None, DEFAULT_DIGESTS_SIZE, id='falls_back_when_absent'),
            pytest.param('not-a-number', DEFAULT_DIGESTS_SIZE, id='falls_back_when_unparseable'),
        ],
    )
    def test_sync_cache_sizes(self, dbm_instance, digests_size, expected_maxsize):
        check, job = self._make(dbm_instance)
        check.global_variables._variables = (
            {'performance_schema_digests_size': digests_size} if digests_size is not None else {}
        )
        job._sync_cache_sizes()
        assert job._obfuscation_lookup.maxsize == expected_maxsize

    def test_fqt_events_emitted_once_per_signature(self, dbm_instance):
        _, job = self._make(dbm_instance)
        rows = [
            {
                'schema_name': 'testdb',
                'query_signature': QUERY_SIGNATURE,
                'digest_text': NORMALIZED_QUERY,
                'dd_tables': ['employees'],
                'dd_commands': ['SELECT'],
                'dd_comments': None,
            }
        ]
        assert len(list(job._rows_to_fqt_events(rows, []))) == 1
        assert list(job._rows_to_fqt_events(rows, [])) == []

    def test_only_query_recent_statements_warns(self, dbm_instance, caplog):
        dbm_instance['query_metrics']['only_query_recent_statements'] = True
        caplog.set_level(logging.WARNING, logger="datadog_checks")
        MySql(common.CHECK_NAME, {}, [dbm_instance])
        assert 'only_query_recent_statements has no effect' in caplog.text

    def test_digest_text_fetch_is_batched(self, dbm_instance):
        _, job = self._make(dbm_instance)
        digests = {'d{}'.format(i) for i in range(1200)}
        cursor = mock.MagicMock()
        cursor.fetchall.return_value = []
        connection = mock.MagicMock()
        connection.cursor.return_value = cursor

        with mock.patch.object(job, '_get_db_connection', return_value=connection):
            job._fetch_digest_texts(digests)

        batch_sizes = [len(call[0][1]) for call in cursor.execute.call_args_list]
        assert batch_sizes == [500, 500, 200]
        # Every statement binds exactly as many placeholders as it passes parameters.
        for call in cursor.execute.call_args_list:
            statement, params = call[0]
            assert statement.count('%s') == len(params)

    def test_digest_text_fetch_returns_partial_result_on_error(self, dbm_instance):
        """A failed batch leaves its digests unresolved instead of losing the whole cycle."""
        _, job = self._make(dbm_instance)
        cursor = mock.MagicMock()
        cursor.execute.side_effect = [None, pymysql.err.OperationalError('gone')]
        cursor.fetchall.return_value = [{'digest': 'd1', 'digest_text': 'SELECT 1'}]
        connection = mock.MagicMock()
        connection.cursor.return_value = cursor

        with mock.patch.object(job, '_get_db_connection', return_value=connection):
            texts = job._fetch_digest_texts({'d{}'.format(i) for i in range(600)})

        assert texts == {'d1': 'SELECT 1'}

    def test_performance_schema_disabled_records_warning(self, dbm_instance):
        check, job = self._make(dbm_instance)
        check.global_variables._variables = {'performance_schema': 'OFF'}
        with mock.patch.object(job, '_collect_per_statement_metrics') as collect:
            job.collect_per_statement_metrics()
        collect.assert_not_called()
        assert check._warnings_by_code


# ---------------------------------------------------------------------------
# Payload parity between v1 and v2
# ---------------------------------------------------------------------------


def test_v2_row_shape_matches_v1(dbm_instance, datadog_agent):
    """The rows the two collectors hand to the payload carry the same keys."""
    v1_instance = dict(dbm_instance)
    v1_instance['query_metrics'] = dict(dbm_instance['query_metrics'])
    del v1_instance['query_metrics']['incremental_query_metrics']

    v1_check = MySql(common.CHECK_NAME, {}, [v1_instance])
    v2_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    def v1_row(count_star):
        row = {
            '_dd_statement_id': None,
            'schema_name': 'testdb',
            'digest': 'd1',
            'digest_text': 'SELECT * FROM employees WHERE id = ?',
            'last_seen': time.time(),
        }
        row.update(dict.fromkeys(METRICS_COLUMNS, 0))
        row['count_star'] = count_star
        return row

    with (
        mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent,
        mock.patch.object(v1_check._statement_metrics, '_get_statement_count'),
        mock.patch.object(
            v1_check._statement_metrics,
            '_query_summary_per_statement',
            side_effect=iter([[v1_row(100)], [v1_row(110)]]),
        ),
        mock.patch.object(v2_check._statement_metrics, '_get_statement_count'),
        mock.patch.object(
            v2_check._statement_metrics,
            '_query_digest_snapshot',
            side_effect=iter([[_snapshot_row('d1', 100)], [_snapshot_row('d1', 110)]]),
        ),
        mock.patch.object(
            v2_check._statement_metrics,
            '_fetch_digest_texts',
            return_value={'d1': 'SELECT * FROM employees WHERE id = ?'},
        ),
    ):
        mock_agent.side_effect = lambda query, options=None: json.dumps({'query': NORMALIZED_QUERY, 'metadata': {}})
        v2_check._statement_metrics._collect_prepared_statements = False

        v1_check._statement_metrics._collect_per_statement_metrics([])
        v1_rows = v1_check._statement_metrics._collect_per_statement_metrics([])
        v2_check._statement_metrics._collect_per_statement_metrics([])
        v2_rows = v2_check._statement_metrics._collect_per_statement_metrics([])

    assert len(v1_rows) == len(v2_rows) == 1
    assert set(v1_rows[0]) == set(v2_rows[0])
    assert v1_rows[0]['query_signature'] == v2_rows[0]['query_signature']
    assert v1_rows[0]['count_star'] == v2_rows[0]['count_star'] == 10
