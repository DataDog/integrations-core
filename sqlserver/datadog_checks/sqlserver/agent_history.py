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

AGENT_HISTORY_QUERY = """\
SELECT TOP 10
    j.name,
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
INNER JOIN msdb.dbo.sysjobs AS j
ON j.job_id = sjh1.job_id
WHERE 
    EXISTS (
        SELECT 1
        FROM msdb.dbo.sysjobhistory AS sjh2
        WHERE sjh2.job_id = sjh1.job_id
        AND sjh2.step_id = 0
        AND sjh2.instance_id >= sjh1.instance_id{last_instance_id_filter}
    )
"""
def agent_check_getter(self):
    return self._check

class SqlserverAgentHistory(DBMAsyncJob):
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
        self._last_history_id = check._last_history_id
        super(SqlserverAgentHistory, self).__init__(
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
        self._conn_key_prefix = "dbm-agent-jobs-"

    def _close_db_conn(self):
        pass

    def run_job(self):
        self.collect_agent_history()
    
    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_new_agent_job_history(self, cursor):
        last_instance_id_filter = ""
        self._last_history_id = self._check._last_history_id
        if self._last_history_id:
            last_instance_id_filter = "\n\t\tHAVING MIN(sjh2.instance_id) > {last_history_id}".format(last_history_id = self._last_history_id)
        query = AGENT_HISTORY_QUERY.format(last_instance_id_filter=last_instance_id_filter)
        self.log.debug("collecting sql server agent jobs history")
        self.log.debug("Running query [%s]", query)
        cursor.execute(query)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for row in rows:
            if row['completion_instance_id'] > self._last_history_id:
                self._check._last_history_id = row['completion_instance_id']

        self.log.debug("loaded sql server agent jobs history len(rows)=%s", len(rows))
        return rows
    
    def _create_agent_jobs_history_event(self, grouped_jobs_history_rows):
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
            "sqlserver_job_history": grouped_jobs_history_rows
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
                self.log.info(payload)
                # TODO figure out where this payload should go
                self._check.database_monitoring_query_activity(payload)