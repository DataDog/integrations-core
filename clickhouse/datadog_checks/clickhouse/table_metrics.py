# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

from clickhouse_connect.driver.exceptions import OperationalError

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck
    from datadog_checks.clickhouse.config_models.instance import SchemaMetrics

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.tracking import tracked_method

_DEFAULT_COLLECTION_INTERVAL = 60


_TABLE_SIZES_QUERY = """\
SELECT
    database,
    name,
    toInt64(total_rows) AS total_rows,
    toInt64(total_bytes) AS total_bytes
FROM {tables_table}
WHERE database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema')
"""


def agent_check_getter(self):
    return self._check


class ClickhouseTableMetrics(DBMAsyncJob):
    """Per-table size gauges from system.tables."""

    def __init__(self, check: ClickhouseCheck, config: SchemaMetrics):
        collection_interval = config.collection_interval
        if collection_interval is None or collection_interval <= 0:
            collection_interval = _DEFAULT_COLLECTION_INTERVAL

        super(ClickhouseTableMetrics, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=config.run_sync,
            enabled=config.enabled,
            dbms='clickhouse',
            min_collection_interval=check._config.min_collection_interval,
            expected_db_exceptions=(Exception,),
            job_name='clickhouse-table-metrics',
        )
        self._check = check
        self._config = config
        self._collection_interval = collection_interval
        self._db_client = None

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

    def _emit_table_size_gauges(self) -> None:
        try:
            rows = self._execute_query(_TABLE_SIZES_QUERY.format(tables_table=self._check.get_system_table('tables')))
        except Exception:
            self._log.exception("Failed to collect clickhouse table sizes")
            return

        base_tags = list(self._check.tags)
        seen: set[tuple[str, str]] = set()
        for database, name, total_rows, total_bytes in rows:
            if (database, name) in seen:
                continue
            seen.add((database, name))
            entity_tags = base_tags + [f'db:{database}', f'table:{name}']
            self._check.gauge('table.rows', int(total_rows or 0), tags=entity_tags)
            self._check.gauge('table.bytes', int(total_bytes or 0), tags=entity_tags)

