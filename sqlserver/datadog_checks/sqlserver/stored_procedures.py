# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    default_json_event_encoding,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION

DEFAULT_COLLECTION_INTERVAL = 60

SQL_SERVER_PROCEDURE_METRICS_COLUMNS = [
    "execution_count",
    "total_worker_time",
    "total_physical_reads",
    "total_logical_writes",
    "total_logical_reads",
    "total_elapsed_time",
    "total_spills",
]

PROCEDURE_METRICS_QUERY = """\
SELECT TOP ({limit})
    OBJECT_SCHEMA_NAME([object_id], [database_id]) as schema_name,
    OBJECT_NAME([object_id], [database_id]) as procedure_name,
    DB_NAME([database_id]) as database_name,
    -- max(type_desc) as type_desc,
    -- max(cached_time) as cached_time,
    -- max(last_execution_time) as last_execution_time,
    {procedure_metrics_columns}
FROM sys.dm_exec_procedure_stats
WHERE database_id <> 32767 -- reserved resource db
GROUP BY object_id, database_id;
"""


def _row_key(row):
    """
    :param row: a normalized row from STATEMENT_METRICS_QUERY
    :return: a tuple uniquely identifying this row
    """
    return "".join(
        (
            row['database_name'],
            row['schema_name'],
            row['procedure_name'],
        )
    )


def agent_check_getter(self):
    return self._check


class SqlserverProcedureMetrics(DBMAsyncJob):
    """Collects stored procedure metrics"""

    def __init__(self, check, config: SQLServerConfig):
        self.log = check.log
        self._config = config
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
        collection_interval = float(
            self._config.procedure_metrics_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        )
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        super(SqlserverProcedureMetrics, self).__init__(
            check,
            run_sync=is_affirmative(self._config.procedure_metrics_config.get('run_sync', False)),
            enabled=is_affirmative(self._config.procedure_metrics_config.get('enabled', True)),
            expected_db_exceptions=(),
            min_collection_interval=self._config.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            job_name="procedure-metrics",
            shutdown_callback=self._close_db_conn,
        )
        self.dm_exec_procedure_stats_row_limit = int(
            self._config.procedure_metrics_config.get('dm_exec_procedure_stats_row_limit', 10000)
        )
        self._state = StatementMetrics()
        self._conn_key_prefix = "dbm-procedures"
        self._procedure_metrics_query = None
        self._max_procedure_metrics = self._config.procedure_metrics_config.get("max_procedures", 250)

    def _close_db_conn(self):
        pass

    def _get_available_procedure_metrics_columns(self, cursor, all_expected_columns):
        cursor.execute("select top 0 * from sys.dm_exec_procedure_stats")
        all_columns = {i[0] for i in cursor.description}
        available_columns = [c for c in all_expected_columns if c in all_columns]
        missing_columns = set(all_expected_columns) - set(available_columns)
        if missing_columns:
            self.log.debug(
                "missing the following expected query metrics columns from dm_exec_procedure_stats: %s", missing_columns
            )
        self.log.debug("found available sys.dm_exec_procedure_stats columns: %s", available_columns)
        return available_columns

    def _get_procedure_metrics_query_cached(self, cursor):
        if self._procedure_metrics_query:
            return self._procedure_metrics_query
        available_columns = self._get_available_procedure_metrics_columns(cursor, SQL_SERVER_PROCEDURE_METRICS_COLUMNS)
        self._procedure_metrics_query = PROCEDURE_METRICS_QUERY.format(
            procedure_metrics_columns=', '.join(['sum({}) as {}'.format(c, c) for c in available_columns]),
            limit=self.dm_exec_procedure_stats_row_limit,
        )
        return self._procedure_metrics_query

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _load_raw_procedure_metrics_rows(self, cursor):
        procedure_metrics_query = self._get_procedure_metrics_query_cached(cursor)
        self.log.debug("Running query [%s]", procedure_metrics_query)
        cursor.execute(procedure_metrics_query)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return rows

    def _collect_metrics_rows(self, cursor):
        rows = self._load_raw_procedure_metrics_rows(cursor)
        rows = [r for r in rows if r.get('procedure_name') and r.get('database_name')]
        if not rows:
            return []
        metric_columns = [c for c in rows[0].keys() if c in SQL_SERVER_PROCEDURE_METRICS_COLUMNS]
        rows = self._state.compute_derivative_rows(rows, metric_columns, key=_row_key)
        return rows

    def _to_metrics_payload(self, rows, max_queries):
        # sort by total_elapsed_time and return the top max_queries
        rows = sorted(rows, key=lambda i: i['total_elapsed_time'], reverse=True)
        rows = rows[:max_queries]
        return {
            'host': self._check.resolved_hostname,
            'timestamp': time.time() * 1000,
            'min_collection_interval': self.collection_interval,
            'tags': self.tags,
            'cloud_metadata': self._config.cloud_metadata,
            'kind': 'procedure_metrics',
            'sqlserver_rows': rows,
            'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            'ddagentversion': datadog_agent.get_version(),
            'ddagenthostname': self._check.agent_hostname,
        }

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_procedure_metrics(self):
        """
        Collects procedure metrics.
        :return:
        """
        # re-use the check's conn module, but set extra_key=dbm- to ensure we get our own
        # raw connection. adodbapi and pyodbc modules are thread safe, but connections are not.
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                rows = self._collect_metrics_rows(cursor)
                if not rows:
                    self.log.debug("collect_procedure_metrics: no rows returned")
                    return
                payload = self._to_metrics_payload(rows, self._max_procedure_metrics)
                self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))

    def run_job(self):
        self.collect_procedure_metrics()
