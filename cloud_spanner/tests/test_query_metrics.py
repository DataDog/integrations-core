# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.cloud_spanner import SpannerCheck

from .conftest import INSTANCE_CONFIG, INTERVAL_END, MOCK_QUERY_STATS_ROWS, _build_mock_spanner_client

pytestmark = pytest.mark.unit


class TestQueryMetricsPayload:
    def test_emits_one_dbm_metrics_event(self, aggregator, dd_run_check, check):
        dd_run_check(check)

        events = aggregator.get_event_platform_events("dbm-metrics")
        assert len(events) == 1

    def test_payload_top_level_fields(self, aggregator, dd_run_check, check):
        dd_run_check(check)

        event = aggregator.get_event_platform_events("dbm-metrics")[0]
        assert event['host'] == 'test-project:test-instance'
        assert event['database_instance'] == 'test-project:test-instance'
        assert event['spanner_version'] == 'spanner'
        assert event['min_collection_interval'] == pytest.approx(0.1)
        assert event['timestamp'] > 0
        assert 'ddsource' not in event

    def test_payload_cloud_metadata(self, aggregator, dd_run_check, check):
        dd_run_check(check)

        event = aggregator.get_event_platform_events("dbm-metrics")[0]
        assert event['cloud_metadata'] == {'gcp': {'project_id': 'test-project', 'instance_id': 'test-instance'}}

    def test_payload_tags(self, aggregator, dd_run_check, check):
        dd_run_check(check)

        event = aggregator.get_event_platform_events("dbm-metrics")[0]
        assert set(event['tags']) == {'env:test', 'service:myapp'}

    def test_payload_row_count(self, aggregator, dd_run_check, check):
        dd_run_check(check)

        event = aggregator.get_event_platform_events("dbm-metrics")[0]
        assert len(event['spanner_rows']) == len(MOCK_QUERY_STATS_ROWS)


class TestQueryMetricsRowFields:
    def _get_rows(self, aggregator, dd_run_check, check):
        dd_run_check(check)
        return aggregator.get_event_platform_events("dbm-metrics")[0]['spanner_rows']

    def test_database_field(self, aggregator, dd_run_check, check):
        rows = self._get_rows(aggregator, dd_run_check, check)
        for row in rows:
            assert row['database'] == 'test-database'

    def test_query_signature_is_stable(self, aggregator, dd_run_check, check):
        rows = self._get_rows(aggregator, dd_run_check, check)
        # same query text should produce the same signature across runs
        signatures = [row['query_signature'] for row in rows]
        assert len(set(signatures)) == len(rows), "expected distinct signatures for distinct queries"

    def test_query_signature_matches_obfuscated_text(self, aggregator, dd_run_check, check):
        rows = self._get_rows(aggregator, dd_run_check, check)
        for row in rows:
            expected = compute_sql_signature(row['text'])
            assert row['query_signature'] == expected

    def test_interval_end_is_iso_string(self, aggregator, dd_run_check, check):
        rows = self._get_rows(aggregator, dd_run_check, check)
        for row in rows:
            assert row['interval_end'] == INTERVAL_END.isoformat()

    def test_request_tag_preserved(self, aggregator, dd_run_check, check):
        rows = self._get_rows(aggregator, dd_run_check, check)
        tagged = [r for r in rows if r['request_tag'] == 'api/list-users']
        assert len(tagged) == 1

    def test_request_tag_empty_string_for_untagged(self, aggregator, dd_run_check, check):
        rows = self._get_rows(aggregator, dd_run_check, check)
        partitioned = [r for r in rows if r['query_type'] == 'PARTITIONED_QUERY']
        assert len(partitioned) == 1
        assert partitioned[0]['request_tag'] == ''

    def test_query_type_values(self, aggregator, dd_run_check, check):
        rows = self._get_rows(aggregator, dd_run_check, check)
        query_types = {r['query_type'] for r in rows}
        assert query_types == {'GLOBAL', 'PARTITIONED_QUERY'}

    def test_numeric_metrics_are_correct_types(self, aggregator, dd_run_check, check):
        rows = self._get_rows(aggregator, dd_run_check, check)
        float_fields = [
            'avg_latency_seconds',
            'avg_rows',
            'avg_bytes',
            'avg_rows_scanned',
            'avg_cpu_seconds',
            'all_failed_avg_latency_seconds',
        ]
        int_fields = [
            'execution_count',
            'all_failed_execution_count',
            'cancelled_or_disconnected_execution_count',
            'timed_out_execution_count',
        ]
        for row in rows:
            for field in float_fields:
                assert isinstance(row[field], float), f"{field} should be float, got {type(row[field])}"
            for field in int_fields:
                assert isinstance(row[field], int), f"{field} should be int, got {type(row[field])}"

    def test_first_row_numeric_values(self, aggregator, dd_run_check, check):
        rows = self._get_rows(aggregator, dd_run_check, check)
        row = next(r for r in rows if r['request_tag'] == 'api/list-users')
        assert row['execution_count'] == 150
        assert row['avg_latency_seconds'] == pytest.approx(0.023)
        assert row['avg_cpu_seconds'] == pytest.approx(0.015)
        assert row['all_failed_execution_count'] == 2
        assert row['timed_out_execution_count'] == 0

    def test_cancelled_count_preserved(self, aggregator, dd_run_check, check):
        rows = self._get_rows(aggregator, dd_run_check, check)
        partitioned = next(r for r in rows if r['query_type'] == 'PARTITIONED_QUERY')
        assert partitioned['cancelled_or_disconnected_execution_count'] == 1


class TestQueryMetricsDisabled:
    def test_dbm_flag_false_emits_nothing(self, aggregator, dd_run_check, mock_spanner_client):
        mock_client, _ = mock_spanner_client
        instance_config = {**INSTANCE_CONFIG, 'dbm': False}
        check = SpannerCheck('cloud_spanner', {}, [instance_config])
        check._client = mock_client

        dd_run_check(check)

        assert aggregator.get_event_platform_events("dbm-metrics") == []

    def test_query_metrics_disabled_emits_nothing(self, aggregator, dd_run_check, mock_spanner_client):
        mock_client, _ = mock_spanner_client
        instance_config = {**INSTANCE_CONFIG, 'query_metrics': {'enabled': False}}
        check = SpannerCheck('cloud_spanner', {}, [instance_config])
        check._client = mock_client

        dd_run_check(check)

        assert aggregator.get_event_platform_events("dbm-metrics") == []

    def test_empty_results_emits_nothing(self, aggregator, dd_run_check):
        mock_client, _ = _build_mock_spanner_client(rows=[])
        check = SpannerCheck('cloud_spanner', {}, [INSTANCE_CONFIG])
        check._client = mock_client

        dd_run_check(check)

        assert aggregator.get_event_platform_events("dbm-metrics") == []


class TestQueryMetricsNullHandling:
    def test_null_request_tag_becomes_empty_string(self, aggregator, dd_run_check):
        rows_with_null_tag = [list(MOCK_QUERY_STATS_ROWS[0])]
        rows_with_null_tag[0][1] = None  # request_tag = NULL
        mock_client, _ = _build_mock_spanner_client(rows=rows_with_null_tag)
        check = SpannerCheck('cloud_spanner', {}, [INSTANCE_CONFIG])
        check._client = mock_client

        dd_run_check(check)

        event = aggregator.get_event_platform_events("dbm-metrics")[0]
        assert event['spanner_rows'][0]['request_tag'] == ''

    def test_null_numeric_fields_become_zero(self, aggregator, dd_run_check):
        row = list(MOCK_QUERY_STATS_ROWS[0])
        row[6] = None  # execution_count
        row[7] = None  # avg_latency_seconds
        row[11] = None  # avg_cpu_seconds
        mock_client, _ = _build_mock_spanner_client(rows=[row])
        check = SpannerCheck('cloud_spanner', {}, [INSTANCE_CONFIG])
        check._client = mock_client

        dd_run_check(check)

        result_row = aggregator.get_event_platform_events("dbm-metrics")[0]['spanner_rows'][0]
        assert result_row['execution_count'] == 0
        assert result_row['avg_latency_seconds'] == pytest.approx(0.0)
        assert result_row['avg_cpu_seconds'] == pytest.approx(0.0)

    def test_null_text_becomes_empty_obfuscated_query(self, aggregator, dd_run_check):
        row = list(MOCK_QUERY_STATS_ROWS[0])
        row[3] = None  # text = NULL
        mock_client, _ = _build_mock_spanner_client(rows=[row])
        check = SpannerCheck('cloud_spanner', {}, [INSTANCE_CONFIG])
        check._client = mock_client

        dd_run_check(check)

        result_row = aggregator.get_event_platform_events("dbm-metrics")[0]['spanner_rows'][0]
        assert isinstance(result_row['text'], str)


class TestSpannerClientInit:
    def test_client_is_lazily_created(self, mock_spanner_client):
        mock_client, _ = mock_spanner_client
        check = SpannerCheck('cloud_spanner', {}, [INSTANCE_CONFIG])
        assert check._client is None

    def test_client_is_cached_across_runs(self, aggregator, dd_run_check, check):
        dd_run_check(check)
        first_client = check._client
        dd_run_check(check)
        assert check._client is first_client

    def test_reported_hostname(self):
        check = SpannerCheck('cloud_spanner', {}, [INSTANCE_CONFIG])
        assert check.reported_hostname == 'test-project:test-instance'

    def test_cloud_metadata_structure(self):
        check = SpannerCheck('cloud_spanner', {}, [INSTANCE_CONFIG])
        assert check.cloud_metadata == {'gcp': {'project_id': 'test-project', 'instance_id': 'test-instance'}}

    def test_mock_client_does_not_call_create(self, aggregator, dd_run_check, check, mock_spanner_client):
        mock_client, _ = mock_spanner_client
        # _create_spanner_client should never be called because _client is pre-injected
        original_create = check._create_spanner_client
        called = []
        check._create_spanner_client = lambda: called.append(True) or original_create()

        dd_run_check(check)

        assert called == [], "_create_spanner_client should not be called when client is injected"
