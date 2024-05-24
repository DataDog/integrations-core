# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import (
    AO_AG_SYNC_METRICS,
    AO_METRICS_PRIMARY,
    AO_METRICS_SECONDARY,
    AO_REPLICA_FAILOVER_METRICS,
    AO_REPLICA_SYNC_METRICS,
    DATABASE_BACKUP_METRICS,
    DATABASE_FILES_METRICS,
    DATABASE_FRAGMENTATION_METRICS,
    DATABASE_INDEX_METRICS,
    DATABASE_MASTER_FILES,
    DATABASE_SERVICE_CHECK_NAME,
    DATABASE_STATS_METRICS,
    DBM_MIGRATED_METRICS,
    INSTANCE_METRICS,
    INSTANCE_METRICS_DATABASE_AO,
    INSTANCE_METRICS_DATABASE_SINGLE,
    OS_SCHEDULER_METRICS,
    SERVICE_CHECK_NAME,
    TASK_SCHEDULER_METRICS,
    TEMPDB_FILE_SPACE_USAGE_METRICS,
)

from .common import (
    CHECK_NAME,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_MEMBER_COMMON,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_PRIMARY,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_QUORUM_COMMON,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_REPLICA_COMMON,
    EXPECTED_QUERY_EXECUTOR_AO_METRICS_SECONDARY,
    SERVER_METRICS,
    SQLSERVER_MAJOR_VERSION,
)
from .utils import always_on, is_always_on, not_windows_ci

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
@pytest.mark.parametrize("dbm_enabled", [True, False])
def test_check_instance_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    dbm_enabled,
):
    instance_docker_metrics['database_autodiscovery'] = False
    instance_docker_metrics['dbm'] = dbm_enabled
    instance_docker_metrics['include_instance_metrics'] = True

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(
        aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags, False
    )

    for metric_name, _, _, _ in INSTANCE_METRICS:
        # TODO: we should find a better way to test these metrics
        # remove SQL Server incremental sql fraction metrics for now
        if metric_name in INCR_FRACTION_METRICS:
            continue
        aggregator.assert_metric(metric_name, tags=tags, hostname=sqlserver_check.resolved_hostname, count=1)

    for metric_name, _, _, _ in INSTANCE_METRICS_DATABASE_SINGLE:
        aggregator.assert_metric(metric_name, tags=tags, hostname=sqlserver_check.resolved_hostname, count=1)

    if not dbm_enabled:
        for metric_name, _, _, _ in DBM_MIGRATED_METRICS:
            aggregator.assert_metric(metric_name, tags=tags, hostname=sqlserver_check.resolved_hostname, count=1)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_instance_metrics_autodiscovery(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['autodiscovery_include'] = AUTODISCOVERY_DBS
    instance_docker_metrics['include_instance_metrics'] = True

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])
    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(
        aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags, True
    )

    for metric_name, _, _, _ in INSTANCE_METRICS:
        # TODO: we should find a better way to test these metrics
        # remove SQL Server incremental sql fraction metrics for now
        if metric_name in INCR_FRACTION_METRICS:
            continue
        aggregator.assert_metric(metric_name, tags=tags, hostname=sqlserver_check.resolved_hostname, count=1)

    for db in AUTODISCOVERY_DBS:
        for metric_name, _, _, _ in INSTANCE_METRICS_DATABASE_SINGLE:
            aggregator.assert_metric(
                metric_name,
                tags=tags + ['database:{}'.format(db)],
                hostname=sqlserver_check.resolved_hostname,
                count=1,
            )
        if db == 'datadog_test' and is_always_on():
            for metric_name, _, _, _ in INSTANCE_METRICS_DATABASE_AO:
                aggregator.assert_metric(
                    metric_name,
                    tags=tags + ['database:{}'.format(db)],
                    hostname=sqlserver_check.resolved_hostname,
                    count=1,
                )


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

    check_sqlserver_can_connect(
        aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags, database_autodiscovery
    )

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
    instance_docker_metrics['ignore_missing_database'] = True

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

    for metric_name in DATABASE_INDEX_METRICS:
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

    check_sqlserver_can_connect(
        aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags, database_autodiscovery
    )

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
@pytest.mark.skipif(SQLSERVER_MAJOR_VERSION < 2016, reason='Metric not supported')
def test_check_incr_fraction_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    bob_conn_raw,
):
    instance_docker_metrics['database'] = 'datadog_test'
    instance_docker_metrics['ignore_missing_database'] = True
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    sqlserver_check.run()
    previous_value = copy.deepcopy(sqlserver_check.sqlserver_incr_fraction_metric_previous_values)

    cursor = bob_conn_raw.cursor()

    # Creating a test case to assert changes in the "Average Latch Wait Time (ms)" may be a bit tricky
    # since latches are internal mechanisms used by SQL Server to manage access to its data structures.
    # However, we can try to generate latch contention artificially by creating a hot spot in tempdb and
    # aggressively manipulating temporary tables. But this approach does not guarantee that the latch
    # contention will be high enough to trigger a change in the "Average Latch Wait Time (ms)" metric.
    cursor.execute(
        '''
    BEGIN
        CREATE TABLE #TempContention (
            ID INT IDENTITY PRIMARY KEY,
            SomeData CHAR(8000) -- Large row size to consume more space
        );

        DECLARE @i INT = 0;
        WHILE @i < 10000
        BEGIN
            INSERT INTO #TempContention (SomeData) VALUES (REPLICATE('X',8000));
            SET @i = @i + 1;
        END
        DROP TABLE #TempContention;
    END
    '''
    )
    sqlserver_check.run()
    cursor.close()

    tags = instance_docker_metrics.get('tags', [])

    check_sqlserver_can_connect(aggregator, instance_docker_metrics['host'], sqlserver_check.resolved_hostname, tags)

    for metric_name in INCR_FRACTION_METRICS:
        key = "{}:{}".format(metric_name, "".join(tags))
        if previous_value[key] == sqlserver_check.sqlserver_incr_fraction_metric_previous_values[key]:
            continue
        aggregator.assert_metric(metric_name, tags=tags, hostname=sqlserver_check.resolved_hostname, count=1)

    sqlserver_check.cancel()


@not_windows_ci
@always_on
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_ao_primary_replica(aggregator, dd_run_check, init_config, instance_ao_docker_primary):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_ao_docker_primary])
    dd_run_check(sqlserver_check)

    for metric_name, _, _ in AO_METRICS_PRIMARY:
        for tag_prefix in ('availability_group', 'availability_group_name', 'synchronization_health_desc'):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name, _, _ in AO_AG_SYNC_METRICS:
        for tag_prefix in ('availability_group', 'availability_group_name', 'synchronization_health_desc'):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name, _, _ in AO_REPLICA_SYNC_METRICS:
        for tag_prefix in (
            'availability_group',
            'availability_group_name',
            'synchronization_state_desc',
            'replica_server_name',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name, _, _ in AO_REPLICA_FAILOVER_METRICS:
        for tag_prefix in (
            'availability_group',
            'availability_group_name',
            'failover_mode_desc',
            'is_primary_replica',
            'replica_server_name',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name in EXPECTED_QUERY_EXECUTOR_AO_METRICS_PRIMARY:
        for tag_prefix in (
            'availability_group',
            'availability_group_name',
            'availability_mode',
            'database_id',
            'database_name',
            'database_state',
            'failover_cluster',
            'failover_mode',
            'replica_id',
            'replica_role',
            'replica_server_name',
            'synchronization_state',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name in EXPECTED_QUERY_EXECUTOR_AO_METRICS_REPLICA_COMMON:
        for tag_prefix in (
            'availability_group',
            'availability_group_name',
            'availability_mode',
            'database_id',
            'database_name',
            'database_state',
            'failover_cluster',
            'failover_mode',
            'replica_id',
            'replica_role',
            'replica_server_name',
            'synchronization_state',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name in EXPECTED_QUERY_EXECUTOR_AO_METRICS_QUORUM_COMMON:
        for tag_prefix in (
            'quorum_type',
            'quorum_state',
            'failover_cluster',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name in EXPECTED_QUERY_EXECUTOR_AO_METRICS_MEMBER_COMMON:
        for tag_prefix in (
            'member_name',
            'member_type',
            'member_state',
            'failover_cluster',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name, _, _ in AO_METRICS_SECONDARY:
        aggregator.assert_metric(metric_name, count=0)


@not_windows_ci
@always_on
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check_ao_secondary_replica(aggregator, dd_run_check, init_config, instance_ao_docker_secondary):
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_ao_docker_secondary])
    dd_run_check(sqlserver_check)

    for metric_name, _, _ in AO_METRICS_SECONDARY:
        for tag_prefix in ('availability_group', 'availability_group_name', 'synchronization_health_desc'):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name, _, _ in AO_AG_SYNC_METRICS:
        for tag_prefix in ('availability_group', 'availability_group_name', 'synchronization_health_desc'):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name, _, _ in AO_REPLICA_SYNC_METRICS:
        for tag_prefix in (
            'availability_group',
            'availability_group_name',
            'synchronization_state_desc',
            'replica_server_name',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name in EXPECTED_QUERY_EXECUTOR_AO_METRICS_SECONDARY:
        for tag_prefix in (
            'availability_group',
            'availability_group_name',
            'availability_mode',
            'database_id',
            'database_name',
            'database_state',
            'failover_cluster',
            'failover_mode',
            'replica_id',
            'replica_role',
            'replica_server_name',
            'synchronization_state',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name in EXPECTED_QUERY_EXECUTOR_AO_METRICS_REPLICA_COMMON:
        for tag_prefix in (
            'availability_group',
            'availability_group_name',
            'availability_mode',
            'database_id',
            'database_name',
            'database_state',
            'failover_cluster',
            'failover_mode',
            'replica_id',
            'replica_role',
            'replica_server_name',
            'synchronization_state',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name in EXPECTED_QUERY_EXECUTOR_AO_METRICS_QUORUM_COMMON:
        for tag_prefix in (
            'quorum_type',
            'quorum_state',
            'failover_cluster',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name in EXPECTED_QUERY_EXECUTOR_AO_METRICS_MEMBER_COMMON:
        for tag_prefix in (
            'member_name',
            'member_type',
            'member_state',
            'failover_cluster',
        ):
            aggregator.assert_metric_has_tag_prefix(metric_name, tag_prefix=tag_prefix)

    for metric_name, _, _ in AO_METRICS_PRIMARY:
        aggregator.assert_metric(metric_name, count=0)

    for metric_name in EXPECTED_QUERY_EXECUTOR_AO_METRICS_PRIMARY:
        aggregator.assert_metric(metric_name, count=0)


def check_sqlserver_can_connect(aggregator, host, resolved_hostname, tags, autodiscovery=False):
    expected_tags = tags + [
        'connection_host:{}'.format(host),
        'sqlserver_host:{}'.format(resolved_hostname),
        'db:master',
    ]
    aggregator.assert_service_check(SERVICE_CHECK_NAME, status=SQLServer.OK, tags=expected_tags)
    if autodiscovery:
        aggregator.assert_service_check(DATABASE_SERVICE_CHECK_NAME, status=SQLServer.OK, tags=expected_tags)
