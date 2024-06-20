import pytest
import pyodbc
import time
import sys
from datadog_checks.sqlserver import SQLServer

from .common import CHECK_NAME
from .conftest import DEFAULT_TIMEOUT

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

JOB_CREATION_QUERY="""\
EXEC msdb.dbo.sp_add_job
    @job_name = 'Job 1'
EXEC msdb.dbo.sp_add_jobstep
    @job_name = 'Job 1',
    @step_name = 'Wait for time 1',
    @subsystem = 'TSQL',
    @command = 'BEGIN  
                    WAITFOR DELAY ''00:00:15'';  
                    EXECUTE sp_helpdb;  
                END;';
EXEC msdb.dbo.sp_add_schedule  
    @schedule_name = 'Job 1 Schedule',  
    @freq_type = 4,
    @freq_interval = 1,
    @freq_subday_type = 4,
    @freq_subday_interval = 1;

EXEC msdb.dbo.sp_attach_schedule
   @job_name = 'Job 1',
   @schedule_name = 'Job 1 Schedule';

EXEC msdb.dbo.sp_add_jobserver
    @job_name = 'Job 1';
EXEC msdb.dbo.sp_add_job
    @job_name = 'Job 2'
"""

HISTORY_INSERTION_QUERY="""\
INSERT INTO msdb.dbo.sysjobhistory (
    job_id,
    step_id,
    step_name,
    sql_message_id,
    sql_severity,
    message,
    run_status,
    run_date,
    run_time,
    run_duration,
    operator_id_emailed,
    operator_id_netsent,
    operator_id_paged,
    retries_attempted,
    server
)
VALUES (
    -- Replace these values with actual data
    (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = 'Job {job_number}'),
    {step_id}, -- step_id
    'Step {step_id}', -- step_name
    0, -- sql_message_id
    0, -- sql_severity
    'Job executed successfully.', -- message
    1, -- run_status (1 = Succeeded, 0 = Failed, 3 = Canceled, 4 = In Progress)
    1, -- run_date in YYYYMMDD format
    1, -- run_time in HHMMSS format
    0, -- run_duration in HHMMSS format (e.g., 10100 for 1 hour 1 minute 0 seconds)
    0, -- operator_id_emailed
    0, -- operator_id_netsent
    0, -- operator_id_paged
    0, -- retries_attempted
    @@SERVERNAME -- server name
);
"""

ACTIVITY_INSERTION_QUERY="""\
INSERT INTO msdb.dbo.sysjobactivity (
    session_id,
    job_id,
    start_execution_date,
    last_executed_step_id,
    stop_execution_date
)
VALUES (
    1, -- New session_id
    (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = 'Job 2'), -- Replace with the actual job_history_id or NULL
    GETDATE(), -- start_execution_date,.
    1,
    NULL -- stop_execution_date (NULL for an active job)
);
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
            assert query == FORMATTED_HISTORY_QUERY
    check.cancel()

@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_activity_duration(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            cursor.execute(AGENT_ACTIVITY_DURATION_QUERY)
    check.cancel()

@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_activity_steps(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            cursor.execute(AGENT_ACTIVITY_STEPS_QUERY)
    check.cancel()

@pytest.mark.usefixtures('dd_environment')
def test_history_output(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])

    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};TrustServerCertificate=yes;'.format(
        instance_docker['driver'], instance_docker['host'], "sa", "Password123"
    )
    conn = pyodbc.connect(conn_str, timeout=DEFAULT_TIMEOUT, autocommit=True)
    sacursor = conn.cursor()
    sacursor.execute(JOB_CREATION_QUERY)
    sacursor.execute("SELECT * FROM msdb.dbo.sysjobs")
    results = sacursor.fetchall()
    assert len(results) == 2
    # job 1 completes once, job 2 completes twice, an instance of job 1 is still in progress
    # should result in 3 job history events to submit
    job_and_step_series = [(1, 1), (1, 2), (2, 1), (1, 0), (2, 0), (1, 1), (2, 1), (2, 0), (2, 1)]
    for (job_number, step_id) in (job_and_step_series):
        query = HISTORY_INSERTION_QUERY.format(job_number=job_number, step_id=step_id)
        sacursor.execute(query)

    check.initialize_connection()
    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            # instances start from 1
            last_instance_id_filter="\n\t\tHAVING MIN(sjh2.instance_id) > 0"
            query = AGENT_HISTORY_QUERY.format(last_instance_id_filter=last_instance_id_filter)
            cursor.execute(query)
            results = cursor.fetchall()
            assert len(results) == 7 # querying all completed job step entries
            assert len(results[0]) == 10 # 10 columns associated with this event 
            assert results[0][4] == 4 # completion instance of first entry
            assert results[0][3] == 1 # instance of first entry
            last_instance_id_filter="\n\t\tHAVING MIN(sjh2.instance_id) > 4"
            query = AGENT_HISTORY_QUERY.format(last_instance_id_filter=last_instance_id_filter)
            cursor.execute(query)
            results = cursor.fetchall()
            assert len(results) == 4 # querying all steps from jobs completed after instance 4
    check.cancel()

def test_agent_jobs_integration(aggregator, dd_run_check, instance_docker):
    instance_docker['dbm'] = True
    instance_docker['include_agent_jobs'] = True
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};TrustServerCertificate=yes;'.format(
        instance_docker['driver'], instance_docker['host'], "sa", "Password123"
    )
    conn = pyodbc.connect(conn_str, timeout=DEFAULT_TIMEOUT, autocommit=True)
    sacursor = conn.cursor()
    sacursor.execute("SELECT job_id FROM msdb.dbo.sysjobs WHERE name = 'Job 2'")
    job2_id = sacursor.fetchone()[0]
    sacursor.execute(ACTIVITY_INSERTION_QUERY)
    sacursor.execute("SELECT * FROM msdb.dbo.sysjobactivity")
    results = sacursor.fetchall()
    assert len(results) == 2
    for activity in results:
        if activity[1] != job2_id:
            continue
        assert activity[6] == 1
        
    dd_run_check(check)
    dbm_activity = aggregator.get_event_platform_events("dbm-samples")
    job_events = [e for e in dbm_activity if (e.get('sqlserver_job_history', None) is not None)]
    assert len(job_events) == 3
    aggregator.assert_metric("sqlserver.agent.active_jobs.duration", count=1)
    aggregator.assert_metric("sqlserver.agent.active_jobs.step_info", count=1)
    aggregator.assert_metric("sqlserver.agent.active_session.duration", count=1)
    # time.sleep(2)
    # dd_run_check(check)
    # aggregator.assert_metric("sqlserver.agent.active_jobs.duration", count=2)
    # aggregator.assert_metric("sqlserver.agent.active_jobs.step_info", count=2)
    # aggregator.assert_metric("sqlserver.agent.active_session.duration", count=2)
    dbm_activity = aggregator.get_event_platform_events("dbm-samples")
    job_events = [e for e in dbm_activity if (e.get('sqlserver_job_history', None) is not None)]
    assert len(job_events) == 3 # successive checks should not create new events for same history entries