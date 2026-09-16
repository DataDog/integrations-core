# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import functools
import hashlib
import logging
import time
from typing import TYPE_CHECKING

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.utils.db.health import DEFAULT_COOLDOWN, HealthEvent, HealthStatus
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.time import get_precise_time
from datadog_checks.sqlserver.connection_errors import SQLConnectionError
from datadog_checks.sqlserver.const import DATABASE_METRICS_CONTEXT_INFO
from datadog_checks.sqlserver.utils import construct_use_statement, raise_if_cancelled

from .base import SqlserverDatabaseMetricsBase
from .db_fragmentation_metrics import SqlserverDBFragmentationMetrics
from .index_usage_metrics import SqlserverIndexUsageMetrics
from .scheduler import DurationEstimate, GroupSpec, HeavyCollectorScheduler, ReconcileResult, TaskState
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
    from datadog_checks.base.utils.db.core import QueryExecutor
    from datadog_checks.sqlserver import SQLServer
    from datadog_checks.sqlserver.config import SQLServerConfig


HEAVY_DATABASE_METRIC_CLASSES = (
    SqlserverIndexUsageMetrics,
    SqlserverDBFragmentationMetrics,
    SqlserverTableSizeMetrics,
)
SCHEDULER_LOOP_RATE = 1_000.0
# Cap on one intentional idle. `decide` already refuses to sleep past the next release, so this
# only bounds how stale a selection and its discovery snapshot may get before the worker
# re-reconciles. Keep it independent of `min_collection_interval`: tying the two truncated the
# pacing of small estates to the check interval and undid the spreading on exactly the
# configurations that are cheapest to spread.
MAX_PACING_WAIT_S = 60.0
# A command timeout bounds time inside the driver, but a task also pays Python/driver overhead.
# Ten percent is an operational allowance, not a driver guarantee or empirically tuned value.
COMMAND_TIMEOUT_ESTIMATE_FACTOR = 1.1

EXPECTED_DB_EXCEPTIONS: list[type[Exception]] = [SQLConnectionError]
if pyodbc is not None:
    EXPECTED_DB_EXCEPTIONS.append(pyodbc.Error)
if adodbapi is not None:
    EXPECTED_DB_EXCEPTIONS.append(adodbapi.DatabaseError)


class SqlserverDatabaseMetricsAsyncJob(DBMAsyncJob):
    """Pace expensive per-database metrics on one dedicated background connection.

    The pure scheduler owns windows and task selection. This class owns SQL Server concerns:
    discovery snapshots, collector construction, cancellation, connection scope, and telemetry.
    """

    def __init__(self, check: SQLServer, config: SQLServerConfig):
        self._check = check
        self._config = config
        self._conn_key_prefix = "dbm-database-metrics-"
        self._database_metrics: list[SqlserverDatabaseMetricsBase] | None = None
        self._database_signature: tuple[str, ...] | None = None
        self._scheduler_spec_signature: tuple[str, ...] | None = None
        self._scheduler_specs: tuple[GroupSpec, ...] = ()
        self._max_idle = max(1.0, float(config.min_collection_interval))
        metric_configs = (
            config.database_metrics_config['index_usage_metrics'],
            config.database_metrics_config['db_fragmentation_metrics'],
            config.database_metrics_config['table_size_metrics'],
        )
        enabled_metric_configs = tuple(metric_config for metric_config in metric_configs if metric_config['enabled'])
        enabled = (
            config.run_heavy_collectors_async
            and not config.only_custom_queries
            and not config.proc
            and bool(enabled_metric_configs)
        )
        # `run_sync` matches the other DBM jobs: tests set it so a returned check implies the
        # collection already happened, instead of racing a background thread.
        run_sync = any(metric_config.get('run_sync', False) for metric_config in metric_configs)
        super().__init__(
            check,
            run_sync=run_sync,
            enabled=enabled,
            expected_db_exceptions=tuple(EXPECTED_DB_EXCEPTIONS),
            min_collection_interval=config.min_collection_interval,
            dbms=check.dbms,
            # The scheduler owns timing and waits interruptibly inside each pass. Keep the outer
            # limiter effectively disabled so it cannot shift the scheduler's wall-clock windows.
            rate_limit=SCHEDULER_LOOP_RATE,
            job_name="database-metrics",
            enable_missed_collection_event=False,
        )
        # Static SQL Server names used by database_identifier are loaded after this job is built.
        # Resolve the identifier lazily on the first pass so instances using those templates do not
        # all hash the same unresolved placeholder.
        self._scheduler: HeavyCollectorScheduler | None = None
        self._scheduler_identifier: str | None = None
        self._scheduler_overloaded = False

    def shutdown(self) -> None:
        self._database_metrics = None
        self._scheduler_specs = ()
        self._scheduler = None
        self._check = None

    def run_job(self) -> None:
        raise_if_cancelled(self._cancel_event)
        scheduler = self._scheduler_for_current_identifier()
        now = time.time()
        self._reconcile_and_emit(scheduler, now)

        if not scheduler.has_pending():
            if not self._run_sync:
                self._wait(min(scheduler.seconds_until_next_release(now), self._max_idle))
                raise_if_cancelled(self._cancel_event)
            return

        with self._check.connection.open_managed_default_connection(self._conn_key_prefix):
            with self._check.connection.restore_current_database_context(self._conn_key_prefix):
                self._run_pending_tasks(scheduler)

    def _run_pending_tasks(self, scheduler: HeavyCollectorScheduler) -> None:
        """Run one paced burst while the caller holds the job's managed connection."""
        while scheduler.has_pending():
            raise_if_cancelled(self._cancel_event)
            if self._check_went_inactive():
                return

            # Use one timestamp for reconciliation and selection so a window boundary cannot fall
            # between them. This also refreshes autodiscovery after every completed task.
            now = time.time()
            self._reconcile_and_emit(scheduler, now)
            if not scheduler.has_pending():
                return
            decision = scheduler.decide(now, allow_idle=not self._run_sync)
            if decision.task is None:
                return

            if decision.wait > 0:
                self._wait(decision.wait)
                raise_if_cancelled(self._cancel_event)
                # A collector may have released, or autodiscovery may have changed, while this
                # worker was asleep. Reconcile and re-run EDF instead of executing a stale choice.
                result = self._reconcile_and_emit(scheduler, time.time())
                if result.invalidates_selection:
                    continue

            if not scheduler.start(decision.task):
                continue
            self._execute_task(decision.task)

    def _reconcile_and_emit(self, scheduler: HeavyCollectorScheduler, now: float) -> ReconcileResult:
        """Refresh discovery, reconcile scheduler state, and emit rollover telemetry."""
        database_names = self._database_names()
        result = scheduler.reconcile(self._group_specs(database_names), database_names, now)
        if not self._run_sync:
            self._emit_window_telemetry(result, now)
        return result

    def _scheduler_for_current_identifier(self) -> HeavyCollectorScheduler:
        identifier = self._check.database_identifier
        if self._scheduler is None or (
            self._scheduler_identifier is not None and self._scheduler_identifier != identifier
        ):
            # Six digest bytes remain exactly representable after the scheduler normalizes this to float.
            phase = int.from_bytes(hashlib.sha256(identifier.encode()).digest()[:6], 'big')
            self._scheduler = HeavyCollectorScheduler(phase=phase, max_wait=MAX_PACING_WAIT_S, log=self._log)
            self._scheduler_identifier = identifier
        return self._scheduler

    def _wait(self, seconds: float) -> bool:
        """Idle interruptibly, returning whether cancellation ended the wait.

        Callers bound their own durations; this only guards against a negative wait.
        """
        return self._cancel_event.wait(max(0.0, seconds))

    def _check_went_inactive(self) -> bool:
        return bool(
            self._last_check_run
            and time.time() - self._last_check_run > float(self._config.min_collection_interval) * 2
        )

    def _database_names(self) -> tuple[str, ...]:
        database_names = tuple(sorted(database.name for database in self._check.databases))
        if database_names:
            return database_names
        return (self._check.instance.get('database', self._check.connection.DEFAULT_DATABASE),)

    def _group_specs(self, database_names: tuple[str, ...]) -> tuple[GroupSpec, ...]:
        if database_names == self._scheduler_spec_signature:
            return self._scheduler_specs

        specs = []
        estimate_cap = self._runtime_estimate_cap()
        for metric_class in HEAVY_DATABASE_METRIC_CLASSES:
            template = self._new_collector(metric_class, list(database_names))
            if not template.enabled:
                continue
            eligible_databases = self._eligible_databases(template)
            specs.append(
                GroupSpec(
                    name=metric_class.__name__,
                    period=float(template.collection_interval),
                    estimate_cap=estimate_cap,
                    task_factory=functools.partial(self._new_task, metric_class),
                    eligible_databases=tuple(eligible_databases),
                )
            )
        self._scheduler_spec_signature = database_names
        self._scheduler_specs = tuple(specs)
        return self._scheduler_specs

    def _eligible_databases(self, template: SqlserverDatabaseMetricsBase) -> list[str]:
        """Let the collector apply its own tempdb and configuration exclusions."""
        try:
            return list(template.databases)
        except ConfigurationError:
            self._log.debug("%s has no eligible databases", type(template).__name__)
            return []

    def _new_task(
        self,
        metric_class: type[SqlserverDatabaseMetricsBase],
        database: str,
        estimate: DurationEstimate,
    ) -> TaskState:
        return TaskState(
            collector=metric_class.__name__,
            database=database,
            estimate=estimate,
            metrics=self._new_collector(metric_class, [database]),
        )

    def _new_collector(
        self, metric_class: type[SqlserverDatabaseMetricsBase], databases: list[str]
    ) -> SqlserverDatabaseMetricsBase:
        execute_query = functools.partial(self._execute_query, collector=metric_class.__name__)
        return metric_class(
            config=self._config,
            new_query_executor=self._check._new_query_executor,
            server_static_info=self._check.static_info_cache,
            execute_query_handler=execute_query,
            track_operation_time=True,
            databases=databases,
        )

    def _build_executor(self, task: TaskState) -> QueryExecutor:
        assert task.metrics is not None
        executor = task.metrics.query_executors[0]
        # The scheduler owns timing. Leaving Query.collection_interval set would silently skip a
        # wall-clock-window execution that starts less than one elapsed interval after the last one.
        for query in executor.queries:
            query.collection_interval = None
        task.estimate.set_cap(self._runtime_estimate_cap(len(executor.queries)))
        return executor

    def _runtime_estimate_cap(self, query_count: int = 1) -> float | None:
        """Bound a task estimate when SQL commands have a configured timeout.

        ``command_timeout=0`` disables the driver timeout, so it must not impose an invented cap
        on observed runtimes. For a positive timeout, each query in an executor can consume the
        full timeout independently.
        """
        command_timeout = float(self._check.connection.timeout)
        if command_timeout <= 0:
            return None
        return command_timeout * query_count * COMMAND_TIMEOUT_ESTIMATE_FACTOR

    def _execute_task(self, task: TaskState) -> None:
        assert self._scheduler is not None
        raise_if_cancelled(self._cancel_event)
        started = get_precise_time()
        try:
            if task.executor is None:
                task.executor = self._build_executor(task)
            task.executor.execute()
            raise_if_cancelled(self._cancel_event)
        except Exception as e:
            raise_if_cancelled(self._cancel_event)
            self._report_database_error(e, task.database, task.collector)
        finally:
            finished = get_precise_time()
            completed_at = time.time()
            self._scheduler.record_completion(task, finished - started)
            lateness = self._scheduler.lateness(task, completed_at)
            if lateness > 0 and not self._run_sync:
                self._check.gauge(
                    "dd.sqlserver.database_metrics.scheduler.lateness_seconds",
                    lateness,
                    tags=self._scheduler_tags(task.collector),
                    raw=True,
                )
        raise_if_cancelled(self._cancel_event)

    @property
    def database_metrics(self) -> list[SqlserverDatabaseMetricsBase]:
        """Return the legacy aggregate collector view used outside scheduler execution."""
        database_names = self._database_names()

        if self._database_metrics is not None and database_names == self._database_signature:
            return self._database_metrics

        self._database_signature = database_names
        self._database_metrics = [
            self._new_collector(metric_class, list(database_names)) for metric_class in HEAVY_DATABASE_METRIC_CLASSES
        ]
        self._log.debug("Initialized async database metric queries for %d databases", len(database_names))
        return self._database_metrics

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

    def _scheduler_tags(self, collector: str) -> list[str]:
        tags = list(self._tags or self._check.tag_manager.get_tags())
        tags.extend(["job:database-metrics", "collector:{}".format(collector)])
        return tags

    def _emit_window_telemetry(self, result: ReconcileResult, now: float) -> None:
        assert self._scheduler is not None
        if not result.rolled:
            return

        # Before every task has run, utilization is built from cold-start placeholders and reads
        # high on any large estate, which would report an overload on every agent restart. Real
        # overload still surfaces through deadline_miss and lateness_seconds while estimates warm up.
        estimates_ready = self._scheduler.estimates_observed()
        utilization = self._scheduler.utilization()
        overloaded = estimates_ready and utilization > 1
        pending = self._scheduler.pending_count()
        slack = self._scheduler.slack(now)
        for group in self._scheduler.groups:
            if group.name not in result.rolled:
                continue
            tags = self._scheduler_tags(group.name)
            if estimates_ready:
                self._check.gauge(
                    "dd.sqlserver.database_metrics.scheduler.utilization", utilization, tags=tags, raw=True
                )
                self._check.gauge(
                    "dd.sqlserver.database_metrics.scheduler.overloaded", int(overloaded), tags=tags, raw=True
                )
            self._check.gauge("dd.sqlserver.database_metrics.scheduler.slack_seconds", slack, tags=tags, raw=True)
            self._check.gauge(
                "dd.sqlserver.database_metrics.scheduler.pending", len(group.pending), tags=tags, raw=True
            )
            self._check.gauge(
                "dd.sqlserver.database_metrics.scheduler.task_count", len(group.tasks), tags=tags, raw=True
            )
            if group.missed_last_window:
                self._check.count(
                    "dd.sqlserver.database_metrics.scheduler.deadline_miss",
                    group.missed_last_window,
                    tags=tags,
                    raw=True,
                )
            if group.coalesced_windows_last_rollover:
                self._check.count(
                    "dd.sqlserver.database_metrics.scheduler.coalesced_windows",
                    group.coalesced_windows_last_rollover,
                    tags=tags,
                    raw=True,
                )

            if overloaded and hasattr(self._check, 'health'):
                self._check.health.submit_health_event(
                    name=HealthEvent.MISSED_COLLECTION,
                    status=HealthStatus.WARNING,
                    tags=tags,
                    cooldown_time=DEFAULT_COOLDOWN,
                    cooldown_values=[self._check.dbms, "database-metrics", group.name],
                    data={
                        "dbms": self._check.dbms,
                        "job_name": "database-metrics",
                        "utilization": utilization,
                        "pending": pending,
                        "deadline_misses": group.missed_last_window,
                    },
                )

        if not estimates_ready:
            # Leave the latched state alone so warming up after a newly discovered database does
            # not read as a recovery from an overload that was never reported.
            return

        if overloaded and not self._scheduler_overloaded:
            self._log.warning(
                "Database metrics scheduler is overloaded (utilization=%.2f); raise collection_interval, "
                "reduce discovered databases, or disable a heavy collector",
                utilization,
            )
        elif self._scheduler_overloaded and not overloaded:
            self._log.info("Database metrics scheduler is no longer overloaded")
        self._scheduler_overloaded = overloaded

    def _execute_query_raw(
        self,
        query: str,
        db: str | None = None,
        params: tuple | None = None,
        fetch_multiple_results: bool = False,
    ) -> list[tuple]:
        with self._check.connection.get_managed_cursor(self._conn_key_prefix) as cursor:
            # CONTEXT_INFO is session state, and this job holds its connection for the length of a
            # sweep -- up to tens of minutes on a large estate. A reconnect in that window would come
            # back unmarked and put these queries into query-activity samples, so mark every cursor
            # rather than marking the session once.
            cursor.execute("SET CONTEXT_INFO {}".format(DATABASE_METRICS_CONTEXT_INFO))
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
