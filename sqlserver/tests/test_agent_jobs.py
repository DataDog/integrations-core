import pytest

from datadog_checks.sqlserver import SQLServer

from .common import CHECK_NAME

@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_tables(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            cursor.execute("SELECT * from msdb.dbo.sysjobs")
            result = cursor.fetchone()
            print(result)
            assert 1 == 1
    check.cancel()
