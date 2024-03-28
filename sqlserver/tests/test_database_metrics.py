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
    SqlserverAoMetrics,
    SqlserverFciMetrics,
    SqlserverFileStatsMetrics,
    SqlserverPrimaryLogShippingMetrics,
    SqlserverSecondaryLogShippingMetrics,
    SqlserverServerStateMetrics,
)

from .common import (
    CHECK_NAME,
    SQLSERVER_ENGINE_EDITION,
    SQLSERVER_MAJOR_VERSION,
)

INCR_FRACTION_METRICS = {'sqlserver.latches.latch_wait_time'}
AUTODISCOVERY_DBS = ['master', 'msdb', 'datadog_test']

STATIC_SERVER_INFO = {
    STATIC_INFO_MAJOR_VERSION: SQLSERVER_MAJOR_VERSION,
    STATIC_INFO_ENGINE_EDITION: SQLSERVER_ENGINE_EDITION,
}


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_sqlserver_file_stats_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True

    mocked_results = [
        ('master', 'ONLINE', 'master', '/xx/master.mdf', 89, 0, 0, 73, 16, 3153920, 933888, 59, 98, 4194304),
        ('master', 'ONLINE', 'mastlog', '/xx/mastlog.ldf', 22, 0, 0, 3, 19, 750592, 580608, 11, 97, 786432),
        ('tempdb', 'ONLINE', 'tempdev', '/xx/tempdb.mdf', 3, 0, 0, 3, 0, 1728512, 32768, 29, 4, 8388608),
        ('tempdb', 'ONLINE', 'templog', '/xx/templog.ldf', 1, 0, 0, 1, 0, 1007616, 16384, 7, 3, 8388608),
        ('model', 'ONLINE', 'modeldev', '/xx/model.mdf', 22, 0, 0, 17, 5, 35151872, 409600, 59, 44, 8388608),
        ('model', 'ONLINE', 'modellog', '/xx/modellog.ldf', 19, 0, 0, 12, 7, 1162752, 317440, 14, 48, 8388608),
        ('msdb', 'ONLINE', 'MSDBData', '/xx/MSDBData.mdf', 34, 0, 0, 29, 5, 3891200, 196608, 62, 23, 14024704),
        ('msdb', 'ONLINE', 'MSDBLog', '/xx/MSDBLog.ldf', 12, 0, 0, 3, 9, 1338368, 180736, 10, 30, 524288),
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    file_stats_metrics = SqlserverFileStatsMetrics(
        instance_config=instance_docker_metrics,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._dynamic_queries = [file_stats_metrics]

    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])
    for result in mocked_results:
        db, state, logical_name, file_location, *metric_values = result
        metrics = zip(file_stats_metrics.metric_names()[0], metric_values)
        expected_tags = [
            f'db:{db}',
            f'state:{state}',
            f'logical_name:{logical_name}',
            f'file_location:{file_location}',
        ] + tags
        for metric_name, metric_value in metrics:
            aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_ao_metrics', [True, False])
def test_sqlserver_ao_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_ao_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['include_ao_metrics'] = include_ao_metrics

    # Mocked results
    mocked_ao_availability_groups = [
        (
            'primary',  # replica_role
            'master',  # database_name
            '0769C993-7AD1-4BA0-B319-5C8580B9A686',  # availability_group
            'RDSAG0',  # availability_group_name
            'EC2AMAZ-J78JTN1',  # replica_server_name
            '5',  # database_id
            '119CFD6A-C903-4E9E-B44A-D29CDB6633AA',  # replica_id
            'rds_cluster',  # failover_cluster
            'synchronous_commit',  # availability_mode
            'automatic',  # failover_mode
            None,  # database_state
            'synchronized',  # synchronization_state
            1,  # filestream_send_rate
            5,  # log_send_queue_size
            1,  # log_send_rate
            50,  # redo_queue_size
            23,  # redo_rate
            1,  # replica_status
            1,  # is_primary_replica
            300,  # low_water_mark_for_ghosts
            1,  # secondary_lag_seconds
        ),
    ]
    mocked_ao_failover_cluster = [('node_majority', 'normal_quorum', '', 1, 1)]
    mocked_ao_failover_cluster_member = [('08cd6223c153', 'cluster_node', 'up', '', 1, 1, 1)]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    execute_query_handler_mocked = mock.MagicMock()
    execute_query_handler_mocked.side_effect = [
        mocked_ao_availability_groups,
        mocked_ao_failover_cluster,
        mocked_ao_failover_cluster_member,
    ]

    ao_metrics = SqlserverAoMetrics(
        instance_config=instance_docker_metrics,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._dynamic_queries = [ao_metrics]

    dd_run_check(sqlserver_check)

    if not include_ao_metrics:
        assert ao_metrics.enabled is False
    else:
        tags = instance_docker_metrics.get('tags', [])
        for result in mocked_ao_availability_groups:
            (
                replica_role,
                database_name,
                availability_group,
                availability_group_name,
                replica_server_name,
                database_id,
                replica_id,
                failover_cluster,
                availability_mode,
                failover_mode,
                database_state,
                synchronization_state,
                *metric_values,
            ) = result
            metrics = zip(
                ao_metrics.metric_names()[0],
                [
                    *metric_values,
                ],
            )
            expected_tags = [
                f'replica_role:{replica_role}',
                f'database_name:{database_name}',
                f'availability_group:{availability_group}',
                f'availability_group_name:{availability_group_name}',
                f'replica_server_name:{replica_server_name}',
                f'database_id:{database_id}',
                f'replica_id:{replica_id}',
                f'failover_cluster:{failover_cluster}',
                f'availability_mode:{availability_mode}',
                f'failover_mode:{failover_mode}',
                f'database_state:{database_state}',
                f'synchronization_state:{synchronization_state}',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)
        for result in mocked_ao_failover_cluster:
            quorum_type, quorum_state, failover_cluster, *metric_values = result
            metrics = zip(ao_metrics.metric_names()[1], metric_values)
            expected_tags = [
                f'quorum_type:{quorum_type}',
                f'quorum_state:{quorum_state}',
                f'failover_cluster:{failover_cluster}',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)
        for result in mocked_ao_failover_cluster_member:
            member_name, member_type, member_state, failover_cluster, *metric_values = result
            metrics = zip(ao_metrics.metric_names()[2], metric_values)
            expected_tags = [
                f'member_name:{member_name}',
                f'member_type:{member_type}',
                f'member_state:{member_state}',
                f'failover_cluster:{failover_cluster}',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_fci_metrics', [True, False])
def test_sqlserver_fci_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_fci_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['include_fci_metrics'] = include_fci_metrics

    mocked_results = [
        ('node1', 'up', 'cluster1', 0, 1),
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    fci_metrics = SqlserverFciMetrics(
        instance_config=instance_docker_metrics,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
        # execute_query_handler=sqlserver_check.execute_query_raw,
    )

    sqlserver_check._dynamic_queries = [fci_metrics]

    dd_run_check(sqlserver_check)

    if not include_fci_metrics:
        assert fci_metrics.enabled is False
    else:
        tags = instance_docker_metrics.get('tags', [])
        for result in mocked_results:
            node_name, status, failover_cluster, *metric_values = result
            metrics = zip(fci_metrics.metric_names()[0], metric_values)
            expected_tags = [
                f'node_name:{node_name}',
                f'status:{status}',
                f'failover_cluster:{failover_cluster}',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_primary_log_shipping_metrics', [True, False])
def test_sqlserver_primary_log_shipping_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_primary_log_shipping_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['include_primary_log_shipping_metrics'] = include_primary_log_shipping_metrics

    mocked_results = [('97E29D89-2FA0-44FF-9EF7-65DA75FE0E3E', 'EC2AMAZ-Q0NCNV5', 'MyDummyDB', 500, 3600)]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    primary_log_shipping_metrics = SqlserverPrimaryLogShippingMetrics(
        instance_config=instance_docker_metrics,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
        # execute_query_handler=sqlserver_check.execute_query_raw,
    )

    sqlserver_check._dynamic_queries = [primary_log_shipping_metrics]

    dd_run_check(sqlserver_check)

    if not include_primary_log_shipping_metrics:
        assert primary_log_shipping_metrics.enabled is False
    else:
        tags = instance_docker_metrics.get('tags', [])
        for result in mocked_results:
            primary_id, primary_server, primary_db, *metric_values = result
            metrics = zip(primary_log_shipping_metrics.metric_names()[0], metric_values)
            expected_tags = [
                f'primary_id:{primary_id}',
                f'primary_server:{primary_server}',
                f'primary_db:{primary_db}',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_secondary_log_shipping_metrics', [True, False])
def test_sqlserver_secondary_log_shipping_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_secondary_log_shipping_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['include_secondary_log_shipping_metrics'] = include_secondary_log_shipping_metrics

    mocked_results = [
        (
            r'EC2AMAZ-Q0NCNV5\MYSECONDARY',
            'MyDummyDB',
            '13269A43-4D79-4473-A8BE-300F0709FF49',
            'EC2AMAZ-Q0NCNV5',
            'MyDummyDB',
            800,
            13000000,
            125000,
            2700,
        )
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    primary_log_shipping_metrics = SqlserverSecondaryLogShippingMetrics(
        instance_config=instance_docker_metrics,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._dynamic_queries = [primary_log_shipping_metrics]

    dd_run_check(sqlserver_check)

    if not include_secondary_log_shipping_metrics:
        assert primary_log_shipping_metrics.enabled is False
    else:
        tags = instance_docker_metrics.get('tags', [])
        for result in mocked_results:
            secondary_server, secondary_db, secondary_id, primary_server, primary_db, *metric_values = result
            metrics = zip(primary_log_shipping_metrics.metric_names()[0], metric_values)
            expected_tags = [
                f'secondary_server:{secondary_server}',
                f'secondary_db:{secondary_db}',
                f'secondary_id:{secondary_id}',
                f'primary_server:{primary_server}',
                f'primary_db:{primary_db}',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_sqlserver_server_state_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True

    mocked_results = [(1000, 4, 8589934592, 17179869184, 4294967296, 8589934592)]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    server_state_metrics = SqlserverServerStateMetrics(
        instance_config=instance_docker_metrics,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._dynamic_queries = [server_state_metrics]

    dd_run_check(sqlserver_check)

    tags = instance_docker_metrics.get('tags', [])
    for result in mocked_results:
        metrics = zip(server_state_metrics.metric_names()[0], result)
        for metric_name, metric_value in metrics:
            aggregator.assert_metric(metric_name, value=metric_value, tags=tags)
