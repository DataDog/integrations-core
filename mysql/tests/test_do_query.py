# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pymysql
import pytest

from datadog_checks.mysql.cursor import CommenterSSCursor
from datadog_checks.mysql.do_query import FETCH_BATCH_ROWS, MAX_RESULT_ROWS, DOQuerySession, NoResultSetError
from datadog_checks.mysql.version_utils import parse_version

from .do_fakes import MYSQL_8, FakeConnection, FakeCursor

pytestmark = pytest.mark.unit


def _session(conn, version=MYSQL_8):
    server_version = parse_version(*version)
    return DOQuerySession(conn, server_version, server_version.flavor == 'MariaDB')


def _settings(conn):
    return [sql for sql in conn.executed if isinstance(sql, tuple)]


def test_query_runs_with_server_side_row_limit():
    # The server stops at the row limit instead of producing rows that would only be thrown away.
    conn = FakeConnection({'SELECT id FROM big': (['id'], [(i,) for i in range(20)])})

    columns, rows = _session(conn).run('shop', 'SELECT id FROM big', 30_000, max_rows=5)

    assert ('SET SESSION sql_select_limit = %s', (5,)) in _settings(conn)
    assert (columns, rows) == (['id'], [(i,) for i in range(5)])
    assert CommenterSSCursor in conn.cursor_classes


def test_run_reads_the_rows_in_one_call():
    # The monitor path reads its whole capped result with a single fetchmany().
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)])})

    _session(conn).run('shop', 'SELECT 1', 30_000, max_rows=MAX_RESULT_ROWS)

    assert ('SET SESSION sql_select_limit = %s', (MAX_RESULT_ROWS,)) in _settings(conn)
    assert conn.fetch_sizes == [MAX_RESULT_ROWS]


def _rows(count):
    return [(i,) for i in range(count)]


def test_stream_reads_in_batches():
    conn = FakeConnection({'SELECT id FROM t': (['id'], _rows(2_500))})

    columns, batches = _session(conn).stream('shop', 'SELECT id FROM t', 30_000, max_rows=1_000_000)

    assert columns == ['id']
    assert [len(batch) for batch in batches] == [1_000, 1_000, 500]
    assert conn.fetch_sizes == [1_000, 1_000, 1_000]


def test_stream_stops_at_max_rows():
    conn = FakeConnection({'SELECT id FROM t': (['id'], _rows(3_000))})

    _, batches = _session(conn).stream('shop', 'SELECT id FROM t', 30_000, max_rows=2_000)

    assert [row for batch in batches for row in batch] == _rows(2_000)
    assert conn.fetch_sizes == [1_000, 1_000]
    assert ('SET SESSION sql_select_limit = %s', (2_000,)) in _settings(conn)


def test_stream_never_fetches_everything_at_once():
    conn = FakeConnection({'SELECT id FROM t': (['id'], _rows(50_000))})

    _, batches = _session(conn).stream('shop', 'SELECT id FROM t', 30_000, max_rows=1_000_000)

    assert sum(len(batch) for batch in batches) == 50_000
    assert max(conn.fetch_sizes) == FETCH_BATCH_ROWS


@pytest.mark.parametrize(
    'query, results, error',
    [
        pytest.param('SET SESSION TRANSACTION READ WRITE', {}, NoResultSetError, id='no-result-set'),
        pytest.param(
            'SELECT nope',
            {'SELECT nope': pymysql.err.OperationalError(1054, "Unknown column 'nope'")},
            pymysql.err.OperationalError,
            id='server-error',
        ),
    ],
)
def test_stream_error_before_result_set_raises_from_stream(query, results, error):
    with pytest.raises(error):
        _session(FakeConnection(results)).stream('shop', query, 30_000, max_rows=10)


def test_stream_error_while_reading_closes_the_cursor():
    timeout = pymysql.err.OperationalError(3024, 'maximum statement execution time exceeded')
    conn = FakeConnection({'SELECT id FROM t': (['id'], _rows(1_000) + [timeout])})
    session = _session(conn)

    _, batches = session.stream('shop', 'SELECT id FROM t', 30_000, max_rows=1_000_000)

    assert len(next(batches)) == 1_000
    with pytest.raises(pymysql.err.OperationalError):
        list(batches)
    assert not conn.drained
    # The server ended the result with the error, so the connection can run the next query.
    assert session.usable


def test_stream_closed_early_does_not_drain():
    conn = FakeConnection({'SELECT id FROM t': (['id'], _rows(5_000))})
    session = _session(conn)

    _, batches = session.stream('shop', 'SELECT id FROM t', 30_000, max_rows=1_000_000)
    next(batches)
    batches.close()

    assert conn.fetch_sizes == [1_000]
    assert not conn.drained
    assert not session.usable


@pytest.mark.parametrize(
    'version, expected',
    [
        pytest.param(MYSQL_8, ('SET SESSION max_execution_time = %s', (30_000,)), id='mysql-milliseconds'),
        pytest.param(
            ('10.6.12-MariaDB', 'mariadb.org binary distribution'),
            ('SET SESSION max_statement_time = %s', (30.0,)),
            id='mariadb-seconds',
        ),
        pytest.param(('5.6.51-log', 'MySQL Community Server (GPL)'), None, id='mysql-without-max-execution-time'),
    ],
)
def test_statement_timeout_uses_the_server_variable(version, expected):
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)])}, version=version)

    _session(conn, version).run('shop', 'SELECT 1', 30_000, max_rows=10)

    timeouts = [setting for setting in _settings(conn) if 'sql_select_limit' not in setting[0]]
    assert timeouts == ([expected] if expected else [])


def test_session_settings_change_only_when_a_query_needs_other_values():
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)])})
    session = _session(conn)

    session.run('shop', 'SELECT 1', 30_000, max_rows=10)
    session.run('shop', 'SELECT 1', 30_000, max_rows=10)
    session.run('shop-eu', 'SELECT 1', 60_000, max_rows=10)

    assert _settings(conn) == [
        ('SET SESSION max_execution_time = %s', (30_000,)),
        ('SET SESSION sql_select_limit = %s', (10,)),
        ('SET SESSION max_execution_time = %s', (60_000,)),
    ]
    assert [sql for sql in conn.executed if isinstance(sql, str) and sql.startswith('USE')] == [
        'USE `shop`',
        'USE `shop-eu`',
    ]


@pytest.mark.parametrize(
    'dbname, expected',
    [
        pytest.param('shop-eu', 'USE `shop-eu`', id='dash'),
        pytest.param('odd`name', 'USE `odd``name`', id='backtick'),
    ],
)
def test_database_names_are_quoted(dbname, expected):
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)])})

    _session(conn).run(dbname, 'SELECT 1', 30_000, max_rows=10)

    assert expected in conn.executed


def test_query_without_result_set_raises():
    conn = FakeConnection()

    with pytest.raises(NoResultSetError):
        _session(conn).run('shop', 'SET SESSION TRANSACTION READ WRITE', 30_000, max_rows=10)


def test_failed_cursor_close_makes_the_session_unusable(monkeypatch):
    # The connection may be left mid-result, so the caller must not run another query on it.
    error = pymysql.err.OperationalError(1317, 'Query execution was interrupted')
    conn = FakeConnection({'SELECT 1': error})
    session = _session(conn)

    def close_fails(cursor):
        # Only the query's cursor fails to close; the session's SET statements close normally.
        if cursor.conn.executed[-1] == 'SELECT 1':
            raise pymysql.err.InterfaceError(0, '')

    monkeypatch.setattr(FakeCursor, 'close', close_fails)

    with pytest.raises(pymysql.err.OperationalError):
        session.run('shop', 'SELECT 1', 30_000, max_rows=10)
    assert not session.usable
