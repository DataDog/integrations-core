# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import datetime
import json
import time
import uuid
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

import pymysql
import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.cursor import BaseCommenterCursor, CommenterSSCursor
from datadog_checks.mysql.data_observability import EVENT_TRACK_TYPE
from datadog_checks.mysql.do_query import FETCH_BATCH_ROWS
from datadog_checks.mysql.do_task import (
    MAX_EVENT_BYTES,
    MAX_TASK_STATEMENT_ROWS,
    NET_WRITE_TIMEOUT_SECONDS,
    MySqlTaskCheck,
    _ChunkSender,
    _to_text,
)

from . import common
from .do_fakes import FakeConnection

pytestmark = pytest.mark.unit

CONFIG_ID = 'do-mysql-once-3f1c2a9e-8b7d-4c1e-9f2a-6d5e4c3b2a10'
TASK_ID = '3f1c2a9e-8b7d-4c1e-9f2a-6d5e4c3b2a10'


def _statement(statement_id='s0', query='SELECT 1', max_rows=MAX_TASK_STATEMENT_ROWS, dbname='shop'):
    return {'id': statement_id, 'dbname': dbname, 'query': query, 'timeout_seconds': 300, 'max_rows': max_rows}


def _create_check(instance_basic, statements, expires_at=None):
    instance = deepcopy(instance_basic)
    instance.update(
        {
            'run_once': True,
            'do_task': {
                'config_id': CONFIG_ID,
                'task_id': TASK_ID,
                'expires_at': expires_at if expires_at is not None else int(time.time()) + 600,
                'statements': statements,
            },
        }
    )
    check = MySql(common.CHECK_NAME, {}, [instance])
    check._resolved_hostname = 'mysql.test'
    return check


def _run(dd_run_check, check, *connections):
    with patch('datadog_checks.mysql.do_task.connect_with_session_variables', side_effect=list(connections)) as connect:
        dd_run_check(check)
    return connect


def _events(aggregator):
    return aggregator.get_event_platform_events(EVENT_TRACK_TYPE)


def _chunks(events, statement_id='s0'):
    return [event for event in events if event.get('kind') == 'chunk' and event['statement_id'] == statement_id]


def _final(events, statement_id='s0'):
    (final,) = [event for event in events if event.get('kind') == 'final' and event['statement_id'] == statement_id]
    return final


def _sent_rows(events, statement_id='s0'):
    return [row for chunk in _chunks(events, statement_id) for row in chunk['rows']]


def _metric_tags(check, *extra):
    base = [tag for tag in check.tag_manager.get_tags() if not tag.startswith('dd.internal')]
    return base + ['db_type:mysql', *extra]


def _assert_count(aggregator, check, name, *tags, count=1):
    aggregator.assert_metric(
        name,
        # The stub sums the values of count submissions.
        value=count,
        tags=_metric_tags(check, *tags),
        count=count,
        hostname='mysql.test',
        metric_type=aggregator.COUNT,
    )


def test_instance_with_do_task_builds_the_task_check(instance_basic):
    # The task check must never run the mysql check's own setup: async jobs, health events and
    # collection would carry the user's instance tags and its SQL.
    task_check = _create_check(instance_basic, [_statement()])
    assert isinstance(task_check, MySqlTaskCheck)
    assert not isinstance(task_check, MySql)

    assert isinstance(MySql(common.CHECK_NAME, {}, [deepcopy(instance_basic)]), MySql)


def test_task_runs_statements_and_reports_only_events(aggregator, dd_run_check, instance_basic):
    check = _create_check(
        instance_basic,
        [_statement('s0', 'SELECT id, name FROM customers'), _statement('s1', 'SELECT count(*) FROM orders')],
    )
    conn = FakeConnection(
        {
            'SELECT id, name FROM customers': (['id', 'name'], [(1, 'ada'), (2, None)]),
            'SELECT count(*) FROM orders': (['count(*)'], [(42,)]),
        }
    )

    connect = _run(dd_run_check, check, conn)

    assert connect.call_count == 1
    assert conn.executed[:7] == [
        'SELECT @@version, @@version_comment',
        'SET SESSION TRANSACTION READ ONLY',
        "SET time_zone = '+00:00'",
        ('SET SESSION net_write_timeout = %s', (NET_WRITE_TIMEOUT_SECONDS,)),
        ('SET SESSION max_execution_time = %s', (300_000,)),
        ('SET SESSION sql_select_limit = %s', (MAX_TASK_STATEMENT_ROWS,)),
        'USE `shop`',
    ]
    assert not conn.open

    chunk, final, second_chunk, second_final = _events(aggregator)
    routing = {
        'config_id': CONFIG_ID,
        'task_id': TASK_ID,
        'db_type': 'mysql',
        'db_host': 'mysql.test',
        'db_port': common.PORT,
        'statement_id': 's0',
        'result_id': chunk['result_id'],
    }
    assert chunk == {
        **routing,
        'kind': 'chunk',
        'timestamp': chunk['timestamp'],
        'chunk_index': 0,
        'rows': [['1', 'ada'], ['2', None]],
    }
    assert final == {
        **routing,
        'kind': 'final',
        'timestamp': final['timestamp'],
        'db_name': 'shop',
        'query': 'SELECT id, name FROM customers',
        'timeout_ms': 300_000,
        'status': 'success',
        'chunk_count': 1,
        'row_count': 2,
        'columns': ['id', 'name'],
        'duration_s': final['duration_s'],
        'error': None,
        'error_kind': None,
        'error_code': None,
    }
    assert (second_chunk['kind'], second_chunk['statement_id'], second_chunk['rows']) == ('chunk', 's1', [['42']])
    assert (second_final['kind'], second_final['statement_id'], second_final['row_count']) == ('final', 's1', 1)
    assert second_chunk['result_id'] == second_final['result_id'] != chunk['result_id']

    # The task check shares the tags of the user's instance, so it must not report anything that
    # could change that instance's status, and it starts none of the instance's async jobs. Its
    # only metrics are internal ones.
    assert not aggregator.service_checks(MySql.SERVICE_CHECK_NAME)
    assert aggregator.metric_names
    assert all(name.startswith('dd.mysql.do_task.') for name in aggregator.metric_names)
    assert not aggregator.get_event_platform_events('dbm-health')
    assert not check._async_job_registry


def test_metrics_report_runs_statements_and_events(aggregator, dd_run_check, instance_basic):
    check = _create_check(
        instance_basic,
        [_statement('s0', 'SELECT id FROM customers'), _statement('s1', 'SELECT nope')],
    )
    conn = FakeConnection(
        {
            'SELECT id FROM customers': (['id'], [(1,), (2,)]),
            'SELECT nope': pymysql.err.OperationalError(1054, "Unknown column 'nope'"),
        }
    )

    _run(dd_run_check, check, conn)

    _assert_count(aggregator, check, 'dd.mysql.do_task.runs', 'outcome:completed')
    _assert_count(aggregator, check, 'dd.mysql.do_task.statements', 'status:success')
    _assert_count(
        aggregator,
        check,
        'dd.mysql.do_task.statements',
        'status:error',
        'error_kind:sql_error',
    )
    # A chunk and a final event for the success, a final event for the error.
    _assert_count(aggregator, check, 'dd.mysql.do_task.events', count=3)
    for status in ('success', 'error'):
        aggregator.assert_metric(
            'dd.mysql.do_task.statement_execution_time',
            tags=_metric_tags(check, f'status:{status}'),
            count=1,
            hostname='mysql.test',
            metric_type=aggregator.HISTOGRAM,
        )
    aggregator.assert_metric(
        'dd.mysql.do_task.statement_rows',
        value=2,
        tags=_metric_tags(check),
        count=1,
        hostname='mysql.test',
        metric_type=aggregator.HISTOGRAM,
    )
    aggregator.assert_metric(
        'dd.mysql.do_task.statement_chunks',
        value=1,
        tags=_metric_tags(check),
        count=1,
        hostname='mysql.test',
        metric_type=aggregator.HISTOGRAM,
    )
    for tag in _metric_tags(check):
        assert TASK_ID not in tag
    aggregator.assert_metric('dd.mysql.do_task.emit_failures', count=0)


def test_failed_emit_is_counted_and_the_task_continues(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0', 'SELECT 1'), _statement('s1', 'SELECT 2')])
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)]), 'SELECT 2': (['2'], [(2,)])})

    # The first chunk fails; the final event and the second statement's events still go out.
    with patch.object(check, 'event_platform_event', side_effect=[ValueError('boom'), None, None, None]):
        _run(dd_run_check, check, conn)

    _assert_count(aggregator, check, 'dd.mysql.do_task.emit_failures', 'exc_class:ValueError')
    _assert_count(aggregator, check, 'dd.mysql.do_task.events', count=3)
    _assert_count(aggregator, check, 'dd.mysql.do_task.statements', 'status:success', count=2)
    _assert_count(aggregator, check, 'dd.mysql.do_task.runs', 'outcome:completed')


def test_every_query_carries_the_agent_comment(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0', 'SELECT 1'), _statement('s1', 'SELECT 2')])
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)]), 'SELECT 2': (['2'], [(2,)])})

    _run(dd_run_check, check, conn)

    assert conn.cursor_classes
    assert all(issubclass(cursor_class, BaseCommenterCursor) for cursor_class in conn.cursor_classes)
    assert CommenterSSCursor in conn.cursor_classes


def test_each_execution_gets_a_new_result_id(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement()])
    results = {'SELECT 1': (['1'], [(1,)])}

    _run(dd_run_check, check, FakeConnection(results))
    _run(dd_run_check, check, FakeConnection(results))

    first_chunk, first, second_chunk, second = _events(aggregator)
    assert first['statement_id'] == second['statement_id'] == 's0'
    assert first_chunk['result_id'] == first['result_id'] != second['result_id'] == second_chunk['result_id']
    assert str(uuid.UUID(first['result_id'])) == first['result_id']


def test_failed_statement_does_not_stop_the_others(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0', 'SELECT nope'), _statement('s1', 'SELECT 1')])
    conn = FakeConnection(
        {
            'SELECT nope': pymysql.err.OperationalError(1054, "Unknown column 'nope' in 'field list'"),
            'SELECT 1': (['1'], [(1,)]),
        }
    )

    connect = _run(dd_run_check, check, conn)

    events = _events(aggregator)
    assert not _chunks(events, 's0')
    failed = _final(events, 's0')
    assert (failed['status'], failed['error_kind'], failed['error_code']) == ('error', 'sql_error', '1054')
    assert (failed['chunk_count'], failed['row_count'], failed['columns']) == (0, 0, [])
    assert _final(events, 's1')['status'] == 'success'
    assert _sent_rows(events, 's1') == [['1']]
    # A plain server error leaves the connection usable.
    assert connect.call_count == 1


@pytest.mark.parametrize(
    'error, expected_kind',
    [
        pytest.param(
            pymysql.err.OperationalError(3024, 'maximum statement execution time exceeded'),
            'statement_timeout',
            id='mysql-timeout',
        ),
        pytest.param(
            pymysql.err.OperationalError(1969, 'Query execution was interrupted'),
            'statement_timeout',
            id='mariadb-timeout',
        ),
        pytest.param(
            pymysql.err.OperationalError(1205, 'Lock wait timeout exceeded'), 'lock_timeout', id='lock-timeout'
        ),
        pytest.param(pymysql.err.OperationalError(1142, 'SELECT command denied'), 'sql_error', id='permission'),
        pytest.param(
            pymysql.err.ProgrammingError(1064, 'You have an error in your SQL syntax'), 'sql_error', id='syntax'
        ),
    ],
)
def test_server_errors_are_classified(aggregator, dd_run_check, instance_basic, error, expected_kind):
    check = _create_check(instance_basic, [_statement(query='SELECT slow()')])

    _run(dd_run_check, check, FakeConnection({'SELECT slow()': error}))

    (event,) = _events(aggregator)
    assert (event['error_kind'], event['error_code']) == (expected_kind, str(error.args[0]))


@pytest.mark.parametrize(
    'max_rows, row_count',
    [
        pytest.param(5, 5, id='max-rows'),
        # Above the old 10,000-row cap.
        pytest.param(20_000, 20_000, id='above-old-cap'),
    ],
)
def test_rows_up_to_the_limit_are_returned(aggregator, dd_run_check, instance_basic, max_rows, row_count):
    check = _create_check(instance_basic, [_statement(query='SELECT id FROM t', max_rows=max_rows)])
    conn = FakeConnection({'SELECT id FROM t': (['id'], [(i,) for i in range(row_count)])})

    _run(dd_run_check, check, conn)

    events = _events(aggregator)
    final = _final(events)
    assert final['status'] == 'success'
    assert final['row_count'] == len(_sent_rows(events)) == row_count


@pytest.mark.parametrize(
    'max_rows, row_count',
    [
        pytest.param(5, 100, id='max-rows'),
        pytest.param(20_000, 25_000, id='above-old-cap'),
    ],
)
def test_rows_past_the_limit_are_not_returned(aggregator, dd_run_check, instance_basic, max_rows, row_count):
    check = _create_check(
        instance_basic,
        [_statement('s0', 'SELECT id FROM big', max_rows=max_rows), _statement('s1', 'SELECT 1')],
    )
    conn = FakeConnection(
        {'SELECT id FROM big': (['id'], [(i,) for i in range(row_count)]), 'SELECT 1': (['1'], [(1,)])}
    )

    connect = _run(dd_run_check, check, conn)

    events = _events(aggregator)
    assert _final(events, 's0')['status'] == _final(events, 's1')['status'] == 'success'
    assert _sent_rows(events, 's0') == [[str(i)] for i in range(max_rows)]
    assert _final(events, 's0')['row_count'] == max_rows
    assert ('SET SESSION sql_select_limit = %s', (max_rows,)) in conn.executed
    assert max(conn.fetch_sizes) <= FETCH_BATCH_ROWS
    # The server stopped at the limit, so the next statement runs on the same connection.
    assert not conn.drained
    assert connect.call_count == 1


def test_max_rows_above_the_hard_cap_is_capped(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement(max_rows=MAX_TASK_STATEMENT_ROWS * 2)])
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)])})

    _run(dd_run_check, check, conn)

    assert ('SET SESSION sql_select_limit = %s', (MAX_TASK_STATEMENT_ROWS,)) in conn.executed


def test_connect_failure_reports_every_statement(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0'), _statement('s1')])

    _run(dd_run_check, check, pymysql.err.OperationalError(2003, "Can't connect to MySQL server"))

    events = _events(aggregator)
    assert [(event['kind'], event['statement_id']) for event in events] == [('final', 's0'), ('final', 's1')]
    assert len({event['result_id'] for event in events}) == 2
    for event in events:
        assert (event['error_kind'], event['error_code']) == ('connection_error', '2003')
        assert (event['chunk_count'], event['row_count']) == (0, 0)
        assert event['error'].startswith('Statement not executed: could not connect to the database')

    _assert_count(aggregator, check, 'dd.mysql.do_task.runs', 'outcome:connection_error')
    _assert_count(
        aggregator,
        check,
        'dd.mysql.do_task.statements',
        'status:error',
        'error_kind:connection_error',
        count=2,
    )
    # The statements never ran, so they have no execution time.
    aggregator.assert_metric('dd.mysql.do_task.statement_execution_time', count=0)


@pytest.mark.parametrize(
    'error, code',
    [
        pytest.param(
            pymysql.err.OperationalError(2013, 'Lost connection to MySQL server during query'), '2013', id='lost'
        ),
        # pymysql's error for a socket that is already closed.
        pytest.param(pymysql.err.InterfaceError(0, ''), None, id='closed-socket'),
    ],
)
def test_lost_connection_reconnects_for_the_next_statement(aggregator, dd_run_check, instance_basic, error, code):
    def lose_connection(conn):
        conn.open = False
        return error

    check = _create_check(instance_basic, [_statement('s0', 'SELECT sleep(100)'), _statement('s1', 'SELECT 1')])
    first = FakeConnection({'SELECT sleep(100)': lose_connection})
    second = FakeConnection({'SELECT 1': (['1'], [(1,)])})

    connect = _run(dd_run_check, check, first, second)

    events = _events(aggregator)
    lost = _final(events, 's0')
    assert (lost['error_kind'], lost['error_code']) == ('connection_error', code)
    assert _final(events, 's1')['status'] == 'success'
    assert connect.call_count == 2


def test_statement_without_result_set_drops_the_session(aggregator, dd_run_check, instance_basic):
    # A statement that returns no rows may have changed the session, for example made it writable
    # again, so the next statement must not reuse it.
    check = _create_check(
        instance_basic,
        [_statement('s0', 'SET SESSION TRANSACTION READ WRITE'), _statement('s1', 'SELECT 1')],
    )
    first = FakeConnection()
    second = FakeConnection({'SELECT 1': (['1'], [(1,)])})

    connect = _run(dd_run_check, check, first, second)

    events = _events(aggregator)
    rejected = _final(events, 's0')
    assert (rejected['status'], rejected['error_kind']) == ('error', 'sql_error')
    assert not first.open
    assert connect.call_count == 2
    assert _final(events, 's1')['status'] == 'success'


def test_expired_task_reports_a_task_error_without_connecting(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement()], expires_at=int(time.time()) - 1)

    connect = _run(dd_run_check, check)

    (event,) = _events(aggregator)
    assert 'statement_id' not in event
    assert 'result_id' not in event
    assert 'kind' not in event
    assert (event['task_id'], event['status'], event['error_kind']) == (TASK_ID, 'error', 'expired')
    assert (event['chunk_index'], event['chunk_count']) == (0, 1)
    connect.assert_not_called()
    _assert_count(aggregator, check, 'dd.mysql.do_task.runs', 'outcome:expired')
    _assert_count(aggregator, check, 'dd.mysql.do_task.events')
    aggregator.assert_metric('dd.mysql.do_task.statements', count=0)


def test_cancelled_check_skips_the_remaining_statements(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0', 'SELECT 1'), _statement('s1', 'SELECT 2')])

    conn = FakeConnection({'SELECT 1': (['1'], [(1,)]), 'SELECT 2': (['2'], [(2,)])})
    emit = check._emit

    def cancel_after_the_first_result(event):
        emit(event)
        if event.get('kind') == 'final':
            check._cancelled = True

    with patch.object(check, '_emit', side_effect=cancel_after_the_first_result):
        _run(dd_run_check, check, conn)

    assert [(event['kind'], event['statement_id']) for event in _events(aggregator)] == [
        ('chunk', 's0'),
        ('final', 's0'),
    ]
    assert 'SELECT 2' not in conn.executed
    _assert_count(aggregator, check, 'dd.mysql.do_task.runs', 'outcome:cancelled')
    aggregator.assert_metric('dd.mysql.do_task.runs', tags=_metric_tags(check, 'outcome:completed'), count=0)


def _chunk_budget(instance_basic):
    # The space the rows of one chunk event may use, measured the way the check measures it.
    check = _create_check(instance_basic, [_statement()])
    return _ChunkSender(check, check._task.statements[0], str(uuid.uuid4()))._budget


def _raw_events(aggregator):
    return aggregator.get_event_platform_events(EVENT_TRACK_TYPE, parse_json=False)


def test_chunks_fill_the_byte_budget(aggregator, dd_run_check, instance_basic):
    # A row of n characters encodes as ["…"] plus a separating comma: n + 5 bytes. Three such rows
    # fill the budget exactly, so a fourth starts the next chunk.
    width = _chunk_budget(instance_basic) // 3 - 5
    rows = [(chr(ord('a') + i) * width,) for i in range(7)]
    check = _create_check(instance_basic, [_statement(query='SELECT payload FROM blobs')])

    _run(dd_run_check, check, FakeConnection({'SELECT payload FROM blobs': (['payload'], rows)}))

    raw_events = _raw_events(aggregator)
    assert all(len(raw) <= MAX_EVENT_BYTES for raw in raw_events)
    events = [json.loads(raw) for raw in raw_events]
    chunks = _chunks(events)
    assert [len(chunk['rows']) for chunk in chunks] == [3, 3, 1]
    assert [chunk['chunk_index'] for chunk in chunks] == [0, 1, 2]
    assert _sent_rows(events) == [[value] for (value,) in rows]
    final = _final(events)
    assert (final['chunk_count'], final['row_count']) == (3, 7)
    assert len({event['result_id'] for event in events}) == 1


def test_row_larger_than_the_budget_gets_its_own_chunk(aggregator, dd_run_check, instance_basic):
    rows = [('small',), ('x' * MAX_EVENT_BYTES,), ('small',)]
    check = _create_check(instance_basic, [_statement(query='SELECT payload FROM blobs')])

    _run(dd_run_check, check, FakeConnection({'SELECT payload FROM blobs': (['payload'], rows)}))

    events = _events(aggregator)
    assert [chunk['rows'] for chunk in _chunks(events)] == [[['small']], [['x' * MAX_EVENT_BYTES]], [['small']]]
    assert _final(events)['chunk_count'] == 3


def test_chunks_are_sent_while_reading(aggregator, dd_run_check, instance_basic):
    # 1,000 rows of 5,000 bytes are more than one chunk, so every batch sends at least one.
    rows = [('x' * 5_000,) for _ in range(2_500)]
    check = _create_check(instance_basic, [_statement(query='SELECT payload FROM blobs')])
    conn = FakeConnection({'SELECT payload FROM blobs': (['payload'], rows)})
    events_at_fetch = []
    conn.on_fetch = lambda: events_at_fetch.append(len(_events(aggregator)))

    _run(dd_run_check, check, conn)

    assert conn.fetch_sizes == [FETCH_BATCH_ROWS] * 3
    assert events_at_fetch[0] == 0
    # By the last read, the chunks of the first two batches are already out.
    assert events_at_fetch[-1] >= 2
    assert len(_sent_rows(_events(aggregator))) == 2_500


def test_empty_result_sends_only_the_final_event(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement(query='SELECT id FROM empty')])

    _run(dd_run_check, check, FakeConnection({'SELECT id FROM empty': (['id'], [])}))

    (final,) = _events(aggregator)
    assert (final['kind'], final['status']) == ('final', 'success')
    assert (final['chunk_count'], final['row_count'], final['columns']) == (0, 0, ['id'])


def test_error_while_reading_sends_an_error_final(aggregator, dd_run_check, instance_basic):
    # Two batches of 2,500-byte rows fill one chunk and start a second, which the error discards.
    timeout = pymysql.err.OperationalError(3024, 'maximum statement execution time exceeded')
    rows = [('x' * 2_500,) for _ in range(2 * FETCH_BATCH_ROWS)] + [timeout]
    check = _create_check(instance_basic, [_statement('s0', 'SELECT payload FROM blobs'), _statement('s1')])
    conn = FakeConnection({'SELECT payload FROM blobs': (['payload'], rows), 'SELECT 1': (['1'], [(1,)])})

    connect = _run(dd_run_check, check, conn)

    events = _events(aggregator)
    (chunk,) = _chunks(events, 's0')
    final = _final(events, 's0')
    assert (final['status'], final['error_kind'], final['error_code']) == ('error', 'statement_timeout', '3024')
    assert (final['chunk_count'], final['row_count']) == (1, len(chunk['rows']))
    assert 0 < len(chunk['rows']) < 2 * FETCH_BATCH_ROWS
    assert final['columns'] == []
    assert chunk['result_id'] == final['result_id']
    # The server ended the result with the error, so the next statement reuses the connection.
    assert _final(events, 's1')['status'] == 'success'
    assert connect.call_count == 1


def test_lost_connection_while_reading_reconnects(aggregator, dd_run_check, instance_basic):
    def lose_connection(conn):
        conn.open = False
        return pymysql.err.OperationalError(2013, 'Lost connection to MySQL server during query')

    check = _create_check(instance_basic, [_statement('s0', 'SELECT id FROM t'), _statement('s1')])
    first = FakeConnection({'SELECT id FROM t': (['id'], [(i,) for i in range(FETCH_BATCH_ROWS)] + [lose_connection])})
    second = FakeConnection({'SELECT 1': (['1'], [(1,)])})

    connect = _run(dd_run_check, check, first, second)

    events = _events(aggregator)
    lost = _final(events, 's0')
    assert (lost['status'], lost['error_kind'], lost['error_code']) == ('error', 'connection_error', '2013')
    assert _final(events, 's1')['status'] == 'success'
    assert connect.call_count == 2


def test_cancel_while_reading_closes_the_connection(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0', 'SELECT id FROM big'), _statement('s1')])
    conn = FakeConnection({'SELECT id FROM big': (['id'], [(i,) for i in range(5_000)]), 'SELECT 1': (['1'], [(1,)])})

    def cancel_on_second_read():
        if len(conn.fetch_sizes) == 2:
            check._cancelled = True

    conn.on_fetch = cancel_on_second_read

    _run(dd_run_check, check, conn)

    # No final event: the task is cancelled, so nobody waits for its results.
    assert not [event for event in _events(aggregator) if event.get('kind') == 'final']
    assert conn.fetch_sizes == [FETCH_BATCH_ROWS] * 2
    # The connection is closed instead of the cursor, which would read the remaining rows.
    assert not conn.open
    assert not conn.drained
    assert 'SELECT 1' not in conn.executed
    _assert_count(aggregator, check, 'dd.mysql.do_task.runs', 'outcome:cancelled')
    aggregator.assert_metric('dd.mysql.do_task.statements', count=0)


def test_final_event_carries_the_statement(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement(query='SELECT id FROM t')])

    _run(dd_run_check, check, FakeConnection({'SELECT id FROM t': (['id'], [(1,)])}))

    chunk, final = _events(aggregator)
    statement_fields = ('db_name', 'query', 'timeout_ms')
    assert not any(field in chunk for field in statement_fields)
    assert [final[field] for field in statement_fields] == ['shop', 'SELECT id FROM t', 300_000]


def test_session_sets_net_write_timeout(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement()])
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)])})

    _run(dd_run_check, check, conn)

    assert ('SET SESSION net_write_timeout = %s', (300,)) in conn.executed


@pytest.mark.parametrize(
    'value, expected',
    [
        pytest.param(None, None, id='null'),
        pytest.param(42, '42', id='int'),
        pytest.param(b'abc', 'abc', id='bytes'),
        pytest.param(b'\xff', '�', id='invalid-utf8'),
        pytest.param(Decimal('12.50'), '12.50', id='decimal'),
        pytest.param(Decimal('1E+2'), '100', id='decimal-exponent'),
        pytest.param(datetime.datetime(2026, 1, 1, 0, 49, 0, 5), '2026-01-01 00:49:00.000005', id='datetime'),
        pytest.param(datetime.date(2026, 1, 1), '2026-01-01', id='date'),
        pytest.param(datetime.timedelta(days=1, seconds=5, microseconds=10), '24:00:05.000010', id='time'),
        pytest.param(-datetime.timedelta(hours=1, minutes=2), '-01:02:00', id='negative-time'),
    ],
)
def test_values_are_rendered_as_text(value, expected):
    assert _to_text(value) == expected
