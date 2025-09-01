# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .utils import _get_superconn

@pytest.mark.integration
@pytest.mark.flaky
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('ignore', [True, False])
def test_integration_connection_with_commenter_cursor(integration_check, pg_instance, ignore):
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
    app = 'generate_series'
    super_conn = _get_superconn(pg_instance, application_name=app)
    super_conn.execute("SET client_encoding TO 'UTF8'")
    with super_conn.cursor() as cursor:
        cursor.execute(
            (
                "SELECT query FROM pg_stat_activity where query like '%generate_series%' "
                "and query not like '%%pg_stat_activity%%'"
            )
        )
        result = cursor.fetchall()
        assert len(result) > 0
        comment = '/* service=\'datadog-agent\' */'
        if ignore:
            comment = '{} {}'.format('/* DDIGNORE */', comment)
        assert result[0][0].startswith(comment)
    super_conn.close()
    super_conn = _get_superconn(pg_instance, application_name="test_connection")
    with super_conn.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE application_name = %s", (app,))
        result = cursor.fetchone()
        assert result[0] == 0, f"Expected no active sessions for application_name={app}, found {result[0]}"
    super_conn.close()
