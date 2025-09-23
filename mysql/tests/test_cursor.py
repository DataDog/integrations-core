# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing

import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.cursor import CommenterCursor, CommenterDictCursor

from . import common


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_integration_connection_with_commenter_cursor(instance_basic, root_conn):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])

    with mysql_check._connect() as conn:
        # verify CommenterCursor and CommenterDictCursor prepend the query with /* service='datadog-agent' */
        query = 'SELECT name, enabled FROM performance_schema.setup_consumers WHERE name = %s'
        with closing(conn.cursor(CommenterCursor)) as cursor:
            cursor.execute(query, ('events_waits_current',))
            result = cursor.fetchone()
            assert result[0] == 'events_waits_current'
        __check_prepand_sql_comment(root_conn)

        with conn.cursor(CommenterDictCursor) as cursor:
            cursor.execute(query, ('events_waits_history',))
            result = cursor.fetchone()
            print(result)
            assert result['name'] == 'events_waits_history'
        __check_prepand_sql_comment(root_conn)

    mysql_check.cancel()


def __check_prepand_sql_comment(root_conn):
    # collect sql_text from performance_schema.events_statements_current
    # assert /* service='datadog-agent' */ is present in the query
    with closing(root_conn.cursor(CommenterCursor)) as cursor:
        cursor.execute(
            "SELECT sql_text FROM performance_schema.events_statements_current where sql_text like '%setup_consumers%'"
        )
        result = cursor.fetchall()
        assert len(result) > 0
        assert result[0][0].startswith('/* service=\'datadog-agent\' */')
