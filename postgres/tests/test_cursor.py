# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.postgres.cursor import CommenterCursor, CommenterDictCursor

from .utils import _get_superconn


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('ignore', [True, False])
def test_integration_connection_with_commenter_cursor(integration_check, pg_instance, ignore):
    check = integration_check(pg_instance)

    with check.db() as conn:
        # verify CommenterCursor and CommenterDictCursor prepend the query with /* service='datadog-agent' */
        with conn.cursor(cursor_factory=CommenterCursor) as cursor:
            cursor.execute(
                'SELECT name, setting FROM pg_settings where name = %s',
                ('pg_stat_statements.max',),
                ignore_query_metric=ignore,
            )
            result = cursor.fetchone()
            assert result[0] == 'pg_stat_statements.max'
        __check_prepand_sql_comment(pg_instance, ignore)

        with conn.cursor(cursor_factory=CommenterDictCursor) as cursor:
            cursor.execute(
                'SELECT name, setting FROM pg_settings where name = %s',
                ('max_connections',),
                ignore_query_metric=ignore,
            )
            result = cursor.fetchone()
            assert result['name'] == 'max_connections'
        __check_prepand_sql_comment(pg_instance, ignore)

    check.cancel()


def __check_prepand_sql_comment(pg_instance, ignore):
    # collect query_text from pg_stat_activity
    # assert /* service='datadog-agent' */ is present in the query
    super_conn = _get_superconn(pg_instance)
    with super_conn.cursor() as cursor:
        cursor.execute("SELECT query FROM pg_stat_activity where query like '%pg_settings%'")
        result = cursor.fetchall()
        assert len(result) > 0
        comment = '/* service=\'datadog-agent\' */'
        if ignore:
            comment = '{} {}'.format('/* DDIGNORE */', comment)
        assert result[0][0].startswith(comment)
    super_conn.close()
