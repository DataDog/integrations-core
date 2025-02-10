# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

DEFAULT_COLLECTION_INTERVAL = 15
DEFAULT_ROW_LIMIT = 10000

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


def agent_check_getter(self):
    return self._check


class SqlserverAgentHistory(DBMAsyncJob):
    def __init__(self, check, config: SQLServerConfig):
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
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
        self._last_collection_time = int(time.time())
        super(SqlserverAgentHistory, self).__init__(
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
        self.collect_agent_history()

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
            'service': self._config.service,
            "sqlserver_job_history": history_rows,
        }
        return event

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_agent_history(self):
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
