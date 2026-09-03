# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import nullcontext
from unittest import mock

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.database_metrics import (
    SqlserverDatabaseFilesMetrics,
    SqlserverDBFragmentationMetrics,
    SqlserverIndexUsageMetrics,
    SqlserverTableSizeMetrics,
    SqlserverTempDBFileSpaceUsageMetrics,
)
from datadog_checks.sqlserver.utils import Database

from .common import CHECK_NAME

HEAVY_DATABASE_METRIC_TYPES = (
    SqlserverIndexUsageMetrics,
    SqlserverDBFragmentationMetrics,
    SqlserverTableSizeMetrics,
)


@pytest.mark.unit
def test_heavy_database_metrics_are_owned_by_async_job(init_config, instance_docker_metrics):
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1')}

    synchronous_metrics = check.database_metrics
    async_metrics = check.database_metrics_job.database_metrics

    assert not any(isinstance(metric, HEAVY_DATABASE_METRIC_TYPES) for metric in synchronous_metrics)
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
    query_databases = []

    def execute_query(_query, db=None, **_kwargs):
        query_databases.append(db)
        if db == 'database1':
            raise TimeoutError('database query timed out')
        return []

    job._execute_query_raw = execute_query
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())

    job.run_job()

    assert query_databases == ['database1', 'database2']
    check.connection.open_managed_default_connection.assert_called_once_with('dbm-database-metrics-')
    check.connection.restore_current_database_context.assert_called_once_with('dbm-database-metrics-')
    check.count.assert_called_once()
    assert check.count.call_args.args[:2] == ('dd.sqlserver.async_job.error', 1)
    assert 'database=database1' in caplog.text


@pytest.mark.unit
def test_async_database_metrics_job_stops_between_databases_when_cancelled(init_config, instance_docker_metrics):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'index_usage_metrics': {'enabled': True, 'enabled_tempdb': False},
    }
    check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    check.databases = {Database('database1'), Database('database2')}
    job = check.database_metrics_job
    query_databases = []

    def execute_query(_query, db=None, **_kwargs):
        query_databases.append(db)
        job.cancel()
        return []

    job._execute_query_raw = execute_query
    check.connection.open_managed_default_connection = mock.MagicMock(return_value=nullcontext())
    check.connection.restore_current_database_context = mock.MagicMock(return_value=nullcontext())

    with pytest.raises(Exception, match='Job loop cancelled'):
        job.run_job()

    assert query_databases == ['database1']
