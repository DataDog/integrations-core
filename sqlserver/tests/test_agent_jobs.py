# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import logging
import time
from copy import copy

import pytest

from datadog_checks.sqlserver import SQLServer

from .common import (
    CHECK_NAME,
    EXPECTED_AGENT_JOBS_METRICS_COMMON,
)

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.integration]


AGENT_HISTORY_QUERY = """\
WITH BASE AS (
    SELECT {history_row_limit_filter}
        j.name AS job_name,
        CAST(sjh.job_id AS CHAR(36)) AS job_id,
        sjh.step_name,
        sjh.step_id,
        sjh.instance_id AS step_instance_id,
        DATEDIFF(SECOND, '19700101',
            DATEADD(HOUR, sjh.run_time / 10000,
                DATEADD(MINUTE, (sjh.run_time / 100) % 100,
                    DATEADD(SECOND, sjh.run_time % 100,
                        CAST(CAST(sjh.run_date AS CHAR(8)) AS DATETIME)
                    )
                )
            )
        ) - DATEPART(TZOFFSET, SYSDATETIMEOFFSET()) * 60 AS run_epoch_time,
        (sjh.run_duration / 10000) * 3600
        + ((sjh.run_duration % 10000) / 100) * 60
        + (sjh.run_duration % 100) AS run_duration_seconds,
        CASE sjh.run_status
            WHEN 0 THEN 'Failed'
            WHEN 1 THEN 'Succeeded'
            WHEN 2 THEN 'Retry'
            WHEN 3 THEN 'Canceled'
            WHEN 4 THEN 'In Progress'
            ELSE 'Unknown'
        END AS step_run_status,
        sjh.message
    FROM msdb.dbo.sysjobhistory AS sjh
    INNER JOIN msdb.dbo.sysjobs AS j ON j.job_id = sjh.job_id
	ORDER BY step_instance_id DESC
),
COMPLETION_CTE AS (
    SELECT
        BASE.*,
        MIN(CASE WHEN BASE.step_id = 0 THEN BASE.step_instance_id END) OVER (
            PARTITION BY BASE.job_id
            ORDER BY BASE.step_instance_id
            ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING
        ) AS completion_instance_id
    FROM BASE
),
HISTORY_ENTRIES AS (
    SELECT
        C.*,
        DATEDIFF(SECOND, '19700101',
            DATEADD(HOUR, c_sjh.run_time / 10000,
                DATEADD(MINUTE, (c_sjh.run_time / 100) % 100,
                    DATEADD(SECOND, c_sjh.run_time % 100,
                        CAST(CAST(c_sjh.run_date AS CHAR(8)) AS DATETIME)
                    )
                )
            )
        ) - DATEPART(TZOFFSET, SYSDATETIMEOFFSET()) * 60
        + (c_sjh.run_duration / 10000) * 3600
        + ((c_sjh.run_duration % 10000) / 100) * 60
        + (c_sjh.run_duration % 100) AS completion_epoch_time
    FROM COMPLETION_CTE AS C
    LEFT JOIN msdb.dbo.sysjobhistory AS c_sjh
        ON c_sjh.instance_id = C.completion_instance_id
		WHERE C.completion_instance_id IS NOT NULL
)
SELECT
	job_name,
	job_id,
	step_name,
	step_id,
	step_instance_id,
	completion_instance_id,
	run_epoch_time,
	run_duration_seconds,
	step_run_status,
	message
FROM HISTORY_ENTRIES
WHERE
    completion_epoch_time > {last_collection_time_filter};
"""


FORMATTED_HISTORY_QUERY = """\
WITH BASE AS (
    SELECT TOP 10000
        j.name AS job_name,
        CAST(sjh.job_id AS CHAR(36)) AS job_id,
        sjh.step_name,
        sjh.step_id,
        sjh.instance_id AS step_instance_id,
        DATEDIFF(SECOND, '19700101',
            DATEADD(HOUR, sjh.run_time / 10000,
                DATEADD(MINUTE, (sjh.run_time / 100) % 100,
                    DATEADD(SECOND, sjh.run_time % 100,
                        CAST(CAST(sjh.run_date AS CHAR(8)) AS DATETIME)
                    )
                )
            )
        ) - DATEPART(TZOFFSET, SYSDATETIMEOFFSET()) * 60 AS run_epoch_time,
        (sjh.run_duration / 10000) * 3600
        + ((sjh.run_duration % 10000) / 100) * 60
        + (sjh.run_duration % 100) AS run_duration_seconds,
        CASE sjh.run_status
            WHEN 0 THEN 'Failed'
            WHEN 1 THEN 'Succeeded'
            WHEN 2 THEN 'Retry'
            WHEN 3 THEN 'Canceled'
            WHEN 4 THEN 'In Progress'
            ELSE 'Unknown'
        END AS step_run_status,
        sjh.message
    FROM msdb.dbo.sysjobhistory AS sjh
    INNER JOIN msdb.dbo.sysjobs AS j ON j.job_id = sjh.job_id
	ORDER BY step_instance_id DESC
),
COMPLETION_CTE AS (
    SELECT
        BASE.*,
        MIN(CASE WHEN BASE.step_id = 0 THEN BASE.step_instance_id END) OVER (
            PARTITION BY BASE.job_id
            ORDER BY BASE.step_instance_id
            ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING
        ) AS completion_instance_id
    FROM BASE
),
HISTORY_ENTRIES AS (
    SELECT
        C.*,
        DATEDIFF(SECOND, '19700101',
            DATEADD(HOUR, c_sjh.run_time / 10000,
                DATEADD(MINUTE, (c_sjh.run_time / 100) % 100,
                    DATEADD(SECOND, c_sjh.run_time % 100,
                        CAST(CAST(c_sjh.run_date AS CHAR(8)) AS DATETIME)
                    )
                )
            )
        ) - DATEPART(TZOFFSET, SYSDATETIMEOFFSET()) * 60
        + (c_sjh.run_duration / 10000) * 3600
        + ((c_sjh.run_duration % 10000) / 100) * 60
        + (c_sjh.run_duration % 100) AS completion_epoch_time
    FROM COMPLETION_CTE AS C
    LEFT JOIN msdb.dbo.sysjobhistory AS c_sjh
        ON c_sjh.instance_id = C.completion_instance_id
		WHERE C.completion_instance_id IS NOT NULL
)
SELECT
	job_name,
	job_id,
	step_name,
	step_id,
	step_instance_id,
	completion_instance_id,
	run_epoch_time,
	run_duration_seconds,
	step_run_status,
	message
FROM HISTORY_ENTRIES
WHERE
    completion_epoch_time > 10000;
"""

AGENT_ACTIVITY_DURATION_QUERY = """\
    SELECT
        sj.name,
        CAST(ja.job_id AS char(36)) AS job_id,
        DATEDIFF(SECOND, ja.start_execution_date, GETDATE()) AS duration_seconds
    FROM msdb.dbo.sysjobactivity AS ja
    INNER JOIN msdb.dbo.sysjobs AS sj
    ON ja.job_id = sj.job_id
    WHERE ja.start_execution_date IS NOT NULL
        AND ja.stop_execution_date IS NULL
        AND session_id = (
            SELECT MAX(session_id)
            FROM msdb.dbo.sysjobactivity
        )
"""

AGENT_ACTIVITY_STEPS_QUERY = """\
    WITH ActiveJobs AS (
        SELECT
            job_id,
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
        WHERE sjh1.instance_id = (
            SELECT MAX(instance_id)
            FROM msdb.dbo.sysjobhistory
            WHERE job_id = sjh1.job_id
            AND step_id = sjh1.step_id
        )
    )
    SELECT
        j.name,
        CAST(aj.job_id AS char(36)) AS job_id,
        cs.step_name,
        cs.step_id,
        CASE cs.run_status
            WHEN 0 THEN 'Failed'
            WHEN 1 THEN 'Succeeded'
            WHEN 2 THEN 'Retry'
            WHEN 3 THEN 'Canceled'
            WHEN 4 THEN 'In Progress'
            ELSE 'Unknown'
        END AS step_run_status,
        1 AS step_info
    FROM ActiveJobs AS aj
    INNER JOIN CompletedSteps AS cs
    ON aj.job_id = cs.job_id
        AND aj.last_executed_step_id = cs.step_id
    INNER JOIN msdb.dbo.sysjobs AS j
    ON j.job_id = aj.job_id
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

SESSION_INSERTION_QUERY = """\
IF NOT EXISTS (SELECT * FROM msdb.dbo.syssessions)
BEGIN
    INSERT INTO msdb.dbo.syssessions (
        agent_start_date
    )
    VALUES (
        GETDATE()
    )
END
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
    (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = 'Job {job_number}'),
    {step_id}, -- step_id
    'Step {step_id}', -- step_name
    0, -- sql_message_id
    0, -- sql_severity
    'Job executed successfully.', -- message
    1, -- run_status (1 = Succeeded, 0 = Failed, 3 = Canceled, 4 = In Progress)
    {run_date}, -- run_date in YYYYMMDD format
    {run_time}, -- run_time in HHMMSS format
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
    (SELECT MAX(session_id) FROM msdb.dbo.syssessions),
    (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = 'Job 2'),
    GETDATE(), -- start_execution_date,.
    1,
    NULL
);
"""


@pytest.fixture
def agent_jobs_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['agent_jobs'] = {
        'enabled': True,
        'collection_interval': 1.0,
        'history_row_limit': 10000,
    }
    instance_docker['min_collection_interval'] = 1
    # do not need other dbm metrics
    instance_docker['query_activity'] = {'enabled': False}
    instance_docker['query_metrics'] = {'enabled': False}
    instance_docker['procedure_metrics'] = {'enabled': False}
    instance_docker['collect_settings'] = {'enabled': False}
    return copy(instance_docker)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "dbm_enabled,agent_jobs_enabled,expected_agent_jobs_enabled",
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
    ],
)
def test_agent_job_enabled(instance_docker, dbm_enabled, agent_jobs_enabled, expected_agent_jobs_enabled):
    instance_docker['dbm'] = dbm_enabled
    instance_docker['agent_jobs'] = {'enabled': agent_jobs_enabled}
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()
    agent_jobs_metrics = [m for m in check.database_metrics if m.__class__.__name__ == 'SqlserverAgentMetrics']
    assert agent_jobs_metrics is not None
    assert agent_jobs_metrics[0].enabled == expected_agent_jobs_enabled


@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_history(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            last_collection_time_filter = "{last_collection_time}".format(last_collection_time=10000)
            history_row_limit_filter = "TOP {history_row_limit}".format(history_row_limit=10000)
            query = AGENT_HISTORY_QUERY.format(
                history_row_limit_filter=history_row_limit_filter,
                last_collection_time_filter=last_collection_time_filter,
            )
            cursor.execute(query)
            assert query == FORMATTED_HISTORY_QUERY


@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_activity_duration(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            cursor.execute(AGENT_ACTIVITY_DURATION_QUERY)


@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_activity_steps(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            cursor.execute(AGENT_ACTIVITY_STEPS_QUERY)


now = time.time()


@pytest.mark.usefixtures('dd_environment')
def test_history_output(instance_docker, sa_conn):
    later = now + 10
    with sa_conn as conn:
        with conn.cursor() as cursor:
            cursor.execute(JOB_CREATION_QUERY)
            cursor.execute("SELECT * FROM msdb.dbo.sysjobs")
            results = cursor.fetchall()
            assert len(results) >= 2, "should have 2 created jobs and potentially built in job"
            # job 1 completes once, job 2 completes twice, an instance of job 1 is still in progress
            # should result in 7 steps of job history events to submit
            job_and_step_series_now = [(1, 1), (1, 2), (2, 1), (1, 0)]
            job_and_step_series_later = [(2, 0), (1, 1), (2, 1), (2, 0), (2, 1)]
            run_date_now, run_time_now = history_date_time_from_time(now)
            run_date_later, run_time_later = history_date_time_from_time(later)
            for job_number, step_id in job_and_step_series_now:
                query = HISTORY_INSERTION_QUERY.format(
                    job_number=job_number, step_id=step_id, run_date=run_date_now, run_time=run_time_now
                )
                cursor.execute(query)
            for job_number, step_id in job_and_step_series_later:
                query = HISTORY_INSERTION_QUERY.format(
                    job_number=job_number, step_id=step_id, run_date=run_date_later, run_time=run_time_later
                )
                cursor.execute(query)
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()
    with check.connection.open_managed_default_connection():
        with check.connection.get_managed_cursor() as cursor:
            last_collection_time_filter = "{last_collection_time}".format(last_collection_time=now - 1)
            history_row_limit_filter = "TOP {history_row_limit}".format(history_row_limit=10000)
            query = AGENT_HISTORY_QUERY.format(
                history_row_limit_filter=history_row_limit_filter,
                last_collection_time_filter=last_collection_time_filter,
            )
            cursor.execute(query)
            results = cursor.fetchall()
            assert len(results) == 7, "should have 7 steps associated with completed jobs"
            assert len(results[0]) == 10, "should have 10 columns per step"
            last_collection_time_filter = "{last_collection_time}".format(last_collection_time=now + 1)
            history_row_limit_filter = "TOP {history_row_limit}".format(history_row_limit=10000)
            query = AGENT_HISTORY_QUERY.format(
                history_row_limit_filter=history_row_limit_filter,
                last_collection_time_filter=last_collection_time_filter,
            )
            cursor.execute(query)
            results = cursor.fetchall()
            assert (
                len(results) == 4
            ), "should only have 4 steps associated with completed jobs when filtering with last collection time"


@pytest.mark.flaky
def test_agent_jobs_integration(aggregator, dd_run_check, agent_jobs_instance, sa_conn):
    with sa_conn as conn:
        with conn.cursor() as cursor:
            cursor.execute(SESSION_INSERTION_QUERY)
            cursor.execute("SELECT * FROM msdb.dbo.syssessions")
            results = cursor.fetchall()
            assert len(results) == 1, "should have a session of the agent"
            cursor.execute(ACTIVITY_INSERTION_QUERY)
            cursor.execute("SELECT * FROM msdb.dbo.sysjobactivity")
            results = cursor.fetchall()
            assert len(results) >= 1, "should have 1 entry in activity and potentially built in job activity"
    check = SQLServer(CHECK_NAME, {}, [agent_jobs_instance])
    check.agent_history._last_collection_time = now - 1
    time.sleep(1)
    dd_run_check(check)
    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    job_events = [e for e in dbm_activity if (e.get('sqlserver_job_history', None) is not None)]
    assert len(job_events) == 1, "should have exactly one job history event"
    job_event = job_events[0]
    assert job_event['host'] == "stubbed.hostname", "wrong hostname"
    assert job_event['dbm_type'] == "agent_jobs", "wrong dbm_type"
    assert job_event['ddsource'] == "sqlserver", "wrong source"
    assert job_event['ddagentversion'], "missing ddagentversion"
    assert type(job_event['collection_interval']) in (float, int), "invalid collection_interval"
    history_rows = job_event['sqlserver_job_history']
    assert len(history_rows) == 7, "should have 7 rows of history associated with new completed jobs"
    history_row = history_rows[0]

    # assert that all main fields are present
    assert history_row['job_name']
    assert history_row['job_id']
    assert history_row['step_id'] is not None
    assert history_row['step_name']
    assert history_row['step_instance_id']
    assert history_row['completion_instance_id']
    assert history_row['run_epoch_time']
    assert history_row['run_duration_seconds'] is not None
    assert history_row['step_run_status']
    assert history_row['message']
    for mname in EXPECTED_AGENT_JOBS_METRICS_COMMON:
        aggregator.assert_metric(mname, count=1)
    assert check.agent_history._last_collection_time > now, "should update last collection time appropriately"
    time.sleep(2)
    dd_run_check(check)
    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    job_events = [e for e in dbm_activity if (e.get('sqlserver_job_history', None) is not None)]
    assert len(job_events) == 2, "new sample taken"
    assert (
        len(job_events[1]['sqlserver_job_history']) == 0
    ), "successive checks should not collect new rows for same history entries"
    with sa_conn as conn:
        with conn.cursor() as cursor:
            run_date, run_time = history_date_time_from_time(time.time() + 10)
            query = HISTORY_INSERTION_QUERY.format(job_number=2, step_id=0, run_date=run_date, run_time=run_time)
            cursor.execute(query)
    time.sleep(2)
    dd_run_check(check)
    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    job_events = [e for e in dbm_activity if (e.get('sqlserver_job_history', None) is not None)]
    assert len(job_events) == 3, "new event should be submitted based with new completed job in history"
    new_job_event = job_events[2]
    new_history_rows = new_job_event['sqlserver_job_history']
    assert len(new_history_rows) == 2, "should have 2 rows of history associated with new completed jobs"


def history_date_time_from_time(now):
    datetimestr = str(datetime.datetime.fromtimestamp(now))
    date, time = datetimestr.split(" ")
    date = date.replace('-', "")
    time = time.split(".")[0]
    time = time.replace(':', "")
    return date, time
