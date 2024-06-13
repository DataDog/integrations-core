# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import logging
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy

import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import (
    ENGINE_EDITION_ENTERPRISE,
    ENGINE_EDITION_EXPRESS,
    ENGINE_EDITION_PERSONAL,
    ENGINE_EDITION_STANDARD,
)
from datadog_checks.sqlserver.stored_procedures import SQL_SERVER_PROCEDURE_METRICS_COLUMNS

from .common import CHECK_NAME, OPERATION_TIME_METRIC_NAME

try:
    import pyodbc
except ImportError:
    pyodbc = None

SELF_HOSTED_ENGINE_EDITIONS = {
    ENGINE_EDITION_PERSONAL,
    ENGINE_EDITION_STANDARD,
    ENGINE_EDITION_ENTERPRISE,
    ENGINE_EDITION_EXPRESS,
}

logger = logging.getLogger(__name__)


def _expected_dbm_instance_tags(dbm_instance):
    return dbm_instance['tags']


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['min_collection_interval'] = 1
    instance_docker['query_metrics'] = {'enabled': False}
    instance_docker['query_activity'] = {'enabled': False}
    instance_docker['collect_settings'] = {'enabled': False}
    # set a very small collection interval so the tests go fast
    instance_docker['procedure_metrics'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.1,
    }
    return copy(instance_docker)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "expected_columns,available_columns",
    [
        [
            ["execution_count", "total_worker_time"],
            ["execution_count", "total_worker_time"],
        ],
        [
            ["execution_count", "total_worker_time", "some_missing_column"],
            ["execution_count", "total_worker_time"],
        ],
    ],
)
def test_get_available_procedure_metrics_columns(dbm_instance, expected_columns, available_columns):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.initialize_connection()
    _conn_key_prefix = "dbm-test-procedures"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            result_available_columns = check.procedure_metrics._get_available_procedure_metrics_columns(
                cursor, expected_columns
            )
            assert result_available_columns == available_columns


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_get_procedure_metrics_query_cached(aggregator, dbm_instance, caplog):
    caplog.set_level(logging.DEBUG)
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.initialize_connection()
    _conn_key_prefix = "dbm-test-procedures"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            for _ in range(3):
                query = check.procedure_metrics._get_procedure_metrics_query_cached(cursor)
                assert query, "query should be non-empty"
    times_columns_loaded = 0
    for r in caplog.records:
        if r.message.startswith("found available sys.dm_exec_procedure_stats columns"):
            times_columns_loaded += 1
    assert times_columns_loaded == 1, "columns should have been loaded only once"


test_procedure_metrics_parametrized = (
    "database,query,param_groups,execution_count,expected_objects",
    [
        [
            "master",  # database
            "EXEC multiQueryProc",  # query
            ((),),
            1,
            [
                {
                    'schema_name': 'dbo',
                    'procedure_name': 'multiQueryProc',
                    'database_name': 'master',
                    'execution_count': 1,
                }
            ],
        ],
        [
            "master",  # database
            "EXEC multiQueryProc",  # query
            ((),),
            5,
            [
                {
                    'schema_name': 'dbo',
                    'procedure_name': 'multiQueryProc',
                    'database_name': 'master',
                    'execution_count': 5,
                }
            ],
        ],
        [
            "master",  # database
            "EXEC encryptedProc",  # query
            ((),),
            3,
            [
                {
                    'schema_name': 'dbo',
                    'procedure_name': 'encryptedProc',
                    'database_name': 'master',
                    'execution_count': 3,
                }
            ],
        ],
        [
            "datadog_test",  # database
            "EXEC bobProc",  # query
            ((),),
            1,
            [
                {
                    'schema_name': 'dbo',
                    'procedure_name': 'bobProc',
                    'database_name': 'datadog_test',
                    'execution_count': 1,
                }
            ],
        ],
        [
            "datadog_test",  # database
            "EXEC bobProc",  # query
            ((),),
            10,
            [
                {
                    'schema_name': 'dbo',
                    'procedure_name': 'bobProc',
                    'database_name': 'datadog_test',
                    'execution_count': 10,
                }
            ],
        ],
        [
            "datadog_test",  # database
            "EXEC bobProcParams @P1 = ?, @P2 = ?",  # query
            (
                (1, "foo"),
                (2, "bar"),
            ),
            1,  # This will execute each param set once, for a total of 2 executions
            [
                {
                    'schema_name': 'dbo',
                    'procedure_name': 'bobProcParams',
                    'database_name': 'datadog_test',
                    'execution_count': 2,
                }
            ],
        ],
    ],
)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(*test_procedure_metrics_parametrized)
def test_procedure_metrics(
    aggregator,
    dd_run_check,
    dbm_instance,
    bob_conn,
    database,
    query,
    param_groups,
    execution_count,
    expected_objects,
    caplog,
    datadog_agent,
):
    caplog.set_level(logging.INFO)
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    # the check must be run three times:
    # 1) set _last_stats_query_time (this needs to happen before the 1st test queries to ensure the query time
    # interval is correct)
    # 2) load the test queries into the StatementMetrics state
    # 3) emit the procedure metrics based on the diff of current and last state
    logger.warning('dd_run_check')
    dd_run_check(check)
    for _ in range(0, execution_count):
        for params in param_groups:
            bob_conn.execute_with_retries(query, params, database=database)
    logger.warning('dd_run_check')
    dd_run_check(check)
    aggregator.reset()
    for _ in range(0, execution_count):
        for params in param_groups:
            bob_conn.execute_with_retries(query, params, database=database)
    logger.warning('dd_run_check')
    dd_run_check(check)

    _conn_key_prefix = "dbm-test-procedures"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            available_procedure_metrics_columns = check.procedure_metrics._get_available_procedure_metrics_columns(
                cursor, SQL_SERVER_PROCEDURE_METRICS_COLUMNS
            )

    instance_tags = dbm_instance.get('tags', [])
    expected_instance_tags = {t for t in instance_tags if not t.startswith('dd.internal')}

    # dbm-metrics
    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(dbm_metrics) == 1, "should have collected exactly one dbm-metrics payload"
    payload = next((n for n in dbm_metrics if n.get('kind') == 'procedure_metrics'), None)

    for expected_object in expected_objects:
        matched = False
        for row in payload['sqlserver_rows']:
            # verify that each key is present and that the correct values are found
            is_match = all(key in row and row[key] == expected_object[key] for key in expected_object.keys())
            if is_match:
                matched = True
                break
        assert matched, "could not find expected_object in sqlserver_rows. expected={} seen={}".format(
            expected_objects, payload['sqlserver_rows']
        )

    assert len(payload['sqlserver_rows']) == len(expected_objects), 'should have as many emitted rows as expected'
    assert set(payload['tags']) == expected_instance_tags
    assert payload['ddagenthostname'] == datadog_agent.get_hostname()

    for row in payload['sqlserver_rows']:
        for column in available_procedure_metrics_columns:
            assert column in row, "missing required procedure metric column {}".format(column)

    # internal debug metrics
    aggregator.assert_metric(
        OPERATION_TIME_METRIC_NAME,
        tags=['agent_hostname:stubbed.hostname', 'operation:collect_procedure_metrics']
        + _expected_dbm_instance_tags(dbm_instance),
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_procedure_metrics_limit(aggregator, dd_run_check, dbm_instance, bob_conn):
    dbm_instance['procedure_metrics']['max_procedures'] = 2
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    # the check must be run three times:
    # 1) set _last_stats_query_time (this needs to happen before the 1st test queries to ensure the query time
    # interval is correct)
    # 2) load the test queries into the StatementMetrics state
    # 3) emit the procedure metrics based on the diff of current and last state
    dd_run_check(check)
    bob_conn.execute_with_retries('EXEC multiQueryProc', (), database='master')
    bob_conn.execute_with_retries('EXEC encryptedProc', (), database='master')
    bob_conn.execute_with_retries('EXEC bobProc', (), database='datadog_test')
    dd_run_check(check)
    aggregator.reset()
    bob_conn.execute_with_retries('EXEC multiQueryProc', (), database='master')
    bob_conn.execute_with_retries('EXEC encryptedProc', (), database='master')
    bob_conn.execute_with_retries('EXEC bobProc', (), database='datadog_test')
    dd_run_check(check)

    # dbm-metrics
    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(dbm_metrics) == 1, "should have collected exactly one dbm-metrics payload"
    payload = next((n for n in dbm_metrics if n.get('kind') == 'procedure_metrics'), None)
    # metrics rows
    sqlserver_rows = payload.get('sqlserver_rows', [])
    assert sqlserver_rows, "should have collected some sqlserver query metrics rows"
    assert len(sqlserver_rows) == dbm_instance['procedure_metrics']['max_procedures']

    # check that it's sorted
    assert sqlserver_rows == sorted(sqlserver_rows, key=lambda i: i['total_elapsed_time'], reverse=True)


@pytest.mark.parametrize("procedure_metrics_enabled", [True, False])
def test_async_job_enabled(dd_run_check, dbm_instance, procedure_metrics_enabled):
    dbm_instance['procedure_metrics'] = {'enabled': procedure_metrics_enabled, 'run_sync': False}
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.cancel()
    if procedure_metrics_enabled:
        assert check.procedure_metrics._job_loop_future is not None
        check.procedure_metrics._job_loop_future.result()
    else:
        assert check.procedure_metrics._job_loop_future is None


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_async_job_inactive_stop(aggregator, dd_run_check, dbm_instance):
    dbm_instance['procedure_metrics']['run_sync'] = False
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.procedure_metrics._job_loop_future.result()
    aggregator.assert_metric(
        "dd.sqlserver.async_job.inactive_stop",
        tags=['job:procedure-metrics'] + _expected_dbm_instance_tags(dbm_instance),
        hostname='',
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_async_job_cancel_cancel(aggregator, dd_run_check, dbm_instance):
    dbm_instance['procedure_metrics']['run_sync'] = False
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.cancel()
    # wait for it to stop and make sure it doesn't throw any exceptions
    check.procedure_metrics._job_loop_future.result()
    assert not check.procedure_metrics._job_loop_future.running(), "metrics thread should be stopped"
    # if the thread doesn't start until after the cancel signal is set then the db connection will never
    # be created in the first place
    aggregator.assert_metric(
        "dd.sqlserver.async_job.cancel",
        tags=_expected_dbm_instance_tags(dbm_instance) + ['job:procedure-metrics'],
    )
