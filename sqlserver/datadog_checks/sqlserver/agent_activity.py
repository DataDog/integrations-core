import time

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

DEFAULT_COLLECTION_INTERVAL = 10

AGENT_ACTIVITY_QUERY = """\
SELECT
    sj.name AS Name,
    sa.job_id AS JobID,
    sa.start_execution_date AS StartTime,
    sa.last_executed_step_id AS LastFinishedStep,
    sa.last_executed_step_date AS LastFinishedStepStartTime,
    sa.stop_execution_date AS StopTime
FROM (msdb.dbo.sysjobs sj
INNER JOIN msdb.dbo.sysjobactivity sa ON sj.job_id = sa.job_id)
WHERE  sa.start_execution_date is not NULL AND sa.stop_execution_date is NULL
"""

AGENT_HISTORY_QUERY = """\
SELECT
    sj.name AS Name,
    sj.job_id AS JobID,
    sh.run_status AS Status,
    sh.run_date AS StartDate,
    sh.run_time AS StartTime,
    sh.step_name AS StepName,
    sh.step_id AS StepID,
    sh.run_duration AS Duration,
    sh.instance_id AS Instance,
    sh.message AS Message
FROM msdb.dbo.sysjobhistory sh
INNER JOIN msdb.dbo.sysjobs sj ON sj.job_id = sh.job_id{last_instance_id_filter}
GO
"""
def agent_check_getter(self):
    return self._check

class SqlserverAgentActivity(DBMAsyncJob):
    def __init__(self, check, config: SQLServerConfig):
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
        self.log = check.log
        self._config = config
        collection_interval = float(
            self._config.activity_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        )
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        self._last_history_id = None
        super(SqlserverAgentActivity, self).__init__(
            check,
            run_sync=True,
            enabled=is_affirmative(self._config.activity_config.get('enabled', True)),
            expected_db_exceptions=(),
            min_collection_interval=self._config.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            # is this used as identification information? if so where. is there a convention to follow
            job_name="agent-jobs-activity",
            shutdown_callback=self._close_db_conn,
        )
        # same questions as job_name
        self._conn_key_prefix = "dbm-activity-"

    def _close_db_conn(self):
        pass

    def run_job(self):
        self.collect_agent_activity()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_active_jobs(self, cursor):
        self.log.debug("collecting sql server active agent jobs")
        self.log.debug("Running query [%s]", AGENT_ACTIVITY_QUERY)
        cursor.execute(AGENT_ACTIVITY_QUERY)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self.log.debug("loaded sql server active agent jobs len(rows)=%s", len(rows))
        return rows
    
    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_new_agent_job_history(self, cursor):
        last_instance_id_filter = ""
        if self._last_history_id:
            last_instance_id_filter = "\nWHERE sh.instance_id > {last_history_id}".format(last_history_id = self._last_history_id)
        query = AGENT_HISTORY_QUERY.format(last_instance_id_filter=last_instance_id_filter)
        self.log.debug("collecting sql server agent jobs history")
        self.log.debug("Running query [%s]", query)
        cursor.execute(query)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self.log.debug("loaded sql server agent jobs history len(rows)=%s", len(rows))
        return rows

    def _create_active_agent_jobs_event(self, active_jobs):
        event = {
            "host": self._check.resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": "activity",
            "collection_interval": self.collection_interval,
            "ddtags": self.tags,
            "timestamp": time.time() * 1000,
            'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "cloud_metadata": self._config.cloud_metadata,
            "sqlserver_active_jobs": active_jobs
        }
        return event
    
    def _create_agent_jobs_history_event(self, jobs_history):
        pass

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_agent_activity(self):
        """
        Collects all current agent activity for the SQLServer intance.
        :return:
        """
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                rows = self._get_active_jobs(cursor)
                event = self._create_active_agent_jobs_event(rows)
                payload = json.dumps(event, default=default_json_event_encoding)
                # TODO see what topic is best for this
                self._check.database_monitoring_query_activity(payload)
