# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import nullcontext
from unittest import mock

import pytest

import datadog_checks.sqlserver.database_metrics.async_job as async_job_module
from datadog_checks.base.utils.db.health import HealthEvent, HealthStatus
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import DATABASE_METRICS_CONTEXT_INFO, STATIC_INFO_SERVERNAME
from datadog_checks.sqlserver.database_metrics import (
    SqlserverDatabaseFilesMetrics,
    SqlserverDBFragmentationMetrics,
    SqlserverIndexUsageMetrics,
    SqlserverTableSizeMetrics,
    SqlserverTempDBFileSpaceUsageMetrics,
)
from datadog_checks.sqlserver.database_metrics.scheduler import HeavyCollectorScheduler
from datadog_checks.sqlserver.utils import Database

from .common import CHECK_NAME

HEAVY_DATABASE_METRIC_TYPES = (
    SqlserverIndexUsageMetrics,
    SqlserverDBFragmentationMetrics,
    SqlserverTableSizeMetrics,
)


@pytest.mark.unit
def test_async_database_metrics_job_requires_opt_in(
    init_config, instance_docker_metrics, run_database_metrics_synchronously
):
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.database_metrics_job.run_job = mock.MagicMock()

    check.run_async_jobs([])

    check.database_metrics_job.run_job.assert_not_called()


@pytest.mark.unit
def test_stored_procedure_does_not_run_async_database_metrics(
    init_config, instance_docker_metrics, run_database_metrics_synchronously
):
    instance_docker_metrics['stored_procedure'] = 'pyStoredProc'
    run_database_metrics_synchronously(instance_docker_metrics)
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.database_metrics_job.run_job = mock.MagicMock()

    check.run_async_jobs([])

    check.database_metrics_job.run_job.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize('run_async', [False, True])
def test_heavy_database_metrics_follow_async_configuration(init_config, instance_docker_metrics, run_async):
    instance_docker_metrics['database_metrics'] = {'run_heavy_collectors_async': run_async}
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1')}

    synchronous_metrics = check.database_metrics
    async_metrics = check.database_metrics_job.database_metrics

    assert any(isinstance(metric, HEAVY_DATABASE_METRIC_TYPES) for metric in synchronous_metrics) is not run_async
    assert any(isinstance(metric, SqlserverTempDBFileSpaceUsageMetrics) for metric in synchronous_metrics)
    assert any(isinstance(metric, SqlserverDatabaseFilesMetrics) for metric in synchronous_metrics)
    assert {type(metric) for metric in async_metrics} == set(HEAVY_DATABASE_METRIC_TYPES)
    assert check._async_job_registry['database-metrics'] is check.database_metrics_job

    for metric in synchronous_metrics + async_metrics:
        metric.execute = mock.MagicMock()
    check.load_basic_metrics = mock.MagicMock()
    check._query_manager = mock.MagicMock()
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.get_managed_cursor = mock.MagicMock(return_value=nullcontext(mock.MagicMock()))
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())

    check.collect_metrics()

    for metric in synchronous_metrics:
        metric.execute.assert_called_once_with()
    for metric in async_metrics:
        metric.execute.assert_not_called()


@pytest.mark.unit
def test_async_database_metrics_job_uses_wall_clock_windows(init_config, instance_docker_metrics, monkeypatch):
    """A second pass in one window must be empty without shifting the following window."""
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True, 'collection_interval': 60},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1')}
    job = check.database_metrics_job
    job._run_sync = True
    job._scheduler = HeavyCollectorScheduler(phase=0, max_wait=15, log=job._log)
    job._execute_query_raw = mock.MagicMock(return_value=[])
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())
    now = 1.0
    monkeypatch.setattr(async_job_module.time, 'time', lambda: now)

    job.run_job()
    job.run_job()
    assert job._execute_query_raw.call_count == 1

    now = 61.0
    job.run_job()

    assert job._execute_query_raw.call_count == 2


@pytest.mark.unit
def test_scheduler_phase_uses_resolved_static_database_identifier(init_config, instance_docker_metrics):
    """Static identifier templates must not give distinct SQL Server instances the same scheduler phase."""
    instance_docker_metrics['database_identifier'] = {'template': '$server_name'}
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    job = check.database_metrics_job

    assert job._scheduler is None
    check.static_info_cache[STATIC_INFO_SERVERNAME] = 'server-a'
    # load_static_information invalidates an identifier that was cached before server metadata existed.
    check._database_identifier = None
    first_scheduler = job._scheduler_for_current_identifier()

    assert job._scheduler_identifier == 'server-a'

    check.static_info_cache[STATIC_INFO_SERVERNAME] = 'server-b'
    check._database_identifier = None
    second_scheduler = job._scheduler_for_current_identifier()

    assert job._scheduler_identifier == 'server-b'
    assert second_scheduler is not first_scheduler
    # A rebuilt scheduler is only useful if it staggers: equal phases would align both instances
    # on the same window boundaries and defeat the point of hashing the identifier.
    assert second_scheduler._phase != first_scheduler._phase


@pytest.mark.unit
def test_scheduler_executions_bypass_query_elapsed_interval(init_config, instance_docker_metrics, monkeypatch):
    """Query.should_execute must not silently drop a valid execution in the next wall-clock window."""
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True, 'collection_interval': 60},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1')}
    job = check.database_metrics_job
    job._run_sync = True
    job._scheduler = HeavyCollectorScheduler(phase=0, max_wait=15, log=job._log)
    job._execute_query_raw = mock.MagicMock(return_value=[])
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())
    now = 59.9
    monkeypatch.setattr(async_job_module.time, 'time', lambda: now)

    job.run_job()
    now = 60.1
    job.run_job()

    assert job._execute_query_raw.call_count == 2


@pytest.mark.unit
def test_async_database_metrics_job_uses_dedicated_connection_and_continues_after_database_error(
    init_config, instance_docker_metrics, caplog
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'index_usage_metrics': {'enabled': True, 'enabled_tempdb': False},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1'), Database('database2')}
    check.count = mock.MagicMock()
    job = check.database_metrics_job
    job._run_sync = True
    query_databases = []

    def execute_query(_query, db=None, **_kwargs):
        query_databases.append(db)
        if db == 'database1':
            raise TimeoutError('database query timed out')
        return []

    job._execute_query_raw = execute_query
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    cursor = mock.MagicMock()
    check.connection.get_managed_cursor = mock.MagicMock(return_value=nullcontext(cursor))
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())

    job.run_job()

    assert sorted(query_databases) == ['database1', 'database2']
    check.connection.open_managed_default_connection.assert_called_once_with('dbm-database-metrics-')
    check.connection.restore_current_database_context.assert_called_once_with('dbm-database-metrics-')
    check.count.assert_called_once()
    assert check.count.call_args.args[:2] == ('dd.sqlserver.async_job.error', 1)
    assert 'database=database1' in caplog.text


@pytest.mark.unit
def test_async_database_metrics_refreshes_autodiscovery_during_a_pass(
    init_config, instance_docker_metrics, monkeypatch
):
    """A long pass must add and remove database tasks without waiting for the pass to end."""
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True, 'enabled_tempdb': False},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1'), Database('database2')}
    job = check.database_metrics_job
    job._run_sync = True
    job._scheduler = HeavyCollectorScheduler(phase=0, max_wait=15, log=job._log)
    query_databases = []

    def execute_query(_query, db=None, **_kwargs):
        query_databases.append(db)
        if db == 'database1':
            check.databases = {Database('database1'), Database('database3')}
        return []

    job._execute_query_raw = execute_query
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())
    monkeypatch.setattr(async_job_module.time, 'time', lambda: 0.0)

    job.run_job()

    assert query_databases == ['database1', 'database3']


@pytest.mark.unit
def test_async_database_metrics_marks_every_cursor_for_activity_exclusion(init_config, instance_docker_metrics):
    """
    Each cursor is marked before its query runs.

    The marker is what keeps this job's own heavy queries out of query-activity samples. Setting it
    once per sweep would be enough only if the connection never dropped; a sweep can run for tens of
    minutes, and a reconnect would come back unmarked and start polluting the customer's activity
    data. So the bug being guarded against is a marker that covers the first query but not the rest.
    """
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    job = check.database_metrics_job
    cursor = mock.MagicMock()
    cursor.description = None
    cursor.fetchall.return_value = []
    check.connection.get_managed_cursor = mock.MagicMock(return_value=nullcontext(cursor))

    for _ in range(2):
        job._execute_query_raw('select 1', db='database1')

    marker = mock.call("SET CONTEXT_INFO {}".format(DATABASE_METRICS_CONTEXT_INFO))
    assert cursor.execute.call_args_list.count(marker) == 2
    # ...and it precedes the USE and the query itself on each pass.
    assert cursor.execute.call_args_list[0] == marker
    assert cursor.execute.call_args_list.index(marker, 1) < len(cursor.execute.call_args_list) - 1


@pytest.mark.unit
def test_async_database_metrics_job_stops_between_databases_when_cancelled(init_config, instance_docker_metrics):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'index_usage_metrics': {'enabled': True, 'enabled_tempdb': False},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1'), Database('database2')}
    job = check.database_metrics_job
    job._run_sync = True
    query_databases = []

    def execute_query(_query, db=None, **_kwargs):
        query_databases.append(db)
        job.cancel()
        return []

    job._execute_query_raw = execute_query
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.get_managed_cursor = mock.MagicMock(return_value=nullcontext(mock.MagicMock()))
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())

    with pytest.raises(Exception, match='Job loop cancelled'):
        job.run_job()

    assert len(query_databases) == 1


@pytest.mark.unit
def test_async_database_metrics_job_stops_when_cancelled_while_pacing(
    init_config, instance_docker_metrics, monkeypatch
):
    """A pacing wait must be interruptible so Agent teardown does not wait for the planned gap."""
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True, 'collection_interval': 60},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1')}
    job = check.database_metrics_job
    job._scheduler = HeavyCollectorScheduler(phase=0, max_wait=15, log=job._log)
    job._execute_query_raw = mock.MagicMock(return_value=[])
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())
    monkeypatch.setattr(async_job_module.time, 'time', lambda: 1.0)

    def cancel_during_wait(_seconds: float) -> bool:
        job.cancel()
        return True

    job._wait = cancel_during_wait

    with pytest.raises(Exception, match='Job loop cancelled'):
        job.run_job()

    job._execute_query_raw.assert_not_called()


@pytest.mark.unit
def test_async_database_metrics_job_stops_after_query_error_when_cancelled(init_config, instance_docker_metrics):
    """Cancellation raised by an error path must abort before another database is queried."""
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True, 'enabled_tempdb': False},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1'), Database('database2')}
    check.count = mock.MagicMock()
    job = check.database_metrics_job
    job._run_sync = True
    query_databases = []

    def execute_query(_query: str, db: str | None = None, **_kwargs) -> list[tuple]:
        query_databases.append(db)
        job.cancel()
        raise TimeoutError('database query timed out')

    job._execute_query_raw = execute_query
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())

    with pytest.raises(Exception, match='Job loop cancelled'):
        job.run_job()

    assert len(query_databases) == 1
    check.count.assert_not_called()


@pytest.mark.unit
def test_scheduler_builds_only_eligible_database_tasks(init_config, instance_docker_metrics):
    """Collector-specific tempdb exclusions must be applied before per-database task construction."""
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True, 'enabled_tempdb': False},
        'db_fragmentation_metrics': {'enabled': True, 'enabled_tempdb': False},
        'table_size_metrics': {'enabled': True},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    job = check.database_metrics_job

    specs = job._group_specs(('database1', 'tempdb'))
    scheduler = job._scheduler_for_current_identifier()
    scheduler.reconcile(specs, ('database1', 'tempdb'), 0)

    assert {task.database for group in scheduler.groups for task in group.tasks.values()} == {'database1'}


@pytest.mark.unit
def test_scheduler_does_not_invent_a_runtime_cap_when_command_timeout_is_disabled(init_config, instance_docker_metrics):
    """A disabled driver timeout must allow estimates to reflect arbitrarily long commands."""
    instance_docker_metrics['command_timeout'] = 0
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    specs = check.database_metrics_job._group_specs(('database1',))
    scheduler = check.database_metrics_job._scheduler_for_current_identifier()
    scheduler.reconcile(specs, ('database1',), 0)
    task = scheduler.groups[0].tasks['database1']
    task.estimate.observe(100)

    assert task.estimate.value == 125


@pytest.mark.unit
def test_only_custom_queries_disables_async_database_metrics(
    init_config, instance_docker_metrics, run_database_metrics_synchronously
):
    """Instances restricted to custom queries must not build or run heavy collector tasks."""
    instance_docker_metrics['only_custom_queries'] = True
    run_database_metrics_synchronously(instance_docker_metrics)
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.database_metrics_job.run_job = mock.MagicMock()

    check.run_async_jobs([])

    check.database_metrics_job.run_job.assert_not_called()


@pytest.mark.unit
def test_scheduler_emits_rollover_and_overload_telemetry(init_config, instance_docker_metrics):
    """Missed work must produce bounded-queue telemetry and a rate-limited health warning."""
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True, 'collection_interval': 10},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    job = check.database_metrics_job
    job._scheduler = HeavyCollectorScheduler(phase=0, max_wait=15, log=job._log)
    specs = job._group_specs(('database1', 'database2'))
    job._scheduler.reconcile(specs, ('database1', 'database2'), 0)
    for task in job._scheduler.groups[0].tasks.values():
        task.has_completed = True
        task.estimate.observe(20)
    job._scheduler.reconcile(specs, ('database1', 'database2'), 10)
    task = job._scheduler.decide(10, allow_idle=False).task
    assert task is not None
    assert job._scheduler.start(task)
    result = job._scheduler.reconcile(specs, ('database1', 'database2'), 20)
    check.gauge = mock.MagicMock()
    check.count = mock.MagicMock()
    check.health.submit_health_event = mock.MagicMock()

    job._emit_window_telemetry(result, 20)

    gauge_names = {call.args[0] for call in check.gauge.call_args_list}
    assert gauge_names == {
        'dd.sqlserver.database_metrics.scheduler.utilization',
        'dd.sqlserver.database_metrics.scheduler.slack_seconds',
        'dd.sqlserver.database_metrics.scheduler.pending',
        'dd.sqlserver.database_metrics.scheduler.overloaded',
        'dd.sqlserver.database_metrics.scheduler.task_count',
    }
    count_names = {call.args[0] for call in check.count.call_args_list}
    assert count_names == {
        'dd.sqlserver.database_metrics.scheduler.deadline_miss',
        'dd.sqlserver.database_metrics.scheduler.coalesced_windows',
    }
    check.health.submit_health_event.assert_called_once()
    assert check.health.submit_health_event.call_args.kwargs['name'] is HealthEvent.MISSED_COLLECTION
    assert check.health.submit_health_event.call_args.kwargs['status'] is HealthStatus.WARNING


@pytest.mark.unit
def test_worker_telemetry_is_not_attributed_to_an_individual_collector(init_config, instance_docker_metrics):
    """One busy collector must not report its load against every other collector's name."""
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True, 'collection_interval': 10},
        'db_fragmentation_metrics': {'enabled': True, 'collection_interval': 10},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    job = check.database_metrics_job
    job._scheduler = HeavyCollectorScheduler(phase=0, max_wait=15, log=job._log)
    specs = job._group_specs(('database1',))
    job._scheduler.reconcile(specs, ('database1',), 0)
    for group in job._scheduler.groups:
        for task in group.tasks.values():
            task.estimate.observe(20)
    result = job._scheduler.reconcile(specs, ('database1',), 10)
    assert len(result.rolled) == 2
    check.gauge = mock.MagicMock()

    job._emit_window_telemetry(result, 10)

    def tags_for(metric):
        return [call.kwargs['tags'] for call in check.gauge.call_args_list if call.args[0] == metric]

    # The shared worker reports once, without a collector tag to misattribute it to.
    for metric in (
        'dd.sqlserver.database_metrics.scheduler.utilization',
        'dd.sqlserver.database_metrics.scheduler.overloaded',
        'dd.sqlserver.database_metrics.scheduler.slack_seconds',
    ):
        emitted = tags_for(metric)
        assert len(emitted) == 1, metric
        assert not [tag for tag in emitted[0] if tag.startswith('collector:')], metric

    # Work a collector actually owns stays attributed to it.
    collectors = {tag for tags in tags_for('dd.sqlserver.database_metrics.scheduler.pending') for tag in tags}
    assert {'collector:SqlserverIndexUsageMetrics', 'collector:SqlserverDBFragmentationMetrics'} <= collectors


@pytest.mark.unit
def test_cold_start_estimates_do_not_report_an_overload(init_config, instance_docker_metrics):
    """A restart must not warn about overload from placeholder estimates it has not measured yet."""
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True, 'collection_interval': 10},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    job = check.database_metrics_job
    job._scheduler = HeavyCollectorScheduler(phase=0, max_wait=15, log=job._log)
    databases = tuple(f'database{index}' for index in range(50))
    specs = job._group_specs(databases)
    result = job._scheduler.reconcile(specs, databases, 0)
    check.gauge = mock.MagicMock()
    check.health.submit_health_event = mock.MagicMock()

    # Cold-start placeholders put utilization far above 1 for an estate of this size.
    assert job._scheduler.utilization() > 1
    job._emit_window_telemetry(result, 0)

    gauge_names = {call.args[0] for call in check.gauge.call_args_list}
    assert 'dd.sqlserver.database_metrics.scheduler.overloaded' not in gauge_names
    assert 'dd.sqlserver.database_metrics.scheduler.utilization' not in gauge_names
    assert 'dd.sqlserver.database_metrics.scheduler.pending' in gauge_names
    check.health.submit_health_event.assert_not_called()


@pytest.mark.unit
def test_scheduler_emits_lateness_for_a_completion_after_its_deadline(init_config, instance_docker_metrics):
    """A late completion must report its delay so operators can distinguish severity from miss count."""
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True, 'collection_interval': 10},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.gauge = mock.MagicMock()
    job = check.database_metrics_job
    job._scheduler = HeavyCollectorScheduler(phase=0, max_wait=15, log=job._log)
    specs = job._group_specs(('database1',))
    job._scheduler.reconcile(specs, ('database1',), 0)
    task = job._scheduler.decide(0, allow_idle=False).task
    assert task is not None
    assert job._scheduler.start(task)
    task.executor = mock.MagicMock()

    with (
        mock.patch.object(async_job_module, 'get_precise_time', side_effect=(0, 1)),
        mock.patch.object(async_job_module.time, 'time', return_value=11),
    ):
        job._execute_task(task)

    check.gauge.assert_called_once_with(
        'dd.sqlserver.database_metrics.scheduler.lateness_seconds',
        1,
        tags=job._scheduler_tags(task.collector),
        raw=True,
    )


@pytest.mark.unit
def test_telemetry_failure_does_not_cost_the_collection_it_reports_on(init_config, instance_docker_metrics, caplog):
    """A broken metrics pipeline must not escalate into losing every database's metrics.

    An exception escaping the job stops DBMAsyncJob's loop for every collector and database, so an
    unguarded gauge would trade all collection for one unreportable telemetry value.
    """
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1')}
    check.gauge = mock.MagicMock(side_effect=RuntimeError('metrics pipeline is unavailable'))
    job = check.database_metrics_job
    job._scheduler = HeavyCollectorScheduler(phase=0, max_wait=0, log=job._log)
    job._execute_query_raw = mock.MagicMock(return_value=[])
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())

    job.run_job()

    # The failing gauge must actually have been reached, or this asserts nothing about the guard.
    assert check.gauge.called
    assert job._execute_query_raw.call_count == 1
    assert 'metrics pipeline is unavailable' in caplog.text


@pytest.mark.unit
def test_orphaned_job_stops_querying_once_the_check_stops_running(init_config, instance_docker_metrics, monkeypatch):
    """A job outliving its check must stop issuing expensive per-database queries.

    Without the inactivity check, a removed or reconfigured instance would keep a background
    connection busy sweeping databases nothing is collecting from any more.
    """
    instance_docker_metrics['database_metrics'] = {
        'run_heavy_collectors_async': True,
        'index_usage_metrics': {'enabled': True},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1')}
    job = check.database_metrics_job
    job._run_sync = True
    job._scheduler = HeavyCollectorScheduler(phase=0, max_wait=15, log=job._log)
    job._execute_query_raw = mock.MagicMock(return_value=[])
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())
    stale_by = float(check._config.min_collection_interval) * 2 + 1
    monkeypatch.setattr(async_job_module.time, 'time', lambda: 10_000.0)
    job._last_check_run = 10_000.0 - stale_by

    job.run_job()

    assert job._execute_query_raw.call_count == 0
