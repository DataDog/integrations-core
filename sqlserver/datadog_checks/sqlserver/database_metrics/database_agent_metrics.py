# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.config import is_affirmative

from .base import SqlserverDatabaseMetricsBase

AGENT_ACTIVITY_DURATION_QUERY = {
    "name": "msdb.dbo.sysjobactivity",
    "query": """\
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
    """,
    "columns": [
        {"name": "job_name", "type": "tag"},
        {"name": "job_id", "type": "tag"},
        {"name": "agent.active_jobs.duration", "type": "gauge"},
    ],
}

AGENT_ACTIVITY_STEPS_QUERY = {
    "name": "msdb.dbo.sysjobactivity",
    "query": """\
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
    """,
    "columns": [
        {"name": "job_name", "type": "tag"},
        {"name": "job_id", "type": "tag"},
        {"name": "step_name", "type": "tag"},
        {"name": "step_id", "type": "tag"},
        {"name": "step_run_status", "type": "tag"},
        {"name": "agent.active_jobs.step_info", "type": "gauge"},
    ],
}

AGENT_ACTIVE_SESSION_DURATION_QUERY = {
    "name": "msdb.dbo.syssessions",
    "query": """\
        SELECT TOP 1
            session_id,
            DATEDIFF(SECOND, agent_start_date, GETDATE()) AS duration_seconds
        FROM msdb.dbo.syssessions
        ORDER BY session_id DESC
    """,
    "columns": [
        {"name": "session_id", "type": "tag"},
        {"name": "agent.active_session.duration", "type": "gauge"},
    ],
}


class SqlserverAgentMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_agent_metrics(self) -> bool:
        if not self.config.dbm_enabled:
            return False
        agent_jobs_config = self.config.agent_jobs_config
        if agent_jobs_config:
            return is_affirmative(agent_jobs_config.get('enabled', False))
        return False

    @property
    def _default_collection_interval(self) -> int:
        '''
        Returns the default interval in seconds at which to collect index usage metrics.
        '''
        return 15  # 15 seconds

    @property
    def collection_interval(self) -> int:
        '''
        Returns the interval in seconds at which to collect index usage metrics.
        Note: The index usage metrics query can be expensive, so it is recommended to set a higher interval.
        '''
        agent_jobs_config = self.config.agent_jobs_config
        if agent_jobs_config:
            return int(agent_jobs_config.get('collection_interval', 15))
        return 15  # 15 seconds

    @property
    def enabled(self):
        if not self.include_agent_metrics:
            return False
        return True

    @property
    def queries(self):
        # make a copy of the query to avoid modifying the original
        # in case different instances have different collection intervals
        query_list = []
        active_job_duration_query = AGENT_ACTIVITY_DURATION_QUERY.copy()
        active_job_duration_query['collection_interval'] = self.collection_interval
        query_list.append(active_job_duration_query)
        active_job_step_info_query = AGENT_ACTIVITY_STEPS_QUERY.copy()
        active_job_step_info_query['collection_interval'] = self.collection_interval
        query_list.append(active_job_step_info_query)
        if not self.is_rds:
            active_session_duration_query = AGENT_ACTIVE_SESSION_DURATION_QUERY.copy()
            active_session_duration_query['collection_interval'] = self.collection_interval
            query_list.append(active_session_duration_query)
        return query_list

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_agent_metrics={self.include_agent_metrics}), "
            f"is_rds={self.is_rds}, "
            f"collection_interval={self.collection_interval})"
        )
