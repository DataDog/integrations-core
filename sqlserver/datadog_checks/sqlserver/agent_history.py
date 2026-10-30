# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION
from datadog_checks.sqlserver.utils import raise_if_cancelled

DEFAULT_COLLECTION_INTERVAL = 15
DEFAULT_ROW_LIMIT = 10000

AGENT_HISTORY_MAX_INSTANCE_QUERY = """\
SELECT COALESCE(MAX(instance_id), 0)
FROM msdb.dbo.sysjobhistory;
"""

AGENT_HISTORY_QUERY = """\
WITH NewCompletions AS (
    SELECT TOP (?)
        sjh.job_id,
        sjh.instance_id AS completion_instance_id
    FROM msdb.dbo.sysjobhistory AS sjh
    WHERE sjh.step_id = 0
      AND sjh.instance_id > ?
      AND sjh.instance_id <= ?
    ORDER BY sjh.instance_id ASC
),
CompletionBounds AS (
    SELECT
        completion.job_id,
        completion.completion_instance_id,
        COALESCE(previous.instance_id, 0) AS previous_completion_instance_id
    FROM NewCompletions AS completion
    OUTER APPLY (
        SELECT TOP (1)
            history.instance_id
        FROM msdb.dbo.sysjobhistory AS history
        WHERE history.job_id = completion.job_id
          AND history.step_id = 0
          AND history.instance_id < completion.completion_instance_id
        ORDER BY history.instance_id DESC
    ) AS previous
),
CompletionSizes AS (
    SELECT
        completion.job_id,
        completion.completion_instance_id,
        completion.previous_completion_instance_id,
        execution.execution_row_count
    FROM CompletionBounds AS completion
    CROSS APPLY (
        SELECT COUNT_BIG(*) AS execution_row_count
        FROM msdb.dbo.sysjobhistory AS history
        WHERE history.job_id = completion.job_id
          AND history.instance_id > completion.previous_completion_instance_id
          AND history.instance_id <= completion.completion_instance_id
    ) AS execution
),
PagedCompletions AS (
    SELECT
        completion.*,
        SUM(completion.execution_row_count) OVER (
            ORDER BY completion.completion_instance_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_row_count,
        ROW_NUMBER() OVER (ORDER BY completion.completion_instance_id) AS completion_number
    FROM CompletionSizes AS completion
),
SelectedCompletions AS (
    SELECT
        completion.job_id,
        completion.completion_instance_id,
        completion.previous_completion_instance_id
    FROM PagedCompletions AS completion
    WHERE completion.cumulative_row_count <= ?
       OR completion.completion_number = 1
)
SELECT
    job.name AS job_name,
    CAST(history.job_id AS CHAR(36)) AS job_id,
    history.step_name,
    history.step_id,
    history.instance_id AS step_instance_id,
    completion.completion_instance_id,
    DATEDIFF(SECOND, '19700101',
        DATEADD(HOUR, history.run_time / 10000,
            DATEADD(MINUTE, (history.run_time / 100) % 100,
                DATEADD(SECOND, history.run_time % 100,
                    CAST(CAST(history.run_date AS CHAR(8)) AS DATETIME)
                )
            )
        )
    ) - DATEPART(TZOFFSET, SYSDATETIMEOFFSET()) * 60 AS run_epoch_time,
    (history.run_duration / 10000) * 3600
    + ((history.run_duration % 10000) / 100) * 60
    + (history.run_duration % 100) AS run_duration_seconds,
    CASE history.run_status
        WHEN 0 THEN 'Failed'
        WHEN 1 THEN 'Succeeded'
        WHEN 2 THEN 'Retry'
        WHEN 3 THEN 'Canceled'
        WHEN 4 THEN 'In Progress'
        ELSE 'Unknown'
    END AS step_run_status,
    history.message
FROM SelectedCompletions AS completion
INNER JOIN msdb.dbo.sysjobhistory AS history
    ON history.job_id = completion.job_id
   AND history.instance_id > completion.previous_completion_instance_id
   AND history.instance_id <= completion.completion_instance_id
INNER JOIN msdb.dbo.sysjobs AS job ON job.job_id = completion.job_id
ORDER BY completion.completion_instance_id, history.instance_id;
"""


def agent_check_getter(self):
    return self._check


class SqlserverAgentHistory(DBMAsyncJob):
    def __init__(self, check, config: SQLServerConfig):
        self.log = check.log
        self._config = config
        collection_interval = float(self._config.agent_jobs_config.get('collection_interval', 15))
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        history_row_limit = self._config.agent_jobs_config.get('history_row_limit', DEFAULT_ROW_LIMIT)
        if history_row_limit <= 0:
            history_row_limit = DEFAULT_ROW_LIMIT
        self.history_row_limit = history_row_limit
        self._last_history_id = None
        # Preserve the first baseline across a failed initial submission so a retry cannot skip completions.
        self._initial_history_id = None
        super(SqlserverAgentHistory, self).__init__(
            check,
            run_sync=is_affirmative(self._config.agent_jobs_config.get('run_sync', False)),
            enabled=self._config.agent_jobs_config.get('enabled', False),
            expected_db_exceptions=(),
            min_collection_interval=self._config.min_collection_interval,
            dbms=check.dbms,
            rate_limit=1 / float(collection_interval),
            job_name="agent-jobs-history",
            shutdown_callback=self._close_db_conn,
        )
        self._conn_key_prefix = "dbm-agent-jobs-"

    def shutdown(self) -> None:
        self._check = None

    def _close_db_conn(self):
        pass

    def run_job(self):
        self.collect_agent_history()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_new_agent_job_history(self, cursor):
        cursor.execute(AGENT_HISTORY_MAX_INSTANCE_QUERY)
        upper_bound = int(cursor.fetchone()[0])
        if self._last_history_id is None:
            if self._initial_history_id is None:
                self._initial_history_id = upper_bound
                return [], upper_bound
            last_history_id = self._initial_history_id
        else:
            last_history_id = self._last_history_id

        if upper_bound <= last_history_id:
            return [], upper_bound

        params = (self.history_row_limit, last_history_id, upper_bound, self.history_row_limit)
        self.log.debug("collecting sql server agent jobs history")
        self.log.debug("Running query [%s] %s", AGENT_HISTORY_QUERY, params)
        cursor.execute(AGENT_HISTORY_QUERY, params)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        next_history_id = max(row['completion_instance_id'] for row in rows) if rows else upper_bound

        self.log.debug("loaded sql server agent jobs history len(rows)=%s", len(rows))
        return rows, next_history_id

    def _create_agent_jobs_history_event(self, history_rows):
        event = {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": self._check.agent_version,
            "ddsource": "sqlserver",
            "dbm_type": "agent_jobs",
            "collection_interval": self.collection_interval,
            "ddtags": self._check.tag_manager.get_tags(),
            "timestamp": time.time() * 1000,
            'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "cloud_metadata": self._check.cloud_metadata,
            'service': self._config.service,
            "sqlserver_job_history": history_rows,
        }
        return event

    def _submit_agent_jobs_history(self, history_rows: list[dict], next_history_id: int) -> None:
        history_event = self._create_agent_jobs_history_event(history_rows)
        payload = json.dumps(history_event, default=default_json_event_encoding)
        self.log.debug(payload)
        self._check.database_monitoring_query_activity(payload)
        self._last_history_id = next_history_id
        self._initial_history_id = None

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_agent_history(self):
        """
        Collects all current agent activity for the SQLServer intance.
        :return:
        """
        raise_if_cancelled(self._cancel_event)

        with self._check.connection.open_managed_default_connection(self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(self._conn_key_prefix) as cursor:
                history_rows, next_history_id = self._get_new_agent_job_history(cursor)
                self._submit_agent_jobs_history(history_rows, next_history_id)
