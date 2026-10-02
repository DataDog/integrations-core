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
from datadog_checks.mysql.do_task import MAX_EVENT_BYTES, MAX_TASK_STATEMENT_ROWS, _to_text

from . import common

pytestmark = pytest.mark.unit

CONFIG_ID = 'do-mysql-once-3f1c2a9e-8b7d-4c1e-9f2a-6d5e4c3b2a10'
TASK_ID = '3f1c2a9e-8b7d-4c1e-9f2a-6d5e4c3b2a10'
MYSQL_8 = ('8.0.36', 'MySQL Community Server - GPL')


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


class FakeConnection:
    """
    Stands in for a pymysql connection. `results` maps SQL text to `(columns, rows)`, to an
    exception to raise, or to a callable taking the connection that does either. Any other
    statement succeeds without a result set.
    """

    def __init__(self, results=None, version=MYSQL_8):
        self.results = results or {}
        self.version = version
        self.open = True
        self.executed = []
        self.fetch_sizes = []
        self.cursor_classes = []

    def cursor(self, cursor_class=None):
        self.cursor_classes.append(cursor_class)
        return FakeCursor(self)

    def close(self):
        if not self.open:
            raise pymysql.err.Error('Already closed')
        self.open = False


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = None
        self.rows = []
        self.fetched = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def execute(self, sql, args=None):
        self.conn.executed.append(sql if args is None else (sql, args))
        self.description, self.rows, self.fetched = None, [], 0
        if sql.startswith('SELECT @@version'):
            self.description, self.rows = [('@@version',), ('@@version_comment',)], [self.conn.version]
            return
        result = self.conn.results.get(sql)
        if callable(result):
            result = result(self.conn)
        if isinstance(result, BaseException):
            raise result
        if result is not None:
            columns, self.rows = result
            self.description = [(column,) for column in columns]

    def fetchone(self):
        return self.rows[0]

    def fetchmany(self, size):
        self.conn.fetch_sizes.append(size)
        batch = self.rows[self.fetched : self.fetched + size]
        self.fetched += len(batch)
        return batch

    def close(self):
        pass


def _run(dd_run_check, check, *connections):
    with patch('datadog_checks.mysql.do_task.connect_with_session_variables', side_effect=list(connections)) as connect:
        dd_run_check(check)
    return connect


def _events(aggregator):
    return aggregator.get_event_platform_events(EVENT_TRACK_TYPE)


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
    assert conn.executed[:4] == [
        'SELECT @@version, @@version_comment',
        'SET SESSION TRANSACTION READ ONLY',
        "SET time_zone = '+00:00'",
        ('SET SESSION max_execution_time = %s', (300_000,)),
    ]
    assert 'USE `shop`' in conn.executed
    assert not conn.open

    first, second = _events(aggregator)
    assert first == {
        'timestamp': first['timestamp'],
        'config_id': CONFIG_ID,
        'task_id': TASK_ID,
        'statement_id': 's0',
        'result_id': first['result_id'],
        'chunk_index': 0,
        'chunk_count': 1,
        'db_type': 'mysql',
        'db_host': 'mysql.test',
        'db_port': common.PORT,
        'db_name': 'shop',
        'query': 'SELECT id, name FROM customers',
        'timeout_ms': 300_000,
        'status': 'success',
        'columns': ['id', 'name'],
        'rows': [['1', 'ada'], ['2', None]],
        'row_count': 2,
        'duration_s': first['duration_s'],
        'error': None,
        'error_kind': None,
        'error_code': None,
    }
    assert (second['statement_id'], second['rows']) == ('s1', [['42']])
    assert first['result_id'] != second['result_id']

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
    _assert_count(aggregator, check, 'dd.mysql.do_task.events', count=2)
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
    for tag in _metric_tags(check):
        assert TASK_ID not in tag
    aggregator.assert_metric('dd.mysql.do_task.emit_failures', count=0)


def test_failed_emit_is_counted_and_the_task_continues(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0', 'SELECT 1'), _statement('s1', 'SELECT 2')])
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)]), 'SELECT 2': (['2'], [(2,)])})

    with patch.object(check, 'event_platform_event', side_effect=[ValueError('boom'), None]):
        _run(dd_run_check, check, conn)

    _assert_count(aggregator, check, 'dd.mysql.do_task.emit_failures', 'exc_class:ValueError')
    _assert_count(aggregator, check, 'dd.mysql.do_task.events')
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

    first, second = _events(aggregator)
    assert first['statement_id'] == second['statement_id'] == 's0'
    assert first['result_id'] != second['result_id']
    assert str(uuid.UUID(first['result_id'])) == first['result_id']


def test_database_names_are_quoted(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0', dbname='shop-eu'), _statement('s1', dbname='odd`name')])
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)])})

    _run(dd_run_check, check, conn)

    assert 'USE `shop-eu`' in conn.executed
    assert 'USE `odd``name`' in conn.executed
    assert [event['status'] for event in _events(aggregator)] == ['success', 'success']


def test_failed_statement_does_not_stop_the_others(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0', 'SELECT nope'), _statement('s1', 'SELECT 1')])
    conn = FakeConnection(
        {
            'SELECT nope': pymysql.err.OperationalError(1054, "Unknown column 'nope' in 'field list'"),
            'SELECT 1': (['1'], [(1,)]),
        }
    )

    connect = _run(dd_run_check, check, conn)

    failed, succeeded = _events(aggregator)
    assert (failed['status'], failed['error_kind'], failed['error_code']) == ('error', 'sql_error', '1054')
    assert failed['rows'] == []
    assert (succeeded['status'], succeeded['rows']) == ('success', [['1']])
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
        pytest.param(MAX_TASK_STATEMENT_ROWS, MAX_TASK_STATEMENT_ROWS, id='hard-cap'),
    ],
)
def test_rows_up_to_the_limit_are_returned(aggregator, dd_run_check, instance_basic, max_rows, row_count):
    check = _create_check(instance_basic, [_statement(query='SELECT id FROM t', max_rows=max_rows)])
    conn = FakeConnection({'SELECT id FROM t': (['id'], [(i,) for i in range(row_count)])})

    _run(dd_run_check, check, conn)

    events = _events(aggregator)
    assert all(event['status'] == 'success' for event in events)
    assert sum(event['row_count'] for event in events) == row_count


@pytest.mark.parametrize(
    'max_rows, limit',
    [
        pytest.param(5, 5, id='max-rows'),
        pytest.param(MAX_TASK_STATEMENT_ROWS, MAX_TASK_STATEMENT_ROWS, id='hard-cap'),
        pytest.param(MAX_TASK_STATEMENT_ROWS * 2, MAX_TASK_STATEMENT_ROWS, id='max-rows-above-hard-cap'),
    ],
)
def test_rows_past_the_limit_are_not_returned(aggregator, dd_run_check, instance_basic, max_rows, limit):
    check = _create_check(
        instance_basic,
        [_statement('s0', 'SELECT id FROM big', max_rows=max_rows), _statement('s1', 'SELECT 1')],
    )
    conn = FakeConnection(
        {'SELECT id FROM big': (['id'], [(i,) for i in range(limit + 100)]), 'SELECT 1': (['1'], [(1,)])}
    )

    connect = _run(dd_run_check, check, conn)

    events = _events(aggregator)
    limited = [event for event in events if event['statement_id'] == 's0']
    assert all(event['status'] == 'success' for event in events)
    assert [row for event in limited for row in event['rows']] == [[str(i)] for i in range(limit)]
    assert conn.fetch_sizes[0] == limit
    # The next statement runs on the same connection.
    assert connect.call_count == 1


def test_connect_failure_reports_every_statement(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0'), _statement('s1')])

    _run(dd_run_check, check, pymysql.err.OperationalError(2003, "Can't connect to MySQL server"))

    events = _events(aggregator)
    assert [event['statement_id'] for event in events] == ['s0', 's1']
    assert len({event['result_id'] for event in events}) == 2
    for event in events:
        assert (event['error_kind'], event['error_code']) == ('connection_error', '2003')
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

    lost, succeeded = _events(aggregator)
    assert (lost['error_kind'], lost['error_code']) == ('connection_error', code)
    assert succeeded['status'] == 'success'
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

    rejected, succeeded = _events(aggregator)
    assert (rejected['status'], rejected['error_kind']) == ('error', 'sql_error')
    assert not first.open
    assert connect.call_count == 2
    assert succeeded['status'] == 'success'


def test_expired_task_reports_a_task_error_without_connecting(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement()], expires_at=int(time.time()) - 1)

    connect = _run(dd_run_check, check)

    (event,) = _events(aggregator)
    assert 'statement_id' not in event
    assert 'result_id' not in event
    assert (event['task_id'], event['status'], event['error_kind']) == (TASK_ID, 'error', 'expired')
    assert (event['chunk_index'], event['chunk_count']) == (0, 1)
    connect.assert_not_called()
    _assert_count(aggregator, check, 'dd.mysql.do_task.runs', 'outcome:expired')
    _assert_count(aggregator, check, 'dd.mysql.do_task.events')
    aggregator.assert_metric('dd.mysql.do_task.statements', count=0)


def test_cancelled_check_skips_the_remaining_statements(aggregator, dd_run_check, instance_basic):
    check = _create_check(instance_basic, [_statement('s0', 'SELECT 1'), _statement('s1', 'SELECT 2')])

    def cancel_during_first_statement(conn):
        check._cancelled = True
        return (['1'], [(1,)])

    conn = FakeConnection({'SELECT 1': cancel_during_first_statement, 'SELECT 2': (['2'], [(2,)])})

    _run(dd_run_check, check, conn)

    assert [event['statement_id'] for event in _events(aggregator)] == ['s0']
    assert 'SELECT 2' not in conn.executed
    _assert_count(aggregator, check, 'dd.mysql.do_task.runs', 'outcome:cancelled')
    aggregator.assert_metric('dd.mysql.do_task.runs', tags=_metric_tags(check, 'outcome:completed'), count=0)


def test_large_results_are_split_into_chunks(aggregator, dd_run_check, instance_basic):
    rows = [(str(i) * (MAX_EVENT_BYTES // 3),) for i in range(5)]
    check = _create_check(instance_basic, [_statement(query='SELECT payload FROM blobs')])

    _run(dd_run_check, check, FakeConnection({'SELECT payload FROM blobs': (['payload'], rows)}))

    raw_events = aggregator.get_event_platform_events(EVENT_TRACK_TYPE, parse_json=False)
    assert all(len(raw) <= MAX_EVENT_BYTES for raw in raw_events)
    events = [json.loads(raw) for raw in raw_events]
    assert len(events) > 1
    assert [event['chunk_index'] for event in events] == list(range(len(events)))
    assert {event['chunk_count'] for event in events} == {len(events)}
    assert len({event['result_id'] for event in events}) == 1
    assert all(event['row_count'] == len(event['rows']) for event in events)
    assert [row for event in events for row in event['rows']] == [[value] for (value,) in rows]


@pytest.mark.parametrize(
    'version, expected',
    [
        pytest.param(MYSQL_8, ('SET SESSION max_execution_time = %s', (300_000,)), id='mysql-milliseconds'),
        pytest.param(
            ('10.6.12-MariaDB', 'mariadb.org binary distribution'),
            ('SET SESSION max_statement_time = %s', (300,)),
            id='mariadb-seconds',
        ),
        pytest.param(('5.6.51-log', 'MySQL Community Server (GPL)'), None, id='mysql-without-max-execution-time'),
    ],
)
def test_statement_timeout_uses_the_server_variable(aggregator, dd_run_check, instance_basic, version, expected):
    check = _create_check(instance_basic, [_statement()])
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)])}, version=version)

    _run(dd_run_check, check, conn)

    timeouts = [sql for sql in conn.executed if isinstance(sql, tuple)]
    assert timeouts == ([expected] if expected else [])


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
