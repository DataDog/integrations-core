# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import psycopg
import pytest

from datadog_checks.postgres.cursor import (
    LEADING_COMMENTS_STRIPPED_SERVER_VERSION_NUM,
    BaseCommenterCursor,
    _add_comments,
    _stores_leading_comments,
)

from .utils import _get_superconn

SERVICE = {'service': 'datadog-agent'}


@pytest.mark.parametrize(
    'query, ignore, leading, expected',
    [
        pytest.param(
            'SELECT 1',
            False,
            True,
            "/* service='datadog-agent' */ SELECT 1",
            id='leading',
        ),
        pytest.param(
            'SELECT 1',
            True,
            True,
            "/* DDIGNORE */ /* service='datadog-agent' */ SELECT 1",
            id='leading_ignored',
        ),
        pytest.param(
            'SELECT 1',
            False,
            False,
            "SELECT 1 /* service='datadog-agent' */",
            id='trailing',
        ),
        pytest.param(
            'SELECT 1',
            True,
            False,
            "SELECT 1 /* service='datadog-agent' */ /* DDIGNORE */",
            id='trailing_ignored',
        ),
        # pg_stat_statements discards anything after the terminating semicolon, taking the comments with it.
        pytest.param(
            'SELECT 1;\n',
            True,
            False,
            "SELECT 1 /* service='datadog-agent' */ /* DDIGNORE */;",
            id='trailing_ignored_semicolon',
        ),
    ],
)
def test_add_comments(query, ignore, leading, expected):
    assert _add_comments(query, SERVICE, ignore, leading) == expected


class _FakeInfo:
    def __init__(self, server_version):
        self._server_version = server_version

    @property
    def server_version(self):
        if isinstance(self._server_version, Exception):
            raise self._server_version
        return self._server_version


class _FakeConnection:
    def __init__(self, server_version):
        self.info = _FakeInfo(server_version)


class _RecordingCursor:
    """Stands in for psycopg.ClientCursor, recording the queries that reach the server."""

    def __init__(self, connection):
        self.connection = connection
        self.executed = []

    def execute(self, query, params=None, binary=False, prepare=None):
        self.executed.append(query)


class _FakeCommenterCursor(BaseCommenterCursor, _RecordingCursor):
    pass


@pytest.mark.parametrize(
    'server_version, expected_leading',
    [
        pytest.param(170012, True, id='pg17'),
        pytest.param(180007, False, id='pg18'),
        # libpq reports 0 when it has no usable connection state.
        pytest.param(0, True, id='no_version'),
        pytest.param(psycopg.OperationalError('the connection is closed'), True, id='closed_connection'),
    ],
)
def test_stores_leading_comments(server_version, expected_leading):
    assert _stores_leading_comments(_FakeCommenterCursor(_FakeConnection(server_version))) is expected_leading


def test_execute_still_sends_the_query_when_the_server_version_is_unreadable():
    """Reading the version runs before every query, so a failure must leave the query to report its own error."""
    cursor = _FakeCommenterCursor(_FakeConnection(psycopg.OperationalError('the connection is closed')))

    cursor.execute('SELECT 1', ignore_query_metric=True)

    assert cursor.executed == ["/* DDIGNORE */ /* service='datadog-agent' */ SELECT 1"]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('ignore', [True, False])
def test_integration_connection_with_commenter_cursor(integration_check, pg_instance, ignore):
    pg_instance['application_name'] = 'test_integration_connection_with_commenter_cursor_{}'.format(ignore)
    check = integration_check(pg_instance)

    with check.db() as conn:
        conn.execute("SET client_encoding TO 'UTF8'")
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT generate_series(1, 10) AS number',
                ignore_query_metric=ignore,
            )
            result = cursor.fetchone()
            assert isinstance(result[0], int)
        __check_prepand_sql_comment(pg_instance, ignore)

        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT generate_series(1, 10) AS number',
                ignore_query_metric=ignore,
            )
            result = cursor.fetchone()
            assert isinstance(result[0], int)
        __check_prepand_sql_comment(pg_instance, ignore)

    check.cancel()


def __check_prepand_sql_comment(pg_instance, ignore):
    # collect query_text from pg_stat_activity
    # assert /* service='datadog-agent' */ is present in the query
    super_conn = _get_superconn(pg_instance)
    super_conn.execute("SET client_encoding TO 'UTF8'")
    with super_conn.cursor() as cursor:
        cursor.execute(
            (
                "SELECT query FROM pg_stat_activity where application_name = %s and query like '%%generate_series%%' "
                "and query not like '%%pg_stat_activity%%'"
            ),
            (pg_instance['application_name'],),
        )
        result = cursor.fetchall()
        assert len(result) > 0
        text = result[0][0]
        if super_conn.info.server_version >= LEADING_COMMENTS_STRIPPED_SERVER_VERSION_NUM:
            assert text.endswith("/* service='datadog-agent' */" + (' /* DDIGNORE */' if ignore else ''))
        else:
            assert text.startswith(('/* DDIGNORE */ ' if ignore else '') + "/* service='datadog-agent' */")
    super_conn.close()
