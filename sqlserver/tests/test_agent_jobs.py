import pytest
import sys
from datadog_checks.sqlserver import SQLServer

from .common import CHECK_NAME

AGENT_TEST_QUERY = """\
SELECT 
    sjh1.instance_id AS current_instance_id,
    (
        SELECT MIN(sjh2.instance_id)
        FROM msdb.dbo.sysjobhistory AS sjh2
        WHERE sjh2.job_id = sjh1.job_id
        AND sjh2.step_id = 0
        AND sjh2.instance_id >= sjh1.instance_id
    ) AS next_instance_id_with_step_0,
    sjh1.job_id,
    sjh1.step_id,
    sjh1.step_name,
    sjh1.run_date,
    sjh1.run_time,
    sjh1.run_duration,
    sjh1.run_status,
    sjh1.message
FROM 
    msdb.dbo.sysjobhistory AS sjh1
WHERE
    EXISTS (
        SELECT 1
        FROM msdb.dbo.sysjobhistory AS sjh2
        WHERE sjh2.job_id = sjh1.job_id
        AND sjh2.step_id = 0
        AND sjh2.instance_id > sjh1.instance_id
    ){last_instance_id_filter}
"""

@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_tables(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            last_instance_id_filter="\nAND\n\tsjh1.instance_id > 21000"
            query = AGENT_TEST_QUERY.format(last_instance_id_filter=last_instance_id_filter)
            cursor.execute(query)
            result = cursor.fetchone()
            assert 1 == 1
    check.cancel()
