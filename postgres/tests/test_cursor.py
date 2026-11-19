# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.postgres.cursor import _append_ddignore_comment

from .utils import _get_superconn


@pytest.mark.parametrize(
    'query, expected',
    [
        pytest.param('SELECT 1', 'SELECT 1 /* DDIGNORE */', id='no_semicolon'),
        # pg_stat_statements discards anything after the terminating semicolon, taking the marker with it.
        pytest.param('SELECT 1;', 'SELECT 1 /* DDIGNORE */;', id='semicolon'),
        pytest.param('SELECT 1 ;  \n', 'SELECT 1 /* DDIGNORE */;', id='semicolon_whitespace'),
    ],
)
def test_append_ddignore_comment(query, expected):
    assert _append_ddignore_comment(query) == expected


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
        assert result[0][0].startswith('/* service=\'datadog-agent\' */')
        # Postgres 18 strips leading comments from pg_stat_statements text, so the marker must trail the query.
        assert result[0][0].endswith('/* DDIGNORE */') == ignore
    super_conn.close()
