# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_RDS, STATIC_INFO_VERSION

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

DEFAULT_COLLECTION_INTERVAL = 15
DEFAULT_ROW_LIMIT = 10000

AGENT_HISTORY_QUERY = """\
WITH HISTORY_ENTRIES AS (
    SELECT {history_row_limit_filter}
        j.name AS job_name,
        CAST(sjh1.job_id AS char(36)) AS job_id,
        sjh1.step_name,
        sjh1.step_id,
        sjh1.instance_id AS step_instance_id,
        (
            SELECT MIN(sjh2.instance_id)
            FROM msdb.dbo.sysjobhistory AS sjh2
            WHERE sjh2.job_id = sjh1.job_id
            AND sjh2.step_id = 0
            AND sjh2.instance_id >= sjh1.instance_id
        ) AS completion_instance_id,
        (
            SELECT DATEDIFF(SECOND, '19700101',
                DATEADD(HOUR, sjh1.run_time / 10000,
                    DATEADD(MINUTE, (sjh1.run_time / 100) % 100,
                        DATEADD(SECOND, sjh1.run_time % 100,
                            CAST(CAST(sjh1.run_date AS CHAR(8)) AS DATETIME)
                        )
                    )
                )
            ) - DATEPART(tzoffset, SYSDATETIMEOFFSET()) * 60
        ) AS run_epoch_time,
        (
            (sjh1.run_duration / 10000) * 3600
            + ((sjh1.run_duration % 10000) / 100) * 60
            + (sjh1.run_duration % 100)
        ) AS run_duration_seconds,
        CASE sjh1.run_status
            WHEN 0 THEN 'Failed'
            WHEN 1 THEN 'Succeeded'
            WHEN 2 THEN 'Retry'
            WHEN 3 THEN 'Canceled'
            WHEN 4 THEN 'In Progress'
            ELSE 'Unknown'
        END AS step_run_status,
        sjh1.message
    FROM
        msdb.dbo.sysjobhistory AS sjh1
    INNER JOIN msdb.dbo.sysjobs AS j
    ON j.job_id = sjh1.job_id
    ORDER BY completion_instance_id DESC
)
SELECT * FROM HISTORY_ENTRIES
WHERE
    EXISTS (
        SELECT 1
        FROM msdb.dbo.sysjobhistory AS sjh2
        WHERE sjh2.instance_id = HISTORY_ENTRIES.completion_instance_id
        AND (DATEDIFF(SECOND, '19700101',
                DATEADD(HOUR, sjh2.run_time / 10000,
                    DATEADD(MINUTE, (sjh2.run_time / 100) % 100,
                        DATEADD(SECOND, sjh2.run_time % 100,
                            CAST(CAST(sjh2.run_date AS CHAR(8)) AS DATETIME)
                        )
                    )
                )
            ) - DATEPART(tzoffset, SYSDATETIMEOFFSET()) * 60
        + (sjh2.run_duration / 10000) * 3600
        + ((sjh2.run_duration % 10000) / 100) * 60
        + (sjh2.run_duration % 100)) > 0 + {last_collection_time_filter}
    )
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

AGENT_ACTIVE_SESSION_DURATION_QUERY = """\
SELECT TOP 1
    session_id,
    DATEDIFF(SECOND, agent_start_date, GETDATE()) AS duration_seconds
FROM msdb.dbo.syssessions
ORDER BY session_id DESC
"""


def agent_check_getter(self):
    return self._check


class SqlserverAgentJobs(DBMAsyncJob):
    def __init__(self, check, config: SQLServerConfig):
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
        self.log = check.log
        self._config = config
        collection_interval = float(
            self._config.agent_jobs_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        )
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        history_row_limit = self._config.agent_jobs_config.get('history_row_limit', DEFAULT_ROW_LIMIT)
        if history_row_limit <= 0:
            history_row_limit = DEFAULT_ROW_LIMIT
        self.history_row_limit = history_row_limit
        self._last_collection_time = int(time.time())
        super(SqlserverAgentJobs, self).__init__(
            check,
            run_sync=True,
            enabled=self._config.agent_jobs_config.get('enabled', False),
            expected_db_exceptions=(),
            min_collection_interval=self._config.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            job_name="agent-jobs-history",
            shutdown_callback=self._close_db_conn,
        )
        self._conn_key_prefix = "dbm-agent-jobs-"

    def _close_db_conn(self):
        pass

    def run_job(self):
        self.collect_agent_jobs()

    def _collect_metrics_rows(self, cursor):
        self.log.debug("collecting sql server agent jobs activity")

        self.log.debug("Running query [%s]", AGENT_ACTIVITY_DURATION_QUERY)
        cursor.execute(AGENT_ACTIVITY_DURATION_QUERY)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        self.log.debug("Running query [%s]", AGENT_ACTIVITY_STEPS_QUERY)
        cursor.execute(AGENT_ACTIVITY_STEPS_QUERY)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows += [dict(zip(columns, row)) for row in cursor.fetchall()]

        if self._check.static_info_cache.get(STATIC_INFO_RDS, True):
            return rows

        self.log.debug("Running query [%s]", AGENT_ACTIVE_SESSION_DURATION_QUERY)
        cursor.execute(AGENT_ACTIVE_SESSION_DURATION_QUERY)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows += [dict(zip(columns, row)) for row in cursor.fetchall()]

        return rows

    def _to_metrics_payload(self, rows):
        return {
            'host': self._check.resolved_hostname,
            'timestamp': time.time() * 1000,
            'min_collection_interval': self.collection_interval,
            'tags': self.tags,
            'kind': 'agent_jobs_metrics',
            'cloud_metadata': self._config.cloud_metadata,
            'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            'ddagentversion': datadog_agent.get_version(),
            'ddagenthostname': self._check.agent_hostname,
            'sqlserver_rows': rows
        }

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_new_agent_job_history(self, cursor):
        last_collection_time_filter = "{last_collection_time}".format(last_collection_time=self._last_collection_time)
        history_row_limit_filter = "TOP {history_row_limit}".format(history_row_limit=self.history_row_limit)
        query = AGENT_HISTORY_QUERY.format(
            history_row_limit_filter=history_row_limit_filter, last_collection_time_filter=last_collection_time_filter
        )
        self.log.debug("collecting sql server agent jobs history")
        self.log.debug("Running query [%s]", query)
        cursor.execute(query)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for row in rows:
            row_completion_time = row['run_epoch_time'] + row['run_duration_seconds']
            if row_completion_time > self._last_collection_time:
                self._last_collection_time = row_completion_time

        self.log.debug("loaded sql server agent jobs history len(rows)=%s", len(rows))
        return rows

    def _create_agent_jobs_history_event(self, history_rows):
        event = {
            "host": self._check.resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": "agent_jobs",
            "collection_interval": self.collection_interval,
            "ddtags": self.tags,
            "timestamp": time.time() * 1000,
            'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "cloud_metadata": self._config.cloud_metadata,
            "sqlserver_job_history": history_rows,
        }
        return event

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_agent_jobs(self):
        """
        Collects all current agent activity for the SQLServer intance.
        :return:
        """
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                history_rows = self._get_new_agent_job_history(cursor)
                history_event = self._create_agent_jobs_history_event(history_rows)
                payload = json.dumps(history_event, default=default_json_event_encoding)
                self.log.debug(payload)
                self._check.database_monitoring_query_activity(payload)

                rows = self._collect_metrics_rows(cursor)
                metrics_payload = self._to_metrics_payload(rows)
                self.log.debug(metrics_payload)
                self._check.database_monitoring_query_metrics(
                    json.dumps(metrics_payload, default=default_json_event_encoding)
                )
