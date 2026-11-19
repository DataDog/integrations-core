# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.postgres.cursor import LEADING_COMMENTS_STRIPPED_SERVER_VERSION_NUM, _add_comments

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
