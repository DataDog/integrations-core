# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from unittest import mock

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import (
    STATIC_INFO_ENGINE_EDITION,
    STATIC_INFO_MAJOR_VERSION,
)
from datadog_checks.sqlserver.database_metrics import (
    SqlserverDatabaseBackupMetrics,
    SqlserverDBFragmentationMetrics,
    SqlserverIndexUsageMetrics,
)

from .common import (
    CHECK_NAME,
    SQLSERVER_ENGINE_EDITION,
    SQLSERVER_MAJOR_VERSION,
)

AUTODISCOVERY_DBS = ['master', 'msdb', 'datadog_test']

STATIC_SERVER_INFO = {
    STATIC_INFO_MAJOR_VERSION: SQLSERVER_MAJOR_VERSION,
    STATIC_INFO_ENGINE_EDITION: SQLSERVER_ENGINE_EDITION,
}


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_index_usage_metrics', [True, False])
@pytest.mark.parametrize('include_index_usage_metrics_tempdb', [True, False])
@pytest.mark.parametrize('index_usage_stats_interval', [None, 600])
def test_sqlserver_index_usage_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_index_usage_metrics,
    include_index_usage_metrics_tempdb,
    index_usage_stats_interval,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['include_index_usage_metrics'] = include_index_usage_metrics
    instance_docker_metrics['include_index_usage_metrics_tempdb'] = include_index_usage_metrics_tempdb
    if index_usage_stats_interval:
        instance_docker_metrics['index_usage_stats_interval'] = index_usage_stats_interval

    mocked_results_non_tempdb = [
        [
            ('master', 'PK__patch_ac__09EA1DC2BD2BC49C', 'patch_action_execution_state', 36, 0, 0, 0),
            ('master', 'PK__rds_comp__2E7CCD4A9E2910C9', 'rds_component_version', 0, 5, 0, 0),
        ],
        [
            ('msdb', 'PK__backupse__21F79AAB9439648C', 'backupset', 0, 1, 0, 0),
        ],
        [
            ('datadog_test', 'idx_something', 'some_table', 10, 60, 12, 18),
            ('datadog_test', 'idx_something_else', 'some_table', 20, 30, 40, 50),
        ],
    ]
    mocked_results_tempdb = [
        ('tempdb', 'PK__dmv_view__B5A34EE25D72CBFE', 'dmv_view_run_history', 1500, 0, 0, 49),
    ]
    mocked_results = mocked_results_non_tempdb
    if include_index_usage_metrics_tempdb:
        mocked_results += [mocked_results_tempdb]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    execute_query_handler_mocked = mock.MagicMock()
    execute_query_handler_mocked.side_effect = mocked_results

    index_usage_metrics = SqlserverIndexUsageMetrics(
        instance_config=instance_docker_metrics,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
        databases=AUTODISCOVERY_DBS + ['tempdb'],
    )

    expected_collection_interval = index_usage_stats_interval or index_usage_metrics._default_collection_interval
    assert index_usage_metrics.queries[0]['collection_interval'] == expected_collection_interval

    sqlserver_check._database_metrics = [index_usage_metrics]

    dd_run_check(sqlserver_check)

    if not include_index_usage_metrics:
        assert index_usage_metrics.enabled is False
    else:
        tags = instance_docker_metrics.get('tags', [])
        for result in mocked_results:
            for row in result:
                db, index_name, table, *metric_values = row
                metrics = zip(index_usage_metrics.metric_names()[0], metric_values)
                expected_tags = [
                    f'db:{db}',
                    f'index_name:{index_name}',
                    f'table:{table}',
                ] + tags
                for metric_name, metric_value in metrics:
                    aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)
                if not include_index_usage_metrics_tempdb:
                    assert db != 'tempdb'

    # index_usage_metrics should not be collected because the collection interval is not reached
    aggregator.reset()
    dd_run_check(sqlserver_check)
    for metric_name in index_usage_metrics.metric_names()[0]:
        aggregator.assert_metric(metric_name, count=0)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_db_fragmentation_metrics', [True, False])
@pytest.mark.parametrize('include_db_fragmentation_metrics_tempdb', [True, False])
@pytest.mark.parametrize(
    'db_fragmentation_object_names', [None, ['spt_fallback_db', 'spt_fallback_dev', 'spt_fallback_usg']]
)
@pytest.mark.parametrize('db_fragmentation_metrics_interval', [None, 600])
def test_sqlserver_db_fragmentation_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_db_fragmentation_metrics,
    include_db_fragmentation_metrics_tempdb,
    db_fragmentation_object_names,
    db_fragmentation_metrics_interval,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['include_db_fragmentation_metrics'] = include_db_fragmentation_metrics
    instance_docker_metrics['include_db_fragmentation_metrics_tempdb'] = include_db_fragmentation_metrics_tempdb
    if db_fragmentation_metrics_interval:
        instance_docker_metrics['db_fragmentation_metrics_interval'] = db_fragmentation_metrics_interval

    mocked_results = [
        [
            ('master', 'spt_fallback_db', 0, None, 0, 0.0, 0, 0.0),
            ('master', 'spt_fallback_dev', 0, None, 0, 0.0, 0, 0.0),
            ('master', 'spt_fallback_usg', 0, None, 0, 0.0, 0, 0.0),
            ('master', 'spt_monitor', 0, None, 1, 1.0, 1, 0.0),
            ('master', 'MSreplication_options', 0, None, 1, 1.0, 1, 0.0),
        ],
        [
            ('msdb', 'syscachedcredentials', 1, 'PK__syscache__F6D56B562DA81DC6', 0, 0.0, 0, 0.0),
            ('msdb', 'syscollector_blobs_internal', 1, 'PK_syscollector_blobs_internal_paremeter_name', 0, 0.0, 0, 0.0),
        ],
        [('datadog_test', 'ϑings', 1, 'thingsindex', 1, 1.0, 1, 0.0)],
    ]
    mocked_results_tempdb = [
        [('tempdb', '#TempExample__000000000008', 1, 'PK__#TempExa__3214EC278A26D67E', 1, 1.0, 1, 0.0)],
    ]

    if db_fragmentation_object_names:
        instance_docker_metrics['db_fragmentation_object_names'] = db_fragmentation_object_names
        mocked_results = [
            [
                ('master', 'spt_fallback_db', 0, None, 0, 0.0, 0, 0.0),
                ('master', 'spt_fallback_dev', 0, None, 0, 0.0, 0, 0.0),
                ('master', 'spt_fallback_usg', 0, None, 0, 0.0, 0, 0.0),
            ],
            [],
            [],
        ]
        mocked_results_tempdb = [[]]

    if include_db_fragmentation_metrics_tempdb:
        mocked_results += mocked_results_tempdb

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    execute_query_handler_mocked = mock.MagicMock()
    execute_query_handler_mocked.side_effect = mocked_results

    db_fragmentation_metrics = SqlserverDBFragmentationMetrics(
        instance_config=instance_docker_metrics,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
        databases=AUTODISCOVERY_DBS + ['tempdb'],
    )

    if db_fragmentation_object_names:
        assert db_fragmentation_metrics.db_fragmentation_object_names == db_fragmentation_object_names

    expected_collection_interval = (
        db_fragmentation_metrics_interval or db_fragmentation_metrics._default_collection_interval
    )
    assert db_fragmentation_metrics.queries[0]['collection_interval'] == expected_collection_interval

    sqlserver_check._database_metrics = [db_fragmentation_metrics]

    dd_run_check(sqlserver_check)

    if not include_db_fragmentation_metrics:
        assert db_fragmentation_metrics.enabled is False
    else:
        tags = instance_docker_metrics.get('tags', [])
        for result in mocked_results:
            for row in result:
                database_name, object_name, index_id, index_name, *metric_values = row
                metrics = zip(db_fragmentation_metrics.metric_names()[0], metric_values)
                expected_tags = [
                    f'db:{database_name}',
                    f'database_name:{database_name}',
                    f'object_name:{object_name}',
                    f'index_id:{index_id}',
                    f'index_name:{index_name}',
                ] + tags
                for metric_name, metric_value in metrics:
                    aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)
                    if db_fragmentation_object_names:
                        for m in aggregator.metrics(metric_name):
                            tags_by_key = dict([t.split(':') for t in m.tags if not t.startswith('dd.internal')])
                            assert tags_by_key['object_name'].lower() in db_fragmentation_object_names
                if not include_db_fragmentation_metrics_tempdb:
                    assert database_name != 'tempdb'

    # db_fragmentation_metrics should not be collected because the collection interval is not reached
    aggregator.reset()
    dd_run_check(sqlserver_check)
    for metric_name in db_fragmentation_metrics.metric_names()[0]:
        aggregator.assert_metric(metric_name, count=0)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('database_backup_metrics_interval', [None, 600])
def test_sqlserver_database_backup_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    database_backup_metrics_interval,
):
    instance_docker_metrics['database_autodiscovery'] = True
    if database_backup_metrics_interval:
        instance_docker_metrics['database_backup_metrics_interval'] = database_backup_metrics_interval

    mocked_results = [
        ('master', 'master', 0),
        ('model', 'model', 2),
        ('msdb', 'msdb', 0),
        ('tempdb', 'tempdb', 0),
        ('datadog_test', 'datadog_test', 10),
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    database_backup_metrics = SqlserverDatabaseBackupMetrics(
        instance_config=instance_docker_metrics,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    expected_collection_interval = (
        database_backup_metrics_interval or database_backup_metrics._default_collection_interval
    )
    assert database_backup_metrics.queries[0]['collection_interval'] == expected_collection_interval

    sqlserver_check._database_metrics = [database_backup_metrics]

    dd_run_check(sqlserver_check)
    tags = instance_docker_metrics.get('tags', [])
    for result in mocked_results:
        db, database, *metric_values = result
        metrics = zip(database_backup_metrics.metric_names()[0], metric_values)
        expected_tags = [
            f'db:{db}',
            f'database:{database}',
        ] + tags
        for metric_name, metric_value in metrics:
            aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)

    # database_backup_metrics should not be collected because the collection interval is not reached
    aggregator.reset()
    dd_run_check(sqlserver_check)
    for metric_name in database_backup_metrics.metric_names()[0]:
        aggregator.assert_metric(metric_name, count=0)
