# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.sqlserver import SQLServer

from .common import CHECK_NAME


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_integration_connection_with_commenter_cursor(instance_docker, sa_conn):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            cursor.execute("SELECT /* testcomments */ count(*) from sys.databases where name = 'master'")
            result = cursor.fetchone()
            assert result[0] == 1
            __check_prepand_sql_comment(sa_conn)

    check.cancel()


def __check_prepand_sql_comment(sa_conn):
    # collect text from dm_exec_requests CROSS APPLY sys.dm_exec_sql_text(sql_handle)
    # assert /* service='datadog-agent' */ is present in the query
    with sa_conn as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    st.text
                FROM
                    sys.dm_exec_query_stats AS qs
                CROSS APPLY
                    sys.dm_exec_sql_text(qs.sql_handle) AS st
                WHERE st.text LIKE '%testcomments%'
                """
            )
            result = cursor.fetchall()
            assert len(result) > 0
            assert result[0][0].startswith('/* service=\'datadog-agent\' */')
