# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

from clickhouse_connect.driver.exceptions import OperationalError

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck
    from datadog_checks.clickhouse.config_models.instance import SchemaMetrics

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.tracking import tracked_method

DEFAULT_COLLECTION_INTERVAL = 60

_TABLE_SIZES_QUERY = """\
SELECT
    database,
    name,
    toInt64(total_rows) AS total_rows,
    toInt64(total_bytes) AS total_bytes
FROM {tables_table}
WHERE database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema')
LIMIT 1 BY database, name
"""

_VIEW_REFRESHES_QUERY = """\
SELECT
    database,
    view,
    hostName() AS host,
    status,
    exception,
    toInt64(toUnixTimestamp(last_success_time)) AS last_refresh_time,
    toInt64(toUnixTimestamp(next_refresh_time)) AS next_refresh_time,
    toInt64(written_rows) AS written_rows,
    toInt64(written_bytes) AS written_bytes
FROM {view_refreshes_table}
LIMIT 1 BY database, view, host
"""

_VIEW_REFRESH_STATUS_MAP = {
    'Scheduled': AgentCheck.OK,
    'Running': AgentCheck.OK,
    'WaitingForDependencies': AgentCheck.WARNING,
    'Disabled': AgentCheck.UNKNOWN,
    'Error': AgentCheck.CRITICAL,
}


def agent_check_getter(self):
    return self._check


class ClickhouseTableMetrics(DBMAsyncJob):
    """Per-table size and per-view refresh gauges from system.tables and system.view_refreshes."""

    def __init__(self, check: ClickhouseCheck, config: SchemaMetrics):
        collection_interval = config.collection_interval
        if collection_interval is None or collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL

        super(ClickhouseTableMetrics, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=config.run_sync,
            enabled=config.enabled,
            dbms=check.dbms,
            min_collection_interval=check._config.min_collection_interval,
            expected_db_exceptions=(Exception,),
            job_name='clickhouse-table-metrics',
        )
        self._check = check
        self._config = config
        self._collection_interval = collection_interval
        self._db_client = None
        self._view_refreshes_unsupported_logged = False
        self._view_refreshes_permission_logged = False
        self._view_refreshes_skip = False

    def cancel(self):
        super(ClickhouseTableMetrics, self).cancel()
        self._close_db_client()

    def _close_db_client(self):
        if self._db_client:
            try:
                self._db_client.close()
            except Exception as e:
                self._log.debug("Error closing table-metrics client: %s", e)
            self._db_client = None

    def _execute_query(self, query: str) -> list:
        if self._db_client is None:
            self._db_client = self._check.create_dbm_client()
            self._db_client.set_client_setting('max_execution_time', self._collection_interval)
        try:
            return self._db_client.query(query).result_rows
        except OperationalError as e:
            self._log.warning("Connection error on table-metrics query, will reconnect: %s", e)
            self._close_db_client()
            raise

    @tracked_method(agent_check_getter=agent_check_getter)
    def run_job(self):
        self._emit_table_size_gauges()
        self._collect_view_refresh_metrics()

    def _emit_table_size_gauges(self) -> None:
        try:
            rows = self._execute_query(_TABLE_SIZES_QUERY.format(tables_table=self._check.get_system_table('tables')))
        except Exception:
            self._log.exception("Failed to collect clickhouse table sizes")
            return

        # Drop the instance-level `db:` base tag (the connection database) so each
        # per-table series carries exactly one `db:` tag — the table's own database.
        base_tags = [t for t in self._check.tags if not t.startswith('db:')]
        for database, name, total_rows, total_bytes in rows:
            entity_tags = base_tags + [f'db:{database}', f'table:{name}']
            self._check.gauge('table.rows', int(total_rows or 0), tags=entity_tags)
            self._check.gauge('table.bytes', int(total_bytes or 0), tags=entity_tags)

    def _collect_view_refresh_metrics(self) -> None:
        if self._view_refreshes_skip:
            return
        try:
            rows = self._check.execute_query_raw(
                _VIEW_REFRESHES_QUERY.format(view_refreshes_table=self._check.get_system_table('view_refreshes'))
            )
        except Exception as e:
            self._handle_view_refreshes_error(e)
            return

        # Drop the instance-level `db:` base tag (the connection database) so each
        # per-view series carries exactly one `db:` tag — the view's own database.
        base_tags = [t for t in self._check.tags if not t.startswith('db:')]
        for database, view_name, host, status, _exception, last_time, next_time, written_rows, written_bytes in rows:
            view_tags = base_tags + [f'db:{database}', f'view:{view_name}', f'host:{host}']
            refresh_status = _VIEW_REFRESH_STATUS_MAP.get(status, AgentCheck.UNKNOWN)
            self._check.gauge('view.refresh.status', refresh_status, tags=view_tags)
            self._check.gauge('view.refresh.last_time', int(last_time or 0), tags=view_tags)
            self._check.gauge('view.refresh.next_time', int(next_time or 0), tags=view_tags)
            self._check.gauge('view.refresh.rows', int(written_rows or 0), tags=view_tags)
            self._check.gauge('view.refresh.bytes', int(written_bytes or 0), tags=view_tags)

    def _handle_view_refreshes_error(self, e: Exception) -> None:
        lowered = str(e).lower()
        if 'unknown table' in lowered or 'unknowntable' in lowered or 'unknown_table' in lowered:
            if not self._view_refreshes_unsupported_logged:
                self._log.info(
                    "system.view_refreshes not present (ClickHouse < 24.3); refresh status will not be populated."
                )
                self._view_refreshes_unsupported_logged = True
            self._view_refreshes_skip = True
        elif 'not enough privileges' in lowered or 'access_denied' in lowered:
            if not self._view_refreshes_permission_logged:
                self._log.warning(
                    "Agent user lacks SELECT on system.view_refreshes; refresh status will not be populated. "
                    "Grant with: GRANT SELECT ON system.view_refreshes TO <agent_user>. "
                    "Restart the agent after granting access."
                )
                self._view_refreshes_permission_logged = True
            self._view_refreshes_skip = True
        else:
            self._log.exception("Unexpected error querying system.view_refreshes")
