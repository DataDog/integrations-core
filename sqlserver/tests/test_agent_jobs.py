import pytest
import time
from datadog_checks.sqlserver import SQLServer

from .common import (
    CHECK_NAME,
    EXPECTED_AGENT_JOBS_METRICS_COMMON,
)

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
\t\tHAVING MIN(sjh2.instance_id) > 10
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

JOB_CREATION_QUERY = """\
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

HISTORY_INSERTION_QUERY = """\
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

ACTIVITY_INSERTION_QUERY = """\
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
            last_instance_id_filter = "\n\t\tHAVING MIN(sjh2.instance_id) > 10"
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
def test_history_output(instance_docker, sa_conn):
    with sa_conn as conn:
        with conn.cursor() as cursor:
            cursor.execute(JOB_CREATION_QUERY)
            cursor.execute("SELECT * FROM msdb.dbo.sysjobs")
            results = cursor.fetchall()
            assert len(results) == 2
            # job 1 completes once, job 2 completes twice, an instance of job 1 is still in progress
            # should result in 7 steps of job history events to submit
            job_and_step_series = [(1, 1), (1, 2), (2, 1), (1, 0), (2, 0), (1, 1), (2, 1), (2, 0), (2, 1)]
            for job_number, step_id in job_and_step_series:
                query = HISTORY_INSERTION_QUERY.format(job_number=job_number, step_id=step_id)
                cursor.execute(query)

    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()
    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            last_instance_id_filter = "\n\t\tHAVING MIN(sjh2.instance_id) > 0"
            query = AGENT_HISTORY_QUERY.format(last_instance_id_filter=last_instance_id_filter)
            cursor.execute(query)
            results = cursor.fetchall()
            assert len(results) == 7, "should have 7 steps associated with completed jobs"
            assert len(results[0]) == 10, "should have 10 columns per step"
            last_instance_id_filter="\n\t\tHAVING MIN(sjh2.instance_id) > 4"
            query = AGENT_HISTORY_QUERY.format(last_instance_id_filter=last_instance_id_filter)
            cursor.execute(query)
            results = cursor.fetchall()
            assert (
                len(results) == 4
                ), "should only have 4 steps associated with completed jobs when filtering with minimum instance_id, all steps from a job that started before filter instance should be collected if it finished after the filter instance"
    check.cancel()


def test_agent_jobs_integration(aggregator, dd_run_check, instance_docker, sa_conn):
    with sa_conn as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT job_id FROM msdb.dbo.sysjobs WHERE name = 'Job 2'")
            job2_id = cursor.fetchone()[0]
            cursor.execute(ACTIVITY_INSERTION_QUERY)
            cursor.execute("SELECT * FROM msdb.dbo.sysjobactivity")
            results = cursor.fetchall()
            assert len(results) == 2, "should have 2 entries in activity"
            for activity in results:
                if activity[1] != job2_id:
                    continue
                assert activity[6] == 1
    instance_docker['dbm'] = True
    instance_docker['include_agent_jobs'] = True
    instance_tags = set(instance_docker.get('tags', []))
    expected_instance_tags = {t for t in instance_tags if not t.startswith('dd.internal')}
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    dd_run_check(check)
    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    job_events = [e for e in dbm_activity if (e.get('sqlserver_job_history', None) is not None)]
    assert len(job_events) == 1, "should have exactly one job history event"
    job_event = job_events[0]
    assert job_event['host'] == "stubbed.hostname", "wrong hostname"
    assert job_event['dbm_type'] == "activity", "wrong dbm_type"
    assert job_event['ddsource'] == "sqlserver", "wrong source"
    assert job_event['ddagentversion'], "missing ddagentversion"
    assert set(job_event['ddtags']) == expected_instance_tags, "wrong instance tags activity"
    assert type(job_event['collection_interval']) in (float, int), "invalid collection_interval"
    history_rows = job_event['sqlserver_job_history']
    assert len(history_rows) == 7, "should have 7 rows of history associated with new completed jobs"
    job_1_step_1_history = history_rows[0]
    # assert that all main fields are present
    assert job_1_step_1_history['name'] == "Job 1"
    assert job_1_step_1_history['job_id']
    assert job_1_step_1_history['step_id'] == 1
    assert job_1_step_1_history['step_name'] == "Step 1"
    assert job_1_step_1_history['step_instance_id'] == 1
    assert job_1_step_1_history['completion_instance_id'] == 4
    assert job_1_step_1_history['run_date']
    assert job_1_step_1_history['run_time']
    assert job_1_step_1_history['run_duration'] is not None
    assert job_1_step_1_history['run_status'] == 1
    assert job_1_step_1_history['message']
    for mname in EXPECTED_AGENT_JOBS_METRICS_COMMON:
        aggregator.assert_metric(mname, count=1)
    assert check._last_history_id == 8, "should update last history in to instance id of latest job completion step"
    dd_run_check(check)
    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    job_events = [e for e in dbm_activity if (e.get('sqlserver_job_history', None) is not None)]
    assert len(job_events) == 1, "successive checks should not create new events for same history entries"
    with sa_conn as conn:
        with conn.cursor() as cursor:
            query = HISTORY_INSERTION_QUERY.format(job_number=2, step_id=0) 
            cursor.execute(query)
    time.sleep(10)
    dd_run_check(check)
    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    job_events = [e for e in dbm_activity if (e.get('sqlserver_job_history', None) is not None)]
    assert len(job_events) == 2, "new event should be submitted based with new completed job in history"
    new_job_event = job_events[1]
    new_history_rows = new_job_event['sqlserver_job_history']
    assert len(new_history_rows) == 2, "should have 2 rows of history associated with new completed jobs"
    check.cancel()
    