# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import logging
import time
import uuid
from collections.abc import Iterator
from copy import copy
from typing import Any
from unittest.mock import Mock

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.agent_history import (
    AGENT_HISTORY_MAX_INSTANCE_QUERY,
    AGENT_HISTORY_QUERY,
    SqlserverAgentHistory,
)

from .common import (
    CHECK_NAME,
    EXPECTED_AGENT_JOBS_METRICS_COMMON,
)

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.integration]


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

HISTORY_INSERTION_BY_NAME_QUERY = """\
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
    (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = ?),
    ?,
    ?,
    0,
    0,
    'Job executed successfully.',
    1,
    ?,
    ?,
    0,
    0,
    0,
    0,
    0,
    @@SERVERNAME
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

IDEMPOTENT_JOB_CREATION_QUERY = """\
IF NOT EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = 'Job 1')
BEGIN
    EXEC msdb.dbo.sp_add_job @job_name = 'Job 1'
END
IF NOT EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = 'Job 2')
BEGIN
    EXEC msdb.dbo.sp_add_job @job_name = 'Job 2'
END
"""

CLEANUP_TEST_DATA_QUERY = """\
DELETE FROM msdb.dbo.sysjobactivity
WHERE job_id IN (SELECT job_id FROM msdb.dbo.sysjobs WHERE name IN ('Job 1', 'Job 2'));
DELETE FROM msdb.dbo.sysjobhistory
WHERE job_id IN (SELECT job_id FROM msdb.dbo.sysjobs WHERE name IN ('Job 1', 'Job 2'));
"""

KEY_PREFIX = "dbm-test-"
AGENT_HISTORY_TEST_PREFIX = "datadog_agent_history_test_"


@pytest.fixture
def agent_history_test_jobs(sa_conn: Any) -> Iterator[list[str]]:
    job_names: list[str] = []
    yield job_names
    with sa_conn as conn:
        with conn.cursor() as cursor:
            for job_name in job_names:
                cursor.execute(
                    "DELETE FROM msdb.dbo.sysjobhistory WHERE job_id = "
                    "(SELECT job_id FROM msdb.dbo.sysjobs WHERE name = ?);",
                    job_name,
                )
                cursor.execute(
                    "EXEC msdb.dbo.sp_delete_job @job_name = ?, @delete_unused_schedule = 0;",
                    job_name,
                )


def create_agent_history_test_job(cursor: Any, job_names: list[str], suffix: str) -> str:
    job_name = f"{AGENT_HISTORY_TEST_PREFIX}{uuid.uuid4().hex[:8]}_{suffix}"
    cursor.execute("EXEC msdb.dbo.sp_add_job @job_name = ?, @enabled = 0;", job_name)
    job_names.append(job_name)
    return job_name


def insert_agent_history(cursor: Any, job_name: str, step_id: int, timestamp: float) -> None:
    run_date, run_time = history_date_time_from_time(timestamp)
    step_name = '(Job outcome)' if step_id == 0 else f'Step {step_id}'
    cursor.execute(HISTORY_INSERTION_BY_NAME_QUERY, job_name, step_id, step_name, run_date, run_time)


def get_max_agent_history_id(cursor: Any) -> int:
    cursor.execute(AGENT_HISTORY_MAX_INSTANCE_QUERY)
    return int(cursor.fetchone()[0])


def create_agent_history_collector(
    last_history_id: int | None, history_row_limit: int = 10000
) -> SqlserverAgentHistory:
    agent_history = object.__new__(SqlserverAgentHistory)
    agent_history.log = Mock()
    agent_history.history_row_limit = history_row_limit
    agent_history._last_history_id = last_history_id
    agent_history._initial_history_id = None
    return agent_history


@pytest.fixture
def agent_jobs_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['agent_jobs'] = {
        'enabled': True,
        'run_sync': True,
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

    with check.connection.open_managed_default_connection(KEY_PREFIX):
        with check.connection.get_managed_cursor(KEY_PREFIX) as cursor:
            upper_bound = get_max_agent_history_id(cursor)
            cursor.execute(AGENT_HISTORY_QUERY, (10000, upper_bound, upper_bound, 10000))


class AgentHistoryCursor:
    description = [('completion_instance_id',)]

    def __init__(self, upper_bound: int = 20000, completion_ids: list[int] | None = None) -> None:
        self.upper_bound = upper_bound
        self.completion_ids = completion_ids or []
        self.executions: list[tuple[str, tuple[int, ...]]] = []

    def execute(self, query: str, params: tuple[int, ...] = ()) -> None:
        self.executions.append((query, params))

    def fetchone(self) -> tuple[int]:
        return (self.upper_bound,)

    def fetchall(self) -> list[tuple[int]]:
        return [(completion_id,) for completion_id in self.completion_ids]


class AgentHistoryCheck:
    name = CHECK_NAME

    def __init__(self) -> None:
        self.log = Mock()
        self.count = Mock()
        self.gauge = Mock()
        self.histogram = Mock()


def test_agent_history_empty_page_advances_to_snapshot_upper_bound():
    check = AgentHistoryCheck()
    agent_history = object.__new__(SqlserverAgentHistory)
    agent_history._check = check
    agent_history.log = check.log
    agent_history.history_row_limit = 10000
    agent_history._last_history_id = 10000
    agent_history._initial_history_id = None
    cursor = AgentHistoryCursor()

    rows, next_history_id = agent_history._get_new_agent_job_history(cursor)

    assert rows == []
    assert next_history_id == 20000


def test_agent_history_watermark_commits_after_submission():
    agent_history = object.__new__(SqlserverAgentHistory)
    agent_history._check = Mock()
    agent_history.log = Mock()
    agent_history._last_history_id = 10000
    agent_history._initial_history_id = None
    agent_history._create_agent_jobs_history_event = Mock(return_value={})
    agent_history._check.database_monitoring_query_activity.side_effect = RuntimeError("submit failed")

    with pytest.raises(RuntimeError, match="submit failed"):
        agent_history._submit_agent_jobs_history([], 20000)

    assert agent_history._last_history_id == 10000
    agent_history._check.database_monitoring_query_activity.side_effect = None
    agent_history._submit_agent_jobs_history([], 20000)
    assert agent_history._last_history_id == 20000


def test_agent_history_initial_watermark_survives_submission_failure():
    agent_history = create_agent_history_collector(last_history_id=None)
    agent_history._check = AgentHistoryCheck()
    agent_history._check.database_monitoring_query_activity = Mock()
    agent_history._create_agent_jobs_history_event = Mock(return_value={})

    rows, initial_history_id = agent_history._get_new_agent_job_history(AgentHistoryCursor(upper_bound=10000))
    agent_history._check.database_monitoring_query_activity.side_effect = RuntimeError("submit failed")
    with pytest.raises(RuntimeError, match="submit failed"):
        agent_history._submit_agent_jobs_history(rows, initial_history_id)

    assert agent_history._initial_history_id == 10000
    retry_cursor = AgentHistoryCursor(upper_bound=20000, completion_ids=[15000])
    rows, next_history_id = agent_history._get_new_agent_job_history(retry_cursor)

    assert retry_cursor.executions[1][1] == (10000, 10000, 20000, 10000)
    assert rows == [{'completion_instance_id': 15000}]
    assert next_history_id == 15000
    agent_history._check.database_monitoring_query_activity.side_effect = None
    agent_history._submit_agent_jobs_history(rows, next_history_id)
    assert agent_history._last_history_id == 15000
    assert agent_history._initial_history_id is None


@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_activity_duration(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection(KEY_PREFIX):
        with check.connection.get_managed_cursor(KEY_PREFIX) as cursor:
            cursor.execute(AGENT_ACTIVITY_DURATION_QUERY)


@pytest.mark.usefixtures('dd_environment')
def test_connection_with_agent_activity_steps(instance_docker):
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    check.initialize_connection()

    with check.connection.open_managed_default_connection(KEY_PREFIX):
        with check.connection.get_managed_cursor(KEY_PREFIX) as cursor:
            cursor.execute(AGENT_ACTIVITY_STEPS_QUERY)


now = time.time()


@pytest.mark.usefixtures('dd_environment')
def test_history_output(instance_docker, sa_conn):
    later = now + 10
    with sa_conn as conn:
        with conn.cursor() as cursor:
            cursor.execute(JOB_CREATION_QUERY)
            starting_history_id = get_max_agent_history_id(cursor)
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
    with check.connection.open_managed_default_connection(KEY_PREFIX):
        with check.connection.get_managed_cursor(KEY_PREFIX) as cursor:
            upper_bound = get_max_agent_history_id(cursor)
            cursor.execute(AGENT_HISTORY_QUERY, (10000, starting_history_id, upper_bound, 10000))
            results = cursor.fetchall()
            assert len(results) == 7, "should have 7 steps associated with completed jobs"
            assert len(results[0]) == 10, "should have 10 columns per step"
            first_completion_id = min(row[5] for row in results)
            cursor.execute(AGENT_HISTORY_QUERY, (10000, first_completion_id, upper_bound, 10000))
            results = cursor.fetchall()
            assert len(results) == 4, "should only return executions after the completion watermark"


@pytest.mark.usefixtures('dd_environment')
def test_agent_history_interleaved_jobs_and_incomplete_execution(sa_conn, agent_history_test_jobs):
    timestamp = time.time()
    with sa_conn as conn:
        with conn.cursor() as cursor:
            first_job = create_agent_history_test_job(cursor, agent_history_test_jobs, 'interleaved_first')
            second_job = create_agent_history_test_job(cursor, agent_history_test_jobs, 'interleaved_second')
            incomplete_job = create_agent_history_test_job(cursor, agent_history_test_jobs, 'incomplete')
            starting_history_id = get_max_agent_history_id(cursor)

            for job_name, step_id in [
                (first_job, 1),
                (second_job, 1),
                (first_job, 2),
                (incomplete_job, 1),
                (second_job, 2),
                (first_job, 0),
                (second_job, 0),
                (incomplete_job, 2),
            ]:
                insert_agent_history(cursor, job_name, step_id, timestamp)

            agent_history = create_agent_history_collector(starting_history_id)
            rows, next_history_id = agent_history._get_new_agent_job_history(cursor)

    rows_by_job = {
        job_name: [row['step_id'] for row in rows if row['job_name'] == job_name]
        for job_name in (first_job, second_job, incomplete_job)
    }
    assert rows_by_job == {
        first_job: [1, 2, 0],
        second_job: [1, 2, 0],
        incomplete_job: [],
    }
    assert next_history_id == max(row['completion_instance_id'] for row in rows)


@pytest.mark.usefixtures('dd_environment')
def test_agent_history_watermark_polling_same_second_and_pre_watermark_steps(sa_conn, agent_history_test_jobs):
    timestamp = time.time()
    with sa_conn as conn:
        with conn.cursor() as cursor:
            first_job = create_agent_history_test_job(cursor, agent_history_test_jobs, 'same_second_first')
            second_job = create_agent_history_test_job(cursor, agent_history_test_jobs, 'same_second_second')
            insert_agent_history(cursor, first_job, 1, timestamp)
            insert_agent_history(cursor, second_job, 1, timestamp)
            starting_history_id = get_max_agent_history_id(cursor)

            insert_agent_history(cursor, first_job, 0, timestamp)
            insert_agent_history(cursor, second_job, 0, timestamp)
            agent_history = create_agent_history_collector(starting_history_id)
            first_rows, first_watermark = agent_history._get_new_agent_job_history(cursor)

            agent_history._last_history_id = first_watermark
            duplicate_rows, unchanged_watermark = agent_history._get_new_agent_job_history(cursor)

            insert_agent_history(cursor, first_job, 1, timestamp)
            no_completion_rows, incomplete_watermark = agent_history._get_new_agent_job_history(cursor)
            agent_history._last_history_id = incomplete_watermark
            insert_agent_history(cursor, first_job, 0, timestamp)
            new_rows, new_watermark = agent_history._get_new_agent_job_history(cursor)

    assert len(first_rows) == 4
    assert {row['job_name'] for row in first_rows} == {first_job, second_job}
    assert len({row['completion_instance_id'] for row in first_rows}) == 2
    assert sum(row['step_instance_id'] <= starting_history_id for row in first_rows) == 2
    assert duplicate_rows == []
    assert unchanged_watermark == first_watermark
    assert no_completion_rows == []
    assert incomplete_watermark > unchanged_watermark
    assert [row['step_id'] for row in new_rows] == [1, 0]
    assert new_rows[0]['step_instance_id'] <= incomplete_watermark
    assert new_watermark > first_watermark


@pytest.mark.usefixtures('dd_environment')
def test_agent_history_pagination_keeps_completions_whole(sa_conn, agent_history_test_jobs):
    timestamp = time.time()
    with sa_conn as conn:
        with conn.cursor() as cursor:
            first_job = create_agent_history_test_job(cursor, agent_history_test_jobs, 'page_first')
            second_job = create_agent_history_test_job(cursor, agent_history_test_jobs, 'page_second')
            third_job = create_agent_history_test_job(cursor, agent_history_test_jobs, 'page_third')
            starting_history_id = get_max_agent_history_id(cursor)

            for step_id in (1, 2, 0):
                insert_agent_history(cursor, first_job, step_id, timestamp)
            for job_name in (second_job, third_job):
                for step_id in (1, 0):
                    insert_agent_history(cursor, job_name, step_id, timestamp)

            agent_history = create_agent_history_collector(starting_history_id, history_row_limit=2)
            pages = []
            for _ in range(3):
                rows, next_history_id = agent_history._get_new_agent_job_history(cursor)
                pages.append(rows)
                agent_history._last_history_id = next_history_id
            final_rows, final_watermark = agent_history._get_new_agent_job_history(cursor)

    assert [[row['job_name'] for row in page] for page in pages] == [
        [first_job, first_job, first_job],
        [second_job, second_job],
        [third_job, third_job],
    ]
    assert [[row['step_id'] for row in page] for page in pages] == [[1, 2, 0], [1, 0], [1, 0]]
    assert final_rows == []
    assert final_watermark == agent_history._last_history_id


@pytest.mark.usefixtures('dd_environment')
def test_agent_history_regression_resets_to_a_safe_baseline(sa_conn, agent_history_test_jobs):
    timestamp = time.time()
    with sa_conn as conn:
        with conn.cursor() as cursor:
            job_name = create_agent_history_test_job(cursor, agent_history_test_jobs, 'regression')
            current_history_id = get_max_agent_history_id(cursor)
            agent_history = create_agent_history_collector(current_history_id + 10000)

            rows, reset_watermark = agent_history._get_new_agent_job_history(cursor)
            agent_history._last_history_id = reset_watermark
            insert_agent_history(cursor, job_name, 1, timestamp)
            insert_agent_history(cursor, job_name, 0, timestamp)
            new_rows, new_watermark = agent_history._get_new_agent_job_history(cursor)

    assert rows == []
    assert reset_watermark == current_history_id
    assert [row['step_id'] for row in new_rows] == [1, 0]
    assert new_watermark > reset_watermark


@pytest.mark.usefixtures('dd_environment')
def test_agent_jobs_integration(aggregator, dd_run_check, agent_jobs_instance, sa_conn):
    test_now = time.time()
    test_later = test_now + 10
    with sa_conn as conn:
        with conn.cursor() as cursor:
            cursor.execute(IDEMPOTENT_JOB_CREATION_QUERY)
            cursor.execute(CLEANUP_TEST_DATA_QUERY)
            starting_history_id = get_max_agent_history_id(cursor)
            run_date_now, run_time_now = history_date_time_from_time(test_now)
            run_date_later, run_time_later = history_date_time_from_time(test_later)
            for job_number, step_id in [(1, 1), (1, 2), (2, 1), (1, 0)]:
                cursor.execute(
                    HISTORY_INSERTION_QUERY.format(
                        job_number=job_number, step_id=step_id, run_date=run_date_now, run_time=run_time_now
                    )
                )
            for job_number, step_id in [(2, 0), (1, 1), (2, 1), (2, 0), (2, 1)]:
                cursor.execute(
                    HISTORY_INSERTION_QUERY.format(
                        job_number=job_number, step_id=step_id, run_date=run_date_later, run_time=run_time_later
                    )
                )
            cursor.execute(SESSION_INSERTION_QUERY)
            cursor.execute("SELECT * FROM msdb.dbo.syssessions")
            results = cursor.fetchall()
            assert len(results) >= 1, "should have a session of the agent"
            cursor.execute(ACTIVITY_INSERTION_QUERY)
            cursor.execute("SELECT * FROM msdb.dbo.sysjobactivity")
            results = cursor.fetchall()
            assert len(results) >= 1, "should have 1 entry in activity and potentially built in job activity"
    check = SQLServer(CHECK_NAME, {}, [agent_jobs_instance])
    check.agent_history._last_history_id = starting_history_id
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
    assert check.agent_history._last_history_id > starting_history_id, "should update the history watermark"
    time.sleep(2)
    dd_run_check(check)
    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    job_events = [e for e in dbm_activity if (e.get('sqlserver_job_history', None) is not None)]
    assert len(job_events) == 2, "new sample taken"
    assert len(job_events[1]['sqlserver_job_history']) == 0, (
        "successive checks should not collect new rows for same history entries"
    )
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
