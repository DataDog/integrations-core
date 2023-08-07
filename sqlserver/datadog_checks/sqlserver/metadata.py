# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from time import time
from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

# default pg_settings collection interval in seconds
DEFAULT_SETTINGS_COLLECTION_INTERVAL = 600
DEFAULT_RESOURCES_COLLECTION_INTERVAL = 300

SETTINGS_QUERY = """\
SELECT {columns} FROM sys.configurations
"""

SQL_SERVER_SETTINGS_COLUMNS = [
    "name",
    "value",
    "minimum",
    "maximum",
    "value_in_use",
    "is_dynamic",
    "is_advanced",
]

def agent_check_getter(self):
    return self.check


class SqlserverMetadata(DBMAsyncJob):
    """
    Collects database metadata. Supports:
        1. cloud metadata collection for resource creations
        2. collection of pg_settings
    """

    def __init__(self, check):
        self.check = check
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in self.check.tags if not t.startswith('dd.internal')]
        self.log = check.log
        self.pg_settings_collection_interval = config.settings_metadata_config.get(
            'collection_interval', DEFAULT_SETTINGS_COLLECTION_INTERVAL
        )
        collection_interval = config.resources_metadata_config.get(
            'collection_interval', DEFAULT_RESOURCES_COLLECTION_INTERVAL
        )

        # by default, send resources every 5 minutes
        self.collection_interval = min(collection_interval, self.pg_settings_collection_interval)
        self.collection_interval = collection_interval
        super(SqlserverMetadata, self).__init__(
            check,
            run_sync=is_affirmative(check.statement_metrics_config.get('run_sync', False)),
            enabled=is_affirmative(check.statement_metrics_config.get('enabled', True)),
            expected_db_exceptions=(),
            min_collection_interval=check.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            job_name="query-metrics",
            shutdown_callback=self._close_db_conn,
        )
        self.disable_secondary_tags = is_affirmative(
            check.statement_metrics_config.get('disable_secondary_tags', False)
        )
        self.dm_exec_query_stats_row_limit = int(
            check.statement_metrics_config.get('dm_exec_query_stats_row_limit', 10000)
        )
        self.enforce_collection_interval_deadline = is_affirmative(
            check.statement_metrics_config.get('enforce_collection_interval_deadline', True)
        )
        self._conn_key_prefix = "dbm-metadata-"
        self._settings_query = None
        self._last_stats_query_time = None
        self._max_query_metrics = check.statement_metrics_config.get("max_queries", 250)

    def _close_db_conn(self):
        pass

    def _get_available_settings_columns(self, cursor, all_expected_columns):
        cursor.execute("select top 0 * from sys.configurations")
        all_columns = {i[0] for i in cursor.description}
        available_columns = [c for c in all_expected_columns if c in all_columns]
        missing_columns = set(all_expected_columns) - set(available_columns)
        if missing_columns:
            self.log.debug(
                "missing the following expected settings columns from sys.configurations: %s", missing_columns
            )
        self.log.debug("found available sys.configurations columns: %s", available_columns)
        return available_columns

    def _get_settings_query_cached(self, cursor):
        if self._settings_query:
            return self._settings_query
        available_columns = self._get_available_settings_columns(cursor, SQL_SERVER_SETTINGS_COLUMNS)
        self._settings_query = SETTINGS_QUERY.format(
            columns=', '.join(available_columns),
        )
        return self._settings_query

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _load_settings_rows(self, cursor):
        self.log.debug("collecting sql server instance settings")
        query = self._get_settings_query_cached(cursor)
        self.log.debug("Running query [%s] %s", query)
        cursor.execute(query)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self.log.debug("loaded sql server statement metrics len(rows)=%s", len(rows))
        return rows
