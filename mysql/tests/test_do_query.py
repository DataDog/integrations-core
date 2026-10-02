# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pymysql
import pytest

from datadog_checks.mysql.cursor import CommenterSSCursor
from datadog_checks.mysql.do_query import MAX_RESULT_ROWS, DOQuerySession, NoResultSetError
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


def test_row_limit_is_capped():
    conn = FakeConnection({'SELECT 1': (['1'], [(1,)])})

    _session(conn).run('shop', 'SELECT 1', 30_000, max_rows=MAX_RESULT_ROWS * 2)

    assert ('SET SESSION sql_select_limit = %s', (MAX_RESULT_ROWS,)) in _settings(conn)
    assert conn.fetch_sizes == [MAX_RESULT_ROWS]


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
