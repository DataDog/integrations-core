# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import DATABASE_INDEX_METRICS

from .common import (
    CUSTOM_METRICS,
    E2E_OPERATION_TIME_METRIC_NAME,
    EXPECTED_AO_METRICS_COMMON,
    EXPECTED_AO_METRICS_PRIMARY,
    EXPECTED_AO_METRICS_SECONDARY,
    EXPECTED_METRICS_DBM_ENABLED,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_COMMON,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_PRIMARY,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_SECONDARY,
    UNEXPECTED_FCI_METRICS,
    UNEXPECTED_QUERY_EXECUTOR_AO_METRICS,
    inc_perf_counter_metrics,
)
from .utils import always_on, not_windows_ci

try:
    import pyodbc
except ImportError:
    pyodbc = None

pytestmark = pytest.mark.e2e


@not_windows_ci
@always_on
def test_ao_primary_replica(dd_agent_check, init_config, instance_ao_docker_primary):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary]})

    # Metrics that are expected to be collected from the primary replica, this includes
    # metrics for secondary replicas.
    for mname in (
        EXPECTED_AO_METRICS_PRIMARY
        + EXPECTED_QUERY_EXECUTOR_AO_METRICS_PRIMARY
        + EXPECTED_AO_METRICS_COMMON
        + EXPECTED_QUERY_EXECUTOR_AO_METRICS_COMMON
        + EXPECTED_QUERY_EXECUTOR_AO_METRICS_SECONDARY
    ):
        aggregator.assert_metric(mname)

    # Metrics that can only be collected from the secondary replica, regardless
    # of being connected to the primary replica.
    for mname in EXPECTED_AO_METRICS_SECONDARY:
        aggregator.assert_metric(mname, count=0)

    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), exclude=CUSTOM_METRICS + E2E_OPERATION_TIME_METRIC_NAME
    )


@not_windows_ci
@always_on
def test_ao_local_primary_replica_only(dd_agent_check, init_config, instance_ao_docker_primary_local_only):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary_local_only]})

    for mname in EXPECTED_AO_METRICS_PRIMARY + EXPECTED_AO_METRICS_COMMON:
        aggregator.assert_metric(mname, count=1)
    for mname in EXPECTED_AO_METRICS_SECONDARY:
        aggregator.assert_metric(mname, count=0)


@not_windows_ci
@always_on
def test_ao_primary_with_non_exist_ag(dd_agent_check, init_config, instance_ao_docker_primary_non_existing_ag):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_primary_non_existing_ag]})

    for mname in EXPECTED_AO_METRICS_PRIMARY + EXPECTED_AO_METRICS_COMMON:
        aggregator.assert_metric(mname, count=0)
    for mname in EXPECTED_AO_METRICS_SECONDARY:
        aggregator.assert_metric(mname, count=0)


@not_windows_ci
@always_on
def test_ao_secondary_replica(dd_agent_check, init_config, instance_ao_docker_secondary):
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_ao_docker_secondary]})

    for mname in (
        EXPECTED_AO_METRICS_SECONDARY
        + EXPECTED_QUERY_EXECUTOR_AO_METRICS_SECONDARY
        + EXPECTED_AO_METRICS_COMMON
        + EXPECTED_QUERY_EXECUTOR_AO_METRICS_COMMON
    ):
        aggregator.assert_metric(mname)
    for mname in EXPECTED_AO_METRICS_PRIMARY + EXPECTED_QUERY_EXECUTOR_AO_METRICS_PRIMARY:
        aggregator.assert_metric(mname, count=0)

    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), exclude=CUSTOM_METRICS + E2E_OPERATION_TIME_METRIC_NAME
    )


@not_windows_ci
def test_check_docker(dd_agent_check, init_config, instance_e2e):
    # run sync to ensure only a single run of both
    # set a very small collection interval so the tests go fast
    instance_e2e['query_activity'] = {'run_sync': True, 'collection_interval': 0.1}
    instance_e2e['query_metrics'] = {'run_sync': True, 'collection_interval': 0.1}
    instance_e2e['procedure_metrics'] = {'run_sync': True, 'collection_interval': 0.1}
    instance_e2e['collect_settings'] = {'run_sync': True, 'collection_interval': 0.1}
    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_e2e]}, rate=True)

    aggregator.assert_metric_has_tag('sqlserver.db.commit_table_entries', 'db:master')

    # ignore DBM debug metrics for the following tests as they're not currently part of the public set of product
    # metrics
    dbm_debug_metrics = [m for m in aggregator._metrics.keys() if m.startswith('dd.sqlserver.')]
    for m in dbm_debug_metrics:
        del aggregator._metrics[m]
    # remove inc perf counter metrics as they rely on diffs to be calculated/ emitted
    # so have special test cases
    inc_perf_counter_metrics_to_remove = [
        m for m in aggregator._metrics.keys() if any(metric[0] in m for metric in inc_perf_counter_metrics)
    ]
    for m in inc_perf_counter_metrics_to_remove:
        del aggregator._metrics[m]

    # remove index usage metrics, which require extra setup & will be tested separately
    for m in DATABASE_INDEX_METRICS:
        if m in aggregator._metrics:
            del aggregator._metrics[m]

    for mname in EXPECTED_METRICS_DBM_ENABLED:
        if mname not in DATABASE_INDEX_METRICS:
            aggregator.assert_metric(mname)

    for mname in UNEXPECTED_FCI_METRICS + UNEXPECTED_QUERY_EXECUTOR_AO_METRICS:
        aggregator.assert_metric(mname, count=0)

    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), exclude=CUSTOM_METRICS + E2E_OPERATION_TIME_METRIC_NAME
    )


@not_windows_ci
def test_custom_queries_readonly_blocks_writes(dd_agent_check, init_config, instance_docker):
    """Verify custom queries cannot execute write operations"""
    # Create a temporary test table for write operations
    if pyodbc:
        conn = pyodbc.connect(instance_docker['connection_string'])
        cursor = conn.cursor()
        cursor.execute("IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'test_readonly_table') CREATE TABLE test_readonly_table (id INT, value NVARCHAR(50))")
        cursor.execute("INSERT INTO test_readonly_table VALUES (1, 'test')")
        conn.commit()
        cursor.close()
        conn.close()

    write_queries = [
        'INSERT INTO test_readonly_table VALUES (2, \'test2\')',
        'UPDATE test_readonly_table SET value = \'updated\' WHERE id = 1',
        'DELETE FROM test_readonly_table WHERE id = 1',
        'CREATE TABLE test_write_table (id INT)',
        'DROP TABLE IF EXISTS test_write_table',
    ]

    try:
        for query in write_queries:
            instance_docker['custom_queries'] = [
                {
                    'query': query,
                    'columns': [{'name': 'result', 'type': 'gauge'}],
                    'metric_prefix': 'sqlserver',
                }
            ]

            # Should fail with read-only error
            with pytest.raises(Exception) as exc_info:
                dd_agent_check({'init_config': init_config, 'instances': [instance_docker]})

            # Verify error message indicates read-only restriction
            error_msg = str(exc_info.value).lower()
            assert 'read' in error_msg or 'write' in error_msg or 'permission' in error_msg or 'cannot' in error_msg, \
                f"Expected read-only error for query '{query}', got: {exc_info.value}"
    finally:
        # Clean up test table
        if pyodbc:
            conn = pyodbc.connect(instance_docker['connection_string'])
            cursor = conn.cursor()
            cursor.execute("IF EXISTS (SELECT * FROM sys.tables WHERE name = 'test_readonly_table') DROP TABLE test_readonly_table")
            cursor.execute("IF EXISTS (SELECT * FROM sys.tables WHERE name = 'test_write_table') DROP TABLE test_write_table")
            conn.commit()
            cursor.close()
            conn.close()


@not_windows_ci
def test_custom_queries_readonly_allows_reads(dd_agent_check, init_config, instance_docker):
    """Verify custom queries can still execute read operations"""
    instance_docker['custom_queries'] = [
        {
            'query': 'SELECT 1 as test_value',
            'columns': [{'name': 'test_value', 'type': 'gauge'}],
            'metric_prefix': 'sqlserver',
        }
    ]

    aggregator = dd_agent_check({'init_config': init_config, 'instances': [instance_docker]})
    aggregator.assert_metric('sqlserver.test_value', value=1)
