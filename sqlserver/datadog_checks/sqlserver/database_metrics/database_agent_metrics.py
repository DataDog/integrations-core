from datadog_checks.base.config import is_affirmative

from .base import SqlserverDatabaseMetricsBase

AGENT_ACTIVITY_DURATION_QUERY = {
    "name": "msdb.dbo.sysjobactivity",
    "query": """\
        SELECT
            ja.job_id,
            DATEDIFF(SECOND, ja.start_execution_date, GETDATE()) AS duration_seconds
        FROM msdb.dbo.sysjobactivity AS ja
        WHERE ja.start_execution_date IS NOT NULL
            AND ja.stop_execution_date IS NULL
            AND session_id = (
                SELECT MAX(session_id) 
                FROM msdb.dbo.sysjobactivity
            )
    """,
    "columns": [
        {"name": "job_id", "type": "tag"},
        {"name": "agent.active_jobs.duration", "type": "gauge"},
    ],
}

AGENT_ACTIVITY_STEPS_QUERY = {
    "name": "msdb.dbo.sysjobactivity",
    "query": """\
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
    """,
    "columns": [
        {"name": "job_id", "type": "tag"},
        {"name": "step_name", "type": "tag"},
        {"name": "step_id", "type": "tag"},
        {"name": "step_run_status", "type": "tag"},
        {"name": "agent.active_jobs.step_info", "type": "gauge"},

    ],
}

class SqlserverAgentMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_agent_metrics(self) -> bool:
        return is_affirmative(self.instance_config.get('include_agent_jobs', False))
    
    @property
    def _default_collection_interval(self) -> int:
        '''
        Returns the default interval in seconds at which to collect index usage metrics.
        '''
        # TODO figure out what a good default collection interval should be
        return 1  # 5 minutes
    
    @property
    def collection_interval(self) -> int:
        '''
        Returns the interval in seconds at which to collect index usage metrics.
        Note: The index usage metrics query can be expensive, so it is recommended to set a higher interval.
        '''
        # TODO make a good name for config and add it to the config
        return int(self.instance_config.get('agent_jobs_interval', self._default_collection_interval))
    
    @property
    def enabled(self):
        if not self.include_agent_metrics:
            return False
        return True
    
    @property
    def queries(self):
        # make a copy of the query to avoid modifying the original
        # in case different instances have different collection intervals
        duration_query = AGENT_ACTIVITY_DURATION_QUERY.copy()
        duration_query['collection_interval'] = self.collection_interval
        step_info_query = AGENT_ACTIVITY_STEPS_QUERY.copy()
        step_info_query['collection_interval'] = self.collection_interval
        return [duration_query, step_info_query]
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_agent_metrics={self.include_agent_metrics}), "
            f"collection_interval={self.collection_interval})"
        )