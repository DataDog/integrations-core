# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from concurrent.futures import ThreadPoolExecutor

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import (
    DATABASE_BACKUP_METRICS,
    DATABASE_FILES_METRICS,
    DATABASE_FRAGMENTATION_METRICS,
    DATABASE_INDEX_METRICS,
    DATABASE_MASTER_FILES,
    DATABASE_STATS_METRICS,
    DBM_MIGRATED_METRICS,
    INSTANCE_METRICS,
    INSTANCE_METRICS_DATABASE,
    OS_SCHEDULER_METRICS,
    TASK_SCHEDULER_METRICS,
    TEMPDB_FILE_SPACE_USAGE_METRICS,
)

from .common import (
    CHECK_NAME,
    SERVER_METRICS,
)

INCR_FRACTION_METRICS = {'sqlserver.latches.latch_wait_time'}
AUTODISCOVERY_DBS = ['master', 'msdb', 'datadog_test']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_server_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags)

    for metric_name in SERVER_METRICS:
        expected_tags = tags
        aggregator.assert_metric(metric_name, tags=expected_tags, hostname=sqlserver_check.resolved_hostname, count=1)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize("database_autodiscovery", [True, False])
@pytest.mark.parametrize("dbm_enabled", [True, False])
def test_check_instance_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    database_autodiscovery,
    dbm_enabled,
):
    instance_docker_metrics['database_autodiscovery'] = database_autodiscovery
    instance_docker_metrics['dbm'] = dbm_enabled
    instance_docker_metrics['include_instance_metrics'] = True
    if database_autodiscovery:
        instance_docker_metrics['autodiscovery_include'] = AUTODISCOVERY_DBS

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags)

    for metric_name, _, _ in INSTANCE_METRICS:
        # TODO: we should find a better way to test these metrics
        # remove SQL Server incremental sql fraction metrics for now
        if metric_name in INCR_FRACTION_METRICS:
            continue
        aggregator.assert_metric(metric_name, tags=tags, hostname=sqlserver_check.resolved_hostname, count=1)

    if not database_autodiscovery:
        for metric_name, _, _ in INSTANCE_METRICS_DATABASE:
            aggregator.assert_metric(metric_name, tags=tags, hostname=sqlserver_check.resolved_hostname, count=1)
    else:
        for db in AUTODISCOVERY_DBS:
            for metric_name, _, _ in INSTANCE_METRICS_DATABASE:
                aggregator.assert_metric(
                    metric_name,
                    tags=tags + ['database:{}'.format(db)],
                    hostname=sqlserver_check.resolved_hostname,
                    count=1,
                )
    if not dbm_enabled:
        for metric_name, _, _ in DBM_MIGRATED_METRICS:
            aggregator.assert_metric(metric_name, tags=tags, hostname=sqlserver_check.resolved_hostname, count=1)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize("database_autodiscovery", [True, False])
def test_check_database_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    database_autodiscovery,
):
    instance_docker_metrics['database_autodiscovery'] = database_autodiscovery
    if database_autodiscovery:
        instance_docker_metrics['autodiscovery_include'] = AUTODISCOVERY_DBS

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags)

    dbs = AUTODISCOVERY_DBS if database_autodiscovery else ['master']

    for db in dbs:
        db_tags = tags + ['database:{}'.format(db), 'db:{}'.format(db)]
        for metric_name, _, _ in DATABASE_FILES_METRICS:
            for tag in db_tags + ['database_files_state_desc:ONLINE']:
                aggregator.assert_metric_has_tag(
                    metric_name,
                    tag=tag,
                )
            for tag_prefix in ('file_id', 'file_type', 'file_location'):
                aggregator.assert_metric_has_tag_prefix(
                    metric_name,
                    tag_prefix=tag_prefix,
                )

        for metric_name, _, _ in DATABASE_STATS_METRICS:
            for tag in db_tags + ['database_state_desc:ONLINE']:
                aggregator.assert_metric_has_tag(metric_name, tag=tag)
            aggregator.assert_metric_has_tag_prefix(
                metric_name,
                tag_prefix='database_recovery_model_desc',
            )

        for metric_name, _, _ in DATABASE_BACKUP_METRICS:
            aggregator.assert_metric(metric_name, tags=db_tags, hostname=sqlserver_check.resolved_hostname, count=1)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_index_usage_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    bob_conn,
):
    instance_docker_metrics['database'] = 'datadog_test'
    instance_docker_metrics['include_index_usage_metrics'] = True

    # Cause an index seek
    bob_conn.execute_with_retries(
        query="SELECT * FROM datadog_test.dbo.ϑings WHERE name = 'foo'",
        database=instance_docker_metrics['database'],
        retries=1,
        return_result=False,
    )
    # Cause an index scan
    bob_conn.execute_with_retries(
        query="SELECT * FROM datadog_test.dbo.ϑings WHERE name LIKE '%foo%'",
        database=instance_docker_metrics['database'],
        retries=1,
        return_result=False,
    )
    # Cause an index lookup
    bob_conn.execute_with_retries(
        query="SELECT id FROM datadog_test.dbo.ϑings WHERE name = 'foo'",
        database=instance_docker_metrics['database'],
        retries=1,
        return_result=False,
    )
    # Cause an index update
    bob_conn.execute_with_retries(
        query="UPDATE datadog_test.dbo.ϑings SET id = 1 WHERE name = 'foo'",
        database=instance_docker_metrics['database'],
        retries=1,
        return_result=False,
    )

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags)

    for metric_name, _, _ in DATABASE_INDEX_METRICS:
        expected_tags = tags + [
            'db:{}'.format(instance_docker_metrics['database']),
            'index_name:thingsindex',
            'table:ϑings',
        ]
        aggregator.assert_metric(metric_name, tags=expected_tags, hostname=sqlserver_check.resolved_hostname, count=1)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_task_scheduler_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
):
    instance_docker_metrics['include_task_scheduler_metrics'] = True

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags)

    for metric_name, _, _ in TASK_SCHEDULER_METRICS:
        for tag in tags:
            aggregator.assert_metric_has_tag(metric_name, tag=tag)
        for tag_prefix in ('scheduler_id',):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name, _, _ in OS_SCHEDULER_METRICS:
        for tag_prefix in ('parent_node_id',):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_master_files_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
):
    instance_docker_metrics['include_master_files_metrics'] = True

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags)

    dbs = AUTODISCOVERY_DBS + ['model', 'tempdb']

    for db in dbs:
        for metric_name, _, _ in DATABASE_MASTER_FILES:
            db_tags = tags + ['database:{}'.format(db), 'db:{}'.format(db)]
            for tag in db_tags + ['database_files_state_desc:ONLINE']:
                aggregator.assert_metric_has_tag(
                    metric_name,
                    tag=tag,
                )
            for tag_prefix in ('file_id', 'file_type', 'file_location'):
                aggregator.assert_metric_has_tag_prefix(
                    metric_name,
                    tag_prefix=tag_prefix,
                )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize("database_autodiscovery", [True, False])
def test_check_db_fragmentation_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    database_autodiscovery,
):
    instance_docker_metrics['include_db_fragmentation_metrics'] = True
    instance_docker_metrics['database_autodiscovery'] = database_autodiscovery
    if database_autodiscovery:
        instance_docker_metrics['autodiscovery_include'] = AUTODISCOVERY_DBS

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags)

    dbs = AUTODISCOVERY_DBS if database_autodiscovery else ['master']

    for db in dbs:
        db_tags = tags + ['database_name:{}'.format(db), 'db:{}'.format(db)]
        for metric_name, _, _ in DATABASE_FRAGMENTATION_METRICS:
            for tag in db_tags:
                aggregator.assert_metric_has_tag(metric_name, tag=tag)
            for tag_prefix in ('index_id', 'index_name', 'object_name'):
                aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_tempdb_file_space_usage_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
):
    instance_docker_metrics['include_tempdb_file_space_usage_metrics'] = True

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags)

    for metric_name, _, _ in TEMPDB_FILE_SPACE_USAGE_METRICS:
        expected_tags = tags + ['database:tempdb', 'database_id:2', 'db:tempdb']
        aggregator.assert_metric(metric_name, tags=expected_tags, hostname=sqlserver_check.resolved_hostname, count=1)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_incr_fraction_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    bob_conn,
):
    instance_docker_metrics['database'] = 'datadog_test'
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    sqlserver_check.run()

    # Creating a test case to assert changes in the "Average Latch Wait Time (ms)" may be a bit tricky
    # since latches are internal mechanisms used by SQL Server to manage access to its data structures.
    # However, we can try to generate latch contention artificially by execute from multiple threads to
    # increase the chance of getting a non-zero value
    executor = ThreadPoolExecutor(max_workers=5)
    for _ in range(5):
        executor.submit(
            bob_conn.execute_with_retries,
            query="SELECT * FROM datadog_test.dbo.ϑings WHERE name = 'foo'",
            database=instance_docker_metrics['database'],
            retries=1,
            return_result=False,
        )
    executor.shutdown(wait=True)

    sqlserver_check.run()

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags)

    for metric_name in INCR_FRACTION_METRICS:
        aggregator.assert_metric(metric_name, tags=tags, hostname=sqlserver_check.resolved_hostname, count=1)

    sqlserver_check.cancel()


def check_sqlserver_can_connect(aggregator, host, resolved_hostname, tags):
    expected_tags = tags + [
        'connection_host:{}'.format(host),
        'sqlserver_host:{}'.format(resolved_hostname),
        'db:master',
    ]
    aggregator.assert_service_check('sqlserver.can_connect', status=SQLServer.OK, tags=expected_tags)
