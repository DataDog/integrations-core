# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import threading
import time
from unittest import mock

import pytest

from datadog_checks.sap_hana.config_models.instance import CustomSqlSelectFields, Entity, Query
from datadog_checks.sap_hana.data_observability import (
    DEFAULT_DO_QUERY_TIMEOUT_MS,
    SapHanaDataObservability,
    _query_key,
)

pytestmark = pytest.mark.unit


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
    do._do_conn_timeout_ms = None
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
    query_timeout=None,
    dbname=None,
):
    return Query(
        query=sql,
        interval_seconds=interval_seconds,
        schedule=schedule,
        monitor_id=monitor_id,
        query_timeout=query_timeout,
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


SAMPLE_RESULT = {
    'status': 'success',
    'columns': ['id'],
    'rows': [[1]],
    'row_count': 1,
    'duration_s': 0.1,
    'error': None,
}


def test_query_key_same_query_same_key():
    assert _query_key(_q('SELECT 1')) == _query_key(_q('SELECT 1'))


def test_query_key_different_sql_different_key():
    # Distinct monitors always yield distinct SQL (monitor ids are embedded in the query).
    assert _query_key(_q('SELECT 1')) != _query_key(_q('SELECT 2'))


def test_query_key_is_16_hex_chars():
    key = _query_key(_q('SELECT 1'))
    assert len(key) == 16
    assert all(c in '0123456789abcdef' for c in key)


def test_query_key_nonzero_monitor_id_used_as_key():
    assert _query_key(_q('SELECT 1', monitor_id=42)) == 'monitor:42'


def test_query_key_different_monitor_ids_different_key():
    # With a real monitor id, identity comes from the id, not the SQL.
    assert _query_key(_q('SELECT 1', monitor_id=1)) != _query_key(_q('SELECT 1', monitor_id=2))


def test_query_key_same_monitor_id_same_key_regardless_of_sql():
    assert _query_key(_q('SELECT 1', monitor_id=7)) == _query_key(_q('SELECT 2', monitor_id=7))


def test_query_key_zero_monitor_id_falls_back_to_query_hash():
    # monitor_id 0 (the omitempty default) and None both fall back to the query hash.
    assert _query_key(_q('SELECT 1', monitor_id=0)) == _query_key(_q('SELECT 1', monitor_id=None))
    assert _query_key(_q('SELECT 1', monitor_id=0)) == _query_key(_q('SELECT 1'))


def test_filter_interval_query_accepted():
    do = _make_do([_q(interval_seconds=60)])
    assert len(do._queries) == 1


def test_filter_cron_query_accepted():
    do = _make_do([_q(schedule='*/5 * * * *')])
    assert len(do._queries) == 1
    assert len(do._schedulers) == 1


def test_filter_missing_scheduling_rejected():
    do = _make_do([_q()])
    assert do._queries == ()


def test_filter_zero_interval_rejected():
    do = _make_do([_q(interval_seconds=0)])
    assert do._queries == ()


def test_filter_negative_interval_rejected():
    do = _make_do([_q(interval_seconds=-1)])
    assert do._queries == ()


def test_filter_invalid_cron_rejected():
    do = _make_do([_q(schedule='not-a-cron')])
    assert do._queries == ()


def test_filter_mixed_valid_and_invalid():
    queries = [_q('SELECT 1', interval_seconds=30), _q('SELECT 2'), _q('SELECT 3', schedule='*/10 * * * *')]
    do = _make_do(queries)
    assert len(do._queries) == 2


def test_filter_cron_scheduler_keyed_by_query_key():
    q = _q(schedule='0 * * * *')
    do = _make_do([q])
    assert _query_key(q) in do._schedulers


def test_filter_interval_query_has_no_scheduler():
    q = _q(interval_seconds=60)
    do = _make_do([q])
    assert _query_key(q) not in do._schedulers


def test_filter_skipped_queries_emit_warning():
    do = _make_do([_q('SELECT 1'), _q('SELECT 2', interval_seconds=30)])
    do._log.warning.assert_called()


def test_due_interval_first_run_is_due():
    do = _make_do([_q(interval_seconds=60)])
    due = do._get_due_queries()
    assert len(due) == 1
    assert due[0].mode == 'interval'


def test_due_interval_not_yet_elapsed():
    q = _q(interval_seconds=60)
    do = _make_do([q])
    do._last_execution[_query_key(q)] = time.time()
    assert do._get_due_queries() == []


def test_due_interval_elapsed_is_due():
    q = _q(interval_seconds=60)
    do = _make_do([q])
    do._last_execution[_query_key(q)] = time.time() - 61
    assert len(do._get_due_queries()) == 1


def test_due_interval_scheduled_time_is_last_plus_interval():
    q = _q(interval_seconds=60)
    do = _make_do([q])
    last = time.time() - 90
    do._last_execution[_query_key(q)] = last
    due = do._get_due_queries()
    assert abs(due[0].scheduled_time - (last + 60)) < 0.01


def test_due_interval_first_run_scheduled_time_is_now():
    q = _q(interval_seconds=60)
    do = _make_do([q])
    before = time.time()
    due = do._get_due_queries()
    after = time.time()
    assert before <= due[0].scheduled_time <= after


def test_due_cron_has_cron_mode():
    # every-minute cron fires within the 300s startup lookback
    q = _q(schedule='* * * * *')
    do = _make_do([q])
    due = do._get_due_queries()
    assert len(due) == 1
    assert due[0].mode == 'cron'


def test_due_no_queries_returns_empty():
    do = _make_do([])
    assert do._get_due_queries() == []


def test_base_tags_db_type_always_present():
    do = _make_do()
    assert 'db_type:saphana' in do._build_base_tags()


def test_base_tags_config_id_tag_added():
    do = _make_do(config_id='cfg-42')
    assert 'config_id:cfg-42' in do._build_base_tags()


def test_base_tags_no_config_id_no_config_id_tag():
    do = _make_do(config_id=None)
    assert not any(t.startswith('config_id:') for t in do._build_base_tags())


def test_base_tags_dd_internal_tags_filtered():
    do = _make_do(tags=['dd.internal.resource:x', 'env:prod'])
    tags = do._build_base_tags()
    assert 'env:prod' in tags
    assert not any(t.startswith('dd.internal') for t in tags)


def test_base_tags_none_tags_does_not_error():
    do = _make_do(tags=None)
    assert 'db_type:saphana' in do._build_base_tags()


def test_payload_monitor_id_present_when_set():
    q = _q(monitor_id=42)
    payload = _make_do()._build_event_payload(q, SAMPLE_RESULT)
    assert payload['monitor_id'] == 42


def test_payload_monitor_id_absent_when_none():
    q = _q()  # monitor_id is None
    payload = _make_do()._build_event_payload(q, SAMPLE_RESULT)
    assert 'monitor_id' not in payload


def test_payload_entity_fields_serialized():
    entity = Entity(platform='snowflake', table='my_table')
    q = Query(query='SELECT 1', interval_seconds=60, entity=entity)
    payload = _make_do()._build_event_payload(q, SAMPLE_RESULT)
    assert payload['entity'] == {'platform': 'snowflake', 'table': 'my_table'}


def test_payload_entity_empty_dict_when_none():
    payload = _make_do()._build_event_payload(_q(), SAMPLE_RESULT)
    assert payload['entity'] == {}


def test_payload_custom_sql_select_fields_serialized():
    fields = CustomSqlSelectFields(metric_config_id=7, entity_id='eid')
    q = Query(query='SELECT 1', interval_seconds=60, custom_sql_select_fields=fields)
    payload = _make_do()._build_event_payload(q, SAMPLE_RESULT)
    assert payload['custom_sql_select_fields'] == {'metric_config_id': 7, 'entity_id': 'eid'}


def test_payload_custom_sql_select_fields_none():
    payload = _make_do()._build_event_payload(_q(), SAMPLE_RESULT)
    assert payload['custom_sql_select_fields'] is None


def test_payload_dbname_empty_string_when_none():
    payload = _make_do()._build_event_payload(_q(), SAMPLE_RESULT)
    assert payload['db_name'] == ''


def test_payload_dbname_present_when_set():
    payload = _make_do()._build_event_payload(_q(dbname='PROD'), SAMPLE_RESULT)
    assert payload['db_name'] == 'PROD'


def test_payload_config_id_in_payload():
    payload = _make_do(config_id='abc-123')._build_event_payload(_q(), SAMPLE_RESULT)
    assert payload['config_id'] == 'abc-123'


def test_payload_config_id_empty_string_when_none():
    payload = _make_do(config_id=None)._build_event_payload(_q(), SAMPLE_RESULT)
    assert payload['config_id'] == ''


def test_payload_result_fields_merged_into_payload():
    payload = _make_do()._build_event_payload(_q(), SAMPLE_RESULT)
    assert payload['status'] == 'success'
    assert payload['row_count'] == 1
    assert payload['columns'] == ['id']
    assert payload['error'] is None


def test_payload_db_type_and_host_present():
    payload = _make_do()._build_event_payload(_q(), SAMPLE_RESULT)
    assert payload['db_type'] == 'saphana'
    assert payload['db_host'] == 'hana-host'
    assert payload['db_port'] == 39015


def test_execute_success_returns_columns_and_rows():
    q = _q('SELECT id FROM T', interval_seconds=60)
    do = _make_do([q])
    conn, _ = _mock_conn(['id', 'name'], [[1, 'alice'], [2, 'bob']])
    do._do_conn = conn
    do._do_conn_timeout_ms = DEFAULT_DO_QUERY_TIMEOUT_MS

    result = do._execute_single_query(q)

    assert result['status'] == 'success'
    assert result['columns'] == ['id', 'name']
    assert result['rows'] == [[1, 'alice'], [2, 'bob']]
    assert result['row_count'] == 2
    assert result['error'] is None


def test_execute_hana_error_returns_error_status():
    from hdbcli.dbapi import Error as HanaError

    q = _q(interval_seconds=60)
    do = _make_do([q])
    conn, cursor = _mock_conn(['id'], [])
    cursor.execute.side_effect = HanaError('connection lost')
    do._do_conn = conn
    do._do_conn_timeout_ms = DEFAULT_DO_QUERY_TIMEOUT_MS

    result = do._execute_single_query(q)

    assert result['status'] == 'error'
    assert result['row_count'] == 0
    assert result['columns'] == []
    assert 'connection lost' in result['error']


def test_execute_hana_error_resets_connection():
    from hdbcli.dbapi import Error as HanaError

    q = _q(interval_seconds=60)
    do = _make_do([q])
    conn, cursor = _mock_conn([], [])
    cursor.execute.side_effect = HanaError('timeout')
    do._do_conn = conn
    do._do_conn_timeout_ms = DEFAULT_DO_QUERY_TIMEOUT_MS

    do._execute_single_query(q)

    assert do._do_conn is None
    assert do._do_conn_timeout_ms is None


def test_execute_uses_default_timeout_when_none():
    q = _q(interval_seconds=60)  # query_timeout is None
    do = _make_do([q])
    called_with = []

    def fake_get_connection(timeout_ms):
        called_with.append(timeout_ms)
        conn, _ = _mock_conn(['x'], [])
        return conn

    do._get_connection = fake_get_connection
    do._execute_single_query(q)
    assert called_with == [DEFAULT_DO_QUERY_TIMEOUT_MS]


def test_execute_uses_query_timeout_when_set():
    q = _q(interval_seconds=60, query_timeout=120)
    do = _make_do([q])
    called_with = []

    def fake_get_connection(timeout_ms):
        called_with.append(timeout_ms)
        conn, _ = _mock_conn(['x'], [])
        return conn

    do._get_connection = fake_get_connection
    do._execute_single_query(q)
    assert called_with == [120]


def test_run_job_no_queries_is_noop():
    do = _make_do([])
    do.run_job()
    do._check.event_platform_event.assert_not_called()


def test_run_job_no_due_queries_is_noop():
    q = _q(interval_seconds=60)
    do = _make_do([q])
    do._last_execution[_query_key(q)] = time.time()  # just ran, not due yet
    do.run_job()
    do._check.event_platform_event.assert_not_called()


def test_run_job_due_query_emits_event_and_metrics():
    q = _q('SELECT id FROM T', interval_seconds=60)
    do = _make_do([q])
    conn, _ = _mock_conn(['id'], [[1], [2]])
    do._do_conn = conn
    do._do_conn_timeout_ms = DEFAULT_DO_QUERY_TIMEOUT_MS

    do.run_job()

    do._check.event_platform_event.assert_called_once()
    raw_event, track_type = do._check.event_platform_event.call_args[0]
    assert track_type == 'do-query-results'
    payload = json.loads(raw_event)
    assert payload['status'] == 'success'
    assert payload['row_count'] == 2
    # interval mode records the last execution so the query is not immediately due again
    assert _query_key(q) in do._last_execution


def test_run_job_connection_open_failure_does_not_skip_remaining_queries():
    from hdbcli.dbapi import Error as HanaError

    q1 = _q('SELECT 1', interval_seconds=60)
    q2 = _q('SELECT 2', interval_seconds=60)
    do = _make_do([q1, q2])

    conn, _ = _mock_conn(['x'], [[1]])
    calls = []

    def fake_get_connection(timeout_ms):
        calls.append(timeout_ms)
        if len(calls) == 1:
            raise HanaError('cannot open connection')
        return conn

    do._get_connection = fake_get_connection

    do.run_job()

    # Both queries were attempted despite the first connection failing, and both
    # produced an event (the first an error, the second a success).
    assert len(calls) == 2
    assert do._check.event_platform_event.call_count == 2
    statuses = {json.loads(c[0][0])['status'] for c in do._check.event_platform_event.call_args_list}
    assert statuses == {'error', 'success'}
