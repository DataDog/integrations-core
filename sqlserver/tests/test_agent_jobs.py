import pytest
import sys
from datadog_checks.sqlserver import SQLServer

from .common import CHECK_NAME

AGENT_HISTORY_QUERY = """\
SELECT 
    sjh1.job_id,
    sjh1.step_id,
    sjh1.step_name,
    sjh1.instance_id AS step_instance_id,
    (
        SELECT MIN(sjh2.instance_id)
        FROM msdb.dbo.sysjobhistory AS sjh2
        WHERE sjh2.job_id = sjh1.job_id
        AND sjh2.step_id = 0
        AND sjh2.instance_id >= sjh1.instance_id
    ) AS completion_instance_id,
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
        AND sjh2.instance_id >= sjh1.instance_id{last_instance_id_filter}
    )
"""

FORMATTED_HISTORY_QUERY = """\
SELECT 
    sjh1.job_id,
    sjh1.step_id,
    sjh1.step_name,
    sjh1.instance_id AS step_instance_id,
    (
        SELECT MIN(sjh2.instance_id)
        FROM msdb.dbo.sysjobhistory AS sjh2
        WHERE sjh2.job_id = sjh1.job_id
        AND sjh2.step_id = 0
        AND sjh2.instance_id >= sjh1.instance_id
    ) AS completion_instance_id,
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
        AND sjh2.instance_id >= sjh1.instance_id
\t\tHAVING MIN(sjh2.instance_id) > 26220
    )
"""

AGENT_ACTIVITY_DURATION_QUERY = """\
SELECT
    ja.job_id,
    DATEDIFF(SECOND, ja.start_execution_date, GETDATE()) AS duration_seconds
FROM
    msdb.dbo.sysjobactivity AS ja
WHERE
    ja.start_execution_date IS NOT NULL
    AND ja.stop_execution_date IS NULL
    AND session_id = (
        SELECT MAX(session_id) 
        FROM msdb.dbo.sysjobactivity
    )
"""

AGENT_ACTIVITY_STEPS_QUERY = """\
    WITH ActiveJobs AS (
        SELECT
            ja.job_id,
            last_executed_step_id
        FROM msdb.dbo.sysjobactivity AS ja
        WHERE ja.start_execution_date IS NOT NULL
            AND ja.stop_execution_date IS NULL
            AND session_id = (
                SELECT MAX(session_id) 
                FROM msdb.dbo.sysjobactivity
            )
    ),
    CompletedSteps AS (
        SELECT
            sjh1.job_id,
            sjh1.step_id,
            sjh1.step_name,
            sjh1.run_status
        FROM msdb.dbo.sysjobhistory AS sjh1
        WHERE NOT EXISTS (
            SELECT 1
            FROM msdb.dbo.sysjobhistory AS sjh2
            WHERE sjh2.job_id = sjh1.job_id
                AND sjh2.step_id = 0
                AND sjh2.instance_id > sjh1.instance_id
            )
    )
    SELECT
        aj.job_id,
        cs.step_name,
        cs.step_id,
        cs.run_status AS step_run_status,
        1 AS step_info
    FROM ActiveJobs AS aj
    INNER JOIN CompletedSteps AS cs
    ON aj.job_id = cs.job_id
        AND aj.last_executed_step_id = cs.step_id
"""

@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_history(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            last_instance_id_filter="\n\t\tHAVING MIN(sjh2.instance_id) > 26220"
            query = AGENT_HISTORY_QUERY.format(last_instance_id_filter=last_instance_id_filter)
            cursor.execute(query)
            result = cursor.fetchone()
            assert query == FORMATTED_HISTORY_QUERY
    check.cancel()

@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_activity_duration(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            cursor.execute(AGENT_ACTIVITY_DURATION_QUERY)
            result = cursor.fetchall()
            assert 1 == 1
    check.cancel()

@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_activity_steps(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            cursor.execute(AGENT_ACTIVITY_STEPS_QUERY)
            result = cursor.fetchall()
            assert 1 == 1
    check.cancel()