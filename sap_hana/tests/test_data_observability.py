# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import threading
import time
from unittest import mock

import pytest

from datadog_checks.sap_hana.config_models.instance import CustomSqlSelectFields, Entity, Query
from datadog_checks.sap_hana.data_observability import (
    DEFAULT_DO_QUERY_TIMEOUT_S,
    SapHanaDataObservability,
    _query_key,
)

pytestmark = pytest.mark.unit

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_do(queries=(), config_id=None, tags=None):
    """Build a SapHanaDataObservability with mocked dependencies, bypassing DBMAsyncJob.__init__."""
    check = mock.MagicMock()
    check._server = 'hana-host'
    check._port = 39015
    check._username = 'dd'
    check._password = 'pass'
    check.instance = {}
    check.reported_hostname = 'hana-host'

    do_config = mock.MagicMock()
    do_config.config_id = config_id

    do = SapHanaDataObservability.__new__(SapHanaDataObservability)
    do._check = check
    do._do_config = do_config
    do._last_execution = {}
    do._do_conn = None
    do._do_conn_timeout_s = None
    do._log = mock.MagicMock()
    do._cancel_event = threading.Event()
    do._tags = tags
    do._queries, do._schedulers = do._filter_valid_queries(queries)
    return do


def _q(
    sql='SELECT 1',
    interval_seconds=None,
    schedule=None,
    monitor_id=None,
    timeout_seconds=None,
    dbname=None,
):
    return Query(
        query=sql,
        interval_seconds=interval_seconds,
        schedule=schedule,
        monitor_id=monitor_id,
        timeout_seconds=timeout_seconds,
        dbname=dbname,
    )


def _mock_conn(columns, rows):
    """Return a (conn, cursor) pair for use in _execute_single_query tests."""
    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    conn.cursor.return_value = cursor
    cursor.description = [(col,) for col in columns]
    cursor.fetchmany.return_value = rows
    return conn, cursor


# ── _query_key ────────────────────────────────────────────────────────────────


class TestQueryKey:
    def test_same_sql_same_key(self):
        assert _query_key(_q('SELECT 1')) == _query_key(_q('SELECT 1'))

    def test_different_sql_different_key(self):
        assert _query_key(_q('SELECT 1')) != _query_key(_q('SELECT 2'))

    def test_key_is_16_hex_chars(self):
        key = _query_key(_q('SELECT 1'))
        assert len(key) == 16
        assert all(c in '0123456789abcdef' for c in key)


# ── _filter_valid_queries ──────────────────────────────────────────────────────


class TestFilterValidQueries:
    def test_interval_query_accepted(self):
        do = _make_do([_q(interval_seconds=60)])
        assert len(do._queries) == 1

    def test_cron_query_accepted(self):
        do = _make_do([_q(schedule='*/5 * * * *')])
        assert len(do._queries) == 1
        assert len(do._schedulers) == 1

    def test_missing_scheduling_rejected(self):
        do = _make_do([_q()])
        assert do._queries == ()

    def test_zero_interval_rejected(self):
        do = _make_do([_q(interval_seconds=0)])
        assert do._queries == ()

    def test_negative_interval_rejected(self):
        do = _make_do([_q(interval_seconds=-1)])
        assert do._queries == ()

    def test_invalid_cron_rejected(self):
        do = _make_do([_q(schedule='not-a-cron')])
        assert do._queries == ()

    def test_mixed_valid_and_invalid(self):
        queries = [_q(interval_seconds=30), _q(), _q(schedule='*/10 * * * *')]
        do = _make_do(queries)
        assert len(do._queries) == 2

    def test_cron_scheduler_keyed_by_query_hash(self):
        q = _q(schedule='0 * * * *')
        do = _make_do([q])
        assert _query_key(q) in do._schedulers

    def test_interval_query_has_no_scheduler(self):
        q = _q(interval_seconds=60)
        do = _make_do([q])
        assert _query_key(q) not in do._schedulers

    def test_skipped_queries_emit_warning(self):
        do = _make_do([_q(), _q(interval_seconds=30)])
        do._log.warning.assert_called()


# ── _get_due_queries ───────────────────────────────────────────────────────────


class TestGetDueQueries:
    def test_interval_first_run_is_due(self):
        do = _make_do([_q(interval_seconds=60)])
        due = do._get_due_queries()
        assert len(due) == 1
        assert due[0].mode == 'interval'

    def test_interval_not_yet_elapsed(self):
        q = _q(interval_seconds=60)
        do = _make_do([q])
        do._last_execution[_query_key(q)] = time.time()
        assert do._get_due_queries() == []

    def test_interval_elapsed_is_due(self):
        q = _q(interval_seconds=60)
        do = _make_do([q])
        do._last_execution[_query_key(q)] = time.time() - 61
        assert len(do._get_due_queries()) == 1

    def test_interval_scheduled_time_is_last_plus_interval(self):
        q = _q(interval_seconds=60)
        do = _make_do([q])
        last = time.time() - 90
        do._last_execution[_query_key(q)] = last
        due = do._get_due_queries()
        assert abs(due[0].scheduled_time - (last + 60)) < 0.01

    def test_interval_first_run_scheduled_time_is_now(self):
        q = _q(interval_seconds=60)
        do = _make_do([q])
        before = time.time()
        due = do._get_due_queries()
        after = time.time()
        assert before <= due[0].scheduled_time <= after

    def test_cron_due_has_cron_mode(self):
        # every-minute cron fires within the 300s startup lookback
        q = _q(schedule='* * * * *')
        do = _make_do([q])
        due = do._get_due_queries()
        assert len(due) == 1
        assert due[0].mode == 'cron'

    def test_no_queries_returns_empty(self):
        do = _make_do([])
        assert do._get_due_queries() == []


# ── _build_base_tags ───────────────────────────────────────────────────────────


class TestBuildBaseTags:
    def test_db_type_always_present(self):
        do = _make_do()
        assert 'db_type:saphana' in do._build_base_tags()

    def test_config_id_tag_added(self):
        do = _make_do(config_id='cfg-42')
        assert 'config_id:cfg-42' in do._build_base_tags()

    def test_no_config_id_no_config_id_tag(self):
        do = _make_do(config_id=None)
        assert not any(t.startswith('config_id:') for t in do._build_base_tags())

    def test_dd_internal_tags_filtered(self):
        do = _make_do(tags=['dd.internal.resource:x', 'env:prod'])
        tags = do._build_base_tags()
        assert 'env:prod' in tags
        assert not any(t.startswith('dd.internal') for t in tags)

    def test_none_tags_does_not_error(self):
        do = _make_do(tags=None)
        assert 'db_type:saphana' in do._build_base_tags()


# ── _build_event_payload ───────────────────────────────────────────────────────


class TestBuildEventPayload:
    _RESULT = {
        'status': 'success',
        'columns': ['id'],
        'rows': [[1]],
        'row_count': 1,
        'duration_s': 0.1,
        'error': None,
    }

    def test_monitor_id_present_when_set(self):
        q = _q(monitor_id=42)
        payload = _make_do()._build_event_payload(q, self._RESULT)
        assert payload['monitor_id'] == 42

    def test_monitor_id_absent_when_none(self):
        q = _q()
        payload = _make_do()._build_event_payload(q, self._RESULT)
        assert 'monitor_id' not in payload

    def test_entity_fields_serialized(self):
        entity = Entity(platform='snowflake', table='my_table')
        q = Query(query='SELECT 1', interval_seconds=60, entity=entity)
        payload = _make_do()._build_event_payload(q, self._RESULT)
        assert payload['entity'] == {'platform': 'snowflake', 'table': 'my_table'}

    def test_entity_empty_dict_when_none(self):
        payload = _make_do()._build_event_payload(_q(), self._RESULT)
        assert payload['entity'] == {}

    def test_custom_sql_select_fields_serialized(self):
        fields = CustomSqlSelectFields(metric_config_id=7, entity_id='eid')
        q = Query(query='SELECT 1', interval_seconds=60, custom_sql_select_fields=fields)
        payload = _make_do()._build_event_payload(q, self._RESULT)
        assert payload['custom_sql_select_fields'] == {'metric_config_id': 7, 'entity_id': 'eid'}

    def test_custom_sql_select_fields_none(self):
        payload = _make_do()._build_event_payload(_q(), self._RESULT)
        assert payload['custom_sql_select_fields'] is None

    def test_dbname_empty_string_when_none(self):
        payload = _make_do()._build_event_payload(_q(), self._RESULT)
        assert payload['db_name'] == ''

    def test_dbname_present_when_set(self):
        payload = _make_do()._build_event_payload(_q(dbname='PROD'), self._RESULT)
        assert payload['db_name'] == 'PROD'

    def test_config_id_in_payload(self):
        payload = _make_do(config_id='abc-123')._build_event_payload(_q(), self._RESULT)
        assert payload['config_id'] == 'abc-123'

    def test_config_id_empty_string_when_none(self):
        payload = _make_do(config_id=None)._build_event_payload(_q(), self._RESULT)
        assert payload['config_id'] == ''

    def test_result_fields_merged_into_payload(self):
        payload = _make_do()._build_event_payload(_q(), self._RESULT)
        assert payload['status'] == 'success'
        assert payload['row_count'] == 1
        assert payload['columns'] == ['id']
        assert payload['error'] is None

    def test_db_type_and_host_present(self):
        payload = _make_do()._build_event_payload(_q(), self._RESULT)
        assert payload['db_type'] == 'saphana'
        assert payload['db_host'] == 'hana-host'
        assert payload['db_port'] == 39015


# ── _execute_single_query ──────────────────────────────────────────────────────


class TestExecuteSingleQuery:
    def test_success_returns_columns_and_rows(self):
        q = _q('SELECT id FROM T', interval_seconds=60)
        do = _make_do([q])
        conn, _ = _mock_conn(['id', 'name'], [[1, 'alice'], [2, 'bob']])
        do._do_conn = conn
        do._do_conn_timeout_s = DEFAULT_DO_QUERY_TIMEOUT_S

        result = do._execute_single_query(q)

        assert result['status'] == 'success'
        assert result['columns'] == ['id', 'name']
        assert result['rows'] == [[1, 'alice'], [2, 'bob']]
        assert result['row_count'] == 2
        assert result['error'] is None

    def test_hana_error_returns_error_status(self):
        from hdbcli.dbapi import Error as HanaError

        q = _q(interval_seconds=60)
        do = _make_do([q])
        conn, cursor = _mock_conn(['id'], [])
        cursor.execute.side_effect = HanaError('connection lost')
        do._do_conn = conn
        do._do_conn_timeout_s = DEFAULT_DO_QUERY_TIMEOUT_S

        result = do._execute_single_query(q)

        assert result['status'] == 'error'
        assert result['row_count'] == 0
        assert result['columns'] == []
        assert 'connection lost' in result['error']

    def test_hana_error_resets_connection(self):
        from hdbcli.dbapi import Error as HanaError

        q = _q(interval_seconds=60)
        do = _make_do([q])
        conn, cursor = _mock_conn([], [])
        cursor.execute.side_effect = HanaError('timeout')
        do._do_conn = conn
        do._do_conn_timeout_s = DEFAULT_DO_QUERY_TIMEOUT_S

        do._execute_single_query(q)

        assert do._do_conn is None
        assert do._do_conn_timeout_s is None

    def test_uses_default_timeout_when_none(self):
        q = _q(interval_seconds=60)  # timeout_seconds is None
        do = _make_do([q])
        called_with = []

        def fake_get_connection(timeout_s):
            called_with.append(timeout_s)
            conn, _ = _mock_conn(['x'], [])
            return conn

        do._get_connection = fake_get_connection
        do._execute_single_query(q)
        assert called_with == [DEFAULT_DO_QUERY_TIMEOUT_S]

    def test_uses_query_timeout_when_set(self):
        q = _q(interval_seconds=60, timeout_seconds=120)
        do = _make_do([q])
        called_with = []

        def fake_get_connection(timeout_s):
            called_with.append(timeout_s)
            conn, _ = _mock_conn(['x'], [])
            return conn

        do._get_connection = fake_get_connection
        do._execute_single_query(q)
        assert called_with == [120]
