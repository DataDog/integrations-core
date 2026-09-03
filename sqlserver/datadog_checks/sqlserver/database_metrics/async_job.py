# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.sqlserver.connection_errors import SQLConnectionError
from datadog_checks.sqlserver.const import DATABASE_METRICS_CONTEXT_INFO
from datadog_checks.sqlserver.utils import construct_use_statement, raise_if_cancelled

from .base import SqlserverDatabaseMetricsBase
from .db_fragmentation_metrics import SqlserverDBFragmentationMetrics
from .index_usage_metrics import SqlserverIndexUsageMetrics
from .table_size_metrics import SqlserverTableSizeMetrics

try:
    import pyodbc
except ImportError:
    pyodbc = None  # type: ignore[assignment]

try:
    import adodbapi
except ImportError:
    adodbapi = None

if TYPE_CHECKING:
    from datadog_checks.sqlserver import SQLServer
    from datadog_checks.sqlserver.config import SQLServerConfig


HEAVY_DATABASE_METRIC_CLASSES = (
    SqlserverIndexUsageMetrics,
    SqlserverDBFragmentationMetrics,
    SqlserverTableSizeMetrics,
)

EXPECTED_DB_EXCEPTIONS: list[type[Exception]] = [SQLConnectionError]
if pyodbc is not None:
    EXPECTED_DB_EXCEPTIONS.append(pyodbc.Error)
if adodbapi is not None:
    EXPECTED_DB_EXCEPTIONS.append(adodbapi.DatabaseError)


class SqlserverDatabaseMetricsAsyncJob(DBMAsyncJob):
    """Collect expensive per-database metrics away from the check runner."""

    def __init__(self, check: SQLServer, config: SQLServerConfig):
        self._check = check
        self._config = config
        self._conn_key_prefix = "dbm-database-metrics-"
        self._database_metrics: list[SqlserverDatabaseMetricsBase] | None = None
        self._database_signature: tuple[str, ...] | None = None
        enabled = not config.only_custom_queries and any(
            metric_config['enabled']
            for metric_config in (
                config.database_metrics_config['index_usage_metrics'],
                config.database_metrics_config['db_fragmentation_metrics'],
                config.database_metrics_config['table_size_metrics'],
            )
        )
        super().__init__(
            check,
            enabled=enabled,
            expected_db_exceptions=tuple(EXPECTED_DB_EXCEPTIONS),
            min_collection_interval=config.min_collection_interval,
            dbms=check.dbms,
            rate_limit=1 / float(config.min_collection_interval),
            job_name="database-metrics",
        )

    def shutdown(self) -> None:
        self._database_metrics = None
        self._check = None

    def run_job(self) -> None:
        raise_if_cancelled(self._cancel_event)
        with self._check.connection.open_managed_default_connection(self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(self._conn_key_prefix) as cursor:
                cursor.execute("SET CONTEXT_INFO {}".format(DATABASE_METRICS_CONTEXT_INFO))
            with self._check.connection.restore_current_database_context(self._conn_key_prefix):
                for database_metric in self.database_metrics:
                    self._execute_database_metric(database_metric)

    @property
    def database_metrics(self) -> list[SqlserverDatabaseMetricsBase]:
        database_names = tuple(sorted(database.name for database in self._check.databases))
        if not database_names:
            database_names = (self._check.instance.get('database', self._check.connection.DEFAULT_DATABASE),)

        if self._database_metrics is not None and database_names == self._database_signature:
            return self._database_metrics

        self._database_signature = database_names
        self._database_metrics = []
        for metric_class in HEAVY_DATABASE_METRIC_CLASSES:
            execute_query = functools.partial(self._execute_query, collector=metric_class.__name__)
            self._database_metrics.append(
                metric_class(
                    config=self._config,
                    new_query_executor=self._check._new_query_executor,
                    server_static_info=self._check.static_info_cache,
                    execute_query_handler=execute_query,
                    track_operation_time=True,
                    databases=list(database_names),
                )
            )
        self._log.debug("Initialized async database metric queries for %d databases", len(database_names))
        return self._database_metrics

    def _execute_database_metric(self, database_metric: SqlserverDatabaseMetricsBase) -> None:
        if not database_metric.enabled:
            self._log.debug("%s: not enabled, skipping execution", database_metric)
            return

        databases = database_metric.databases
        for database, query_executor in zip(databases, database_metric.query_executors):
            raise_if_cancelled(self._cancel_event)
            try:
                query_executor.execute()
            except Exception as e:
                raise_if_cancelled(self._cancel_event)
                self._report_database_error(e, database, type(database_metric).__name__)
            raise_if_cancelled(self._cancel_event)

    def _execute_query(
        self,
        query: str,
        db: str | None = None,
        params: tuple | None = None,
        fetch_multiple_results: bool = False,
        *,
        collector: str,
    ) -> list[tuple]:
        raise_if_cancelled(self._cancel_event)
        try:
            return self._execute_query_raw(query, db=db, params=params, fetch_multiple_results=fetch_multiple_results)
        except Exception as e:
            # QueryExecutor treats query errors as an empty result. Count the failure here, before
            # returning control to it, while preserving cancellation as an abort signal.
            raise_if_cancelled(self._cancel_event)
            self._report_database_error(e, db, collector)
            return []

    def _execute_query_raw(
        self,
        query: str,
        db: str | None = None,
        params: tuple | None = None,
        fetch_multiple_results: bool = False,
    ) -> list[tuple]:
        with self._check.connection.get_managed_cursor(self._conn_key_prefix) as cursor:
            if db:
                context = construct_use_statement(db)
                self._log.debug("Changing async database metrics cursor context via use statement: %s", context)
                cursor.execute(context)
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if not fetch_multiple_results:
                return cursor.fetchall()

            rows = []
            while True:
                if cursor.description is not None:
                    rows.extend(cursor.fetchall())
                if not cursor.nextset():
                    return rows

    def _report_database_error(self, error: Exception, database: str | None, collector: str) -> None:
        self._log.warning(
            "Database metrics collection failed for collector=%s database=%s: %s",
            collector,
            database,
            error,
            exc_info=self._log.getEffectiveLevel() == logging.DEBUG,
        )
        tags = list(self._tags or self._check.tag_manager.get_tags())
        tags.extend(
            [
                "job:database-metrics",
                "collector:{}".format(collector),
                "database:{}".format(database),
                "error:database-{}".format(type(error).__name__),
            ]
        )
        self._check.count("dd.sqlserver.async_job.error", 1, tags=tags, raw=True)
