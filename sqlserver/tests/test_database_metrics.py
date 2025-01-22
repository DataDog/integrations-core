# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from copy import deepcopy
from decimal import Decimal
from unittest import mock

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import (
    STATIC_INFO_ENGINE_EDITION,
    STATIC_INFO_MAJOR_VERSION,
)
from datadog_checks.sqlserver.database_metrics import (
    SqlserverAoMetrics,
    SqlserverAvailabilityGroupsMetrics,
    SqlserverAvailabilityReplicasMetrics,
    SqlserverDatabaseBackupMetrics,
    SqlserverDatabaseFilesMetrics,
    SqlserverDatabaseReplicationStatsMetrics,
    SqlserverDatabaseStatsMetrics,
    SqlserverDBFragmentationMetrics,
    SqlserverFciMetrics,
    SqlserverFileStatsMetrics,
    SqlserverIndexUsageMetrics,
    SqlserverMasterFilesMetrics,
    SqlserverOsSchedulersMetrics,
    SqlserverOsTasksMetrics,
    SqlserverPrimaryLogShippingMetrics,
    SqlserverSecondaryLogShippingMetrics,
    SqlserverServerStateMetrics,
    SqlserverTempDBFileSpaceUsageMetrics,
)

from .common import (
    CHECK_NAME,
    SQLSERVER_ENGINE_EDITION,
    SQLSERVER_MAJOR_VERSION,
)

INCR_FRACTION_METRICS = {'sqlserver.latches.latch_wait_time'}
AUTODISCOVERY_DBS = ['master', 'msdb', 'datadog_test-1']

STATIC_SERVER_INFO = {
    STATIC_INFO_MAJOR_VERSION: SQLSERVER_MAJOR_VERSION,
    STATIC_INFO_ENGINE_EDITION: SQLSERVER_ENGINE_EDITION,
}


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_file_stats_metrics', [True, False])
def test_sqlserver_file_stats_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_file_stats_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'file_stats_metrics': {'enabled': include_file_stats_metrics},
    }

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
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [file_stats_metrics]

    dd_run_check(sqlserver_check)

    if not include_file_stats_metrics:
        assert file_stats_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
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
    instance_docker_metrics['database_metrics'] = {
        'ao_metrics': {'enabled': include_ao_metrics},
    }

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
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [ao_metrics]

    dd_run_check(sqlserver_check)

    if not include_ao_metrics:
        assert ao_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
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
@pytest.mark.parametrize('include_ao_metrics', [True, False])
@pytest.mark.parametrize(
    'availability_group,mocked_results',
    [
        pytest.param(
            None,
            [('AG1', 'AG1', 'HEALTHY', 2, 1, None), ('AG2', 'AG2', 'HEALTHY', 2, 1, None)],
            id='no availability_group',
        ),
        pytest.param('AG1', [('AG1', 'AG1', 'HEALTHY', 2, 1, None)], id='availability_group set'),
    ],
)
def test_sqlserver_availability_groups_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_ao_metrics,
    availability_group,
    mocked_results,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'ao_metrics': {'enabled': include_ao_metrics},
    }
    if availability_group:
        instance_docker_metrics['database_metrics']['ao_metrics']['availability_group'] = availability_group

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    availability_groups_metrics = SqlserverAvailabilityGroupsMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    if availability_group:
        assert availability_groups_metrics.queries[0]['query'].endswith(
            f" where resource_group_id = '{availability_group}'"
        )

    sqlserver_check._database_metrics = [availability_groups_metrics]

    dd_run_check(sqlserver_check)

    if not include_ao_metrics:
        assert availability_groups_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            ag, availability_group_name, synchronization_health_desc, *metric_values = result
            metrics = zip(availability_groups_metrics.metric_names()[0], metric_values)
            expected_tags = [
                f'availability_group:{ag}',
                f'availability_group_name:{availability_group_name}',
                f'synchronization_health_desc:{synchronization_health_desc}',
            ] + tags
            for metric_name, metric_value in metrics:
                if metric_value is not None:
                    aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)
            if availability_group:
                assert ag == availability_group


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_ao_metrics', [True, False])
@pytest.mark.parametrize(
    'availability_group,only_emit_local,mocked_results',
    [
        pytest.param(
            None,
            None,
            [('AG1', 'AG1', 'aoag_secondary', 'SYNCHRONIZED', 2), ('AG1', 'AG1', 'aoag_primary', 'SYNCHRONIZED', 2)],
            id='no availability_group, no only_emit_local',
        ),
        pytest.param(
            'AG1',
            None,
            [('AG1', 'AG1', 'aoag_secondary', 'SYNCHRONIZED', 2), ('AG1', 'AG1', 'aoag_primary', 'SYNCHRONIZED', 2)],
            id='availability_group set, no only_emit_local',
        ),
        pytest.param(
            None,
            True,
            [('AG1', 'AG1', 'aoag_primary', 'SYNCHRONIZED', 2)],
            id='no availability_group, only_emit_local is True',
        ),
        pytest.param(
            'AG1',
            True,
            [('AG1', 'AG1', 'aoag_primary', 'SYNCHRONIZED', 2)],
            id='availability_group set, only_emit_local is True',
        ),
    ],
)
def test_sqlserver_database_replication_stats_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_ao_metrics,
    availability_group,
    only_emit_local,
    mocked_results,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'ao_metrics': {'enabled': include_ao_metrics},
    }
    if availability_group:
        instance_docker_metrics['database_metrics']['ao_metrics']['availability_group'] = availability_group
    if only_emit_local:
        instance_docker_metrics['database_metrics']['ao_metrics']['only_emit_local'] = only_emit_local

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    database_replication_stats_metrics = SqlserverDatabaseReplicationStatsMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    if availability_group:
        assert f"resource_group_id = '{availability_group}'" in database_replication_stats_metrics.queries[0]['query']
    if only_emit_local:
        assert "is_local = 1" in database_replication_stats_metrics.queries[0]['query']

    sqlserver_check._database_metrics = [database_replication_stats_metrics]

    dd_run_check(sqlserver_check)

    if not include_ao_metrics:
        assert database_replication_stats_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            ag, availability_group_name, replica_server_name, synchronization_state_desc, *metric_values = result
            metrics = zip(database_replication_stats_metrics.metric_names()[0], metric_values)
            expected_tags = [
                f'availability_group:{ag}',
                f'availability_group_name:{availability_group_name}',
                f'replica_server_name:{replica_server_name}',
                f'synchronization_state_desc:{synchronization_state_desc}',
            ] + tags
            for metric_name, metric_value in metrics:
                if metric_value is not None:
                    aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)
            if availability_group:
                assert ag == availability_group


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_ao_metrics', [True, False])
@pytest.mark.parametrize(
    'availability_group,only_emit_local,ao_database,mocked_results',
    [
        pytest.param(
            None,
            None,
            None,
            [
                ('datadog_test', 'AG1', 'AG1', 'aoag_primary', 'MANUAL', True, 1, True),
                ('datadog_test', 'AG1', 'AG1', 'aoag_secondary', 'MANUAL', False, 1, True),
            ],
            id='no availability_group, no only_emit_local, no ao_database',
        ),
        pytest.param(
            'AG1',
            None,
            None,
            [
                ('datadog_test', 'AG1', 'AG1', 'aoag_primary', 'MANUAL', True, 1, True),
                ('datadog_test', 'AG1', 'AG1', 'aoag_secondary', 'MANUAL', False, 1, True),
            ],
            id='availability_group set, no only_emit_local, no ao_database',
        ),
        pytest.param(
            None,
            True,
            None,
            [('datadog_test', 'AG1', 'AG1', 'aoag_primary', 'MANUAL', True, 1, True)],
            id='no availability_group, only_emit_local is True, no ao_database',
        ),
        pytest.param(
            'AG1',
            True,
            None,
            [('datadog_test', 'AG1', 'AG1', 'aoag_primary', 'MANUAL', True, 1, True)],
            id='availability_group set, only_emit_local is True, no ao_database',
        ),
        pytest.param(
            None,
            None,
            'my_db',
            [],
            id='no availability_group, no only_emit_local, ao_database set',
        ),
        pytest.param(
            'AG1',
            None,
            'datadog_test',
            [
                ('datadog_test', 'AG1', 'AG1', 'aoag_primary', 'MANUAL', True, 1, True),
                ('datadog_test', 'AG1', 'AG1', 'aoag_secondary', 'MANUAL', False, 1, True),
            ],
            id='availability_group set, no only_emit_local, ao_database set',
        ),
        pytest.param(
            None,
            True,
            'datadog_test',
            [('datadog_test', 'AG1', 'AG1', 'aoag_primary', 'MANUAL', True, 1, True)],
            id='no availability_group, only_emit_local is True, ao_database set',
        ),
        pytest.param(
            'AG1',
            True,
            'datadog_test',
            [('datadog_test', 'AG1', 'AG1', 'aoag_primary', 'MANUAL', True, 1, True)],
            id='availability_group set, only_emit_local is True, ao_database set',
        ),
    ],
)
def test_sqlserver_availability_replicas_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_ao_metrics,
    availability_group,
    only_emit_local,
    ao_database,
    mocked_results,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'ao_metrics': {'enabled': include_ao_metrics},
    }
    if availability_group:
        instance_docker_metrics['database_metrics']['ao_metrics']['availability_group'] = availability_group
    if only_emit_local:
        instance_docker_metrics['database_metrics']['ao_metrics']['only_emit_local'] = only_emit_local
    if ao_database:
        instance_docker_metrics['database_metrics']['ao_metrics']['ao_database'] = ao_database

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    availability_replicas_metrics = SqlserverAvailabilityReplicasMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    if availability_group:
        assert f"resource_group_id = '{availability_group}'" in availability_replicas_metrics.queries[0]['query']
    if only_emit_local:
        assert "is_local = 1" in availability_replicas_metrics.queries[0]['query']
    if ao_database:
        assert f"database_name = '{ao_database}'" in availability_replicas_metrics.queries[0]['query']

    sqlserver_check._database_metrics = [availability_replicas_metrics]

    dd_run_check(sqlserver_check)

    if not include_ao_metrics:
        assert availability_replicas_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            (
                database_name,
                ag,
                availability_group_name,
                replica_server_name,
                failover_mode_desc,
                is_primary_replica,
                *metric_values,
            ) = result
            metrics = zip(availability_replicas_metrics.metric_names()[0], metric_values)
            expected_tags = [
                f'db:{database_name}',
                f'availability_group:{ag}',
                f'availability_group_name:{availability_group_name}',
                f'replica_server_name:{replica_server_name}',
                f'failover_mode_desc:{failover_mode_desc}',
                f'is_primary_replica:{is_primary_replica}',
            ] + tags
            for metric_name, metric_value in metrics:
                if metric_value is not None:
                    aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)
            if availability_group:
                assert ag == availability_group


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
    instance_docker_metrics['database_metrics'] = {
        'fci_metrics': {'enabled': include_fci_metrics},
    }

    mocked_results = [
        ('node1', 'up', 'cluster1', 0, 1),
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    fci_metrics = SqlserverFciMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [fci_metrics]

    dd_run_check(sqlserver_check)

    if not include_fci_metrics:
        assert fci_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
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
    instance_docker_metrics['database_metrics'] = {
        'primary_log_shipping_metrics': {'enabled': include_primary_log_shipping_metrics},
    }
    mocked_results = [('97E29D89-2FA0-44FF-9EF7-65DA75FE0E3E', 'EC2AMAZ-Q0NCNV5', 'MyDummyDB', 500, 3600)]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    primary_log_shipping_metrics = SqlserverPrimaryLogShippingMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [primary_log_shipping_metrics]

    dd_run_check(sqlserver_check)

    if not include_primary_log_shipping_metrics:
        assert primary_log_shipping_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
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
    instance_docker_metrics['database_metrics'] = {
        'secondary_log_shipping_metrics': {'enabled': include_secondary_log_shipping_metrics},
    }
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
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [primary_log_shipping_metrics]

    dd_run_check(sqlserver_check)

    if not include_secondary_log_shipping_metrics:
        assert primary_log_shipping_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
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
@pytest.mark.parametrize('include_server_state_metrics', [True, False])
def test_sqlserver_server_state_metrics(
    aggregator, dd_run_check, init_config, instance_docker_metrics, include_server_state_metrics
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'server_state_metrics': {'enabled': include_server_state_metrics},
    }

    mocked_results = [(1000, 4, 8589934592, 17179869184, 4294967296, 8589934592)]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    server_state_metrics = SqlserverServerStateMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [server_state_metrics]

    dd_run_check(sqlserver_check)

    if not include_server_state_metrics:
        assert server_state_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            metrics = zip(server_state_metrics.metric_names()[0], result)
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_tempdb_file_space_usage_metrics', [True, False])
def test_sqlserver_tempdb_file_space_usage_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_tempdb_file_space_usage_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'tempdb_file_space_usage_metrics': {'enabled': include_tempdb_file_space_usage_metrics}
    }
    mocked_results = [
        [(2, Decimal('5.375000'), Decimal('0.000000'), Decimal('0.000000'), Decimal('1.312500'), Decimal('1.312500'))]
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    tempdb_file_space_usage_metrics = SqlserverTempDBFileSpaceUsageMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [tempdb_file_space_usage_metrics]

    dd_run_check(sqlserver_check)

    if not include_tempdb_file_space_usage_metrics:
        assert tempdb_file_space_usage_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            database_id, *metric_values = result
            metrics = zip(tempdb_file_space_usage_metrics.metric_names()[0], metric_values)
            expected_tags = [
                f'database_id:{database_id}',
                'db:tempdb',
                'database:tempdb',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


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
    instance_docker_metrics['database_metrics'] = {
        'index_usage_metrics': {
            'enabled': include_index_usage_metrics,
            'enabled_tempdb': include_index_usage_metrics_tempdb,
        },
    }
    if index_usage_stats_interval:
        instance_docker_metrics['database_metrics']['index_usage_metrics'][
            'collection_interval'
        ] = index_usage_stats_interval

    mocked_results_non_tempdb = [
        [
            ('master', 'PK__patch_ac__09EA1DC2BD2BC49C', 'dbo', 'patch_action_execution_state', 36, 0, 0, 0),
            ('master', 'PK__rds_comp__2E7CCD4A9E2910C9', 'dbo', 'rds_component_version', 0, 5, 0, 0),
        ],
        [
            ('msdb', 'PK__backupse__21F79AAB9439648C', 'dbo', 'backupset', 0, 1, 0, 0),
        ],
        [
            ('datadog_test-1', 'idx_something', 'dbo', 'some_table', 10, 60, 12, 18),
            ('datadog_test-1', 'idx_something_else', 'dbo', 'some_table', 20, 30, 40, 50),
        ],
    ]
    mocked_results_tempdb = [
        ('tempdb', 'PK__dmv_view__B5A34EE25D72CBFE', 'dbo', 'dmv_view_run_history', 1500, 0, 0, 49),
    ]
    mocked_results = mocked_results_non_tempdb
    if include_index_usage_metrics_tempdb:
        mocked_results += [mocked_results_tempdb]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    execute_query_handler_mocked = mock.MagicMock()
    execute_query_handler_mocked.side_effect = mocked_results

    index_usage_metrics = SqlserverIndexUsageMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
        databases=AUTODISCOVERY_DBS + ['tempdb'],
    )

    expected_collection_interval = index_usage_stats_interval or index_usage_metrics.collection_interval
    assert index_usage_metrics.queries[0]['collection_interval'] == expected_collection_interval

    sqlserver_check._database_metrics = [index_usage_metrics]

    dd_run_check(sqlserver_check)

    if not include_index_usage_metrics:
        assert index_usage_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            for row in result:
                db, index_name, schema, table, *metric_values = row
                metrics = zip(index_usage_metrics.metric_names()[0], metric_values)
                expected_tags = [
                    f'db:{db}',
                    f'index_name:{index_name}',
                    f'schema:{schema}',
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
    instance_docker_metrics['database_metrics'] = {
        'db_fragmentation_metrics': {
            'enabled': include_db_fragmentation_metrics,
            'enabled_tempdb': include_db_fragmentation_metrics_tempdb,
        },
    }
    if db_fragmentation_metrics_interval:
        instance_docker_metrics['database_metrics']['db_fragmentation_metrics'][
            'collection_interval'
        ] = db_fragmentation_metrics_interval
    print(instance_docker_metrics)
    mocked_results = [
        [
            ('master', 'spt_fallback_db', 'dbo', 0, None, 0, 0.0, 0, 0.0),
            ('master', 'spt_fallback_dev', 'dbo', 0, None, 0, 0.0, 0, 0.0),
            ('master', 'spt_fallback_usg', 'dbo', 0, None, 0, 0.0, 0, 0.0),
            ('master', 'spt_monitor', 'dbo', 0, None, 1, 1.0, 1, 0.0),
            ('master', 'MSreplication_options', 'dbo', 0, None, 1, 1.0, 1, 0.0),
        ],
        [
            ('msdb', 'syscachedcredentials', 'dbo', 1, 'PK__syscache__F6D56B562DA81DC6', 0, 0.0, 0, 0.0),
            (
                'msdb',
                'syscollector_blobs_internal',
                'dbo',
                1,
                'PK_syscollector_blobs_internal_paremeter_name',
                0,
                0.0,
                0,
                0.0,
            ),
        ],
        [('datadog_test-1', 'ϑings', 'dbo', 1, 'thingsindex', 1, 1.0, 1, 0.0)],
    ]
    mocked_results_tempdb = [
        [('tempdb', '#TempExample__000000000008', 'dbo', 1, 'PK__#TempExa__3214EC278A26D67E', 1, 1.0, 1, 0.0)],
    ]

    if db_fragmentation_object_names:
        instance_docker_metrics['db_fragmentation_object_names'] = db_fragmentation_object_names
        mocked_results = [
            [
                ('master', 'spt_fallback_db', 'dbo', 0, None, 0, 0.0, 0, 0.0),
                ('master', 'spt_fallback_dev', 'dbo', 0, None, 0, 0.0, 0, 0.0),
                ('master', 'spt_fallback_usg', 'dbo', 0, None, 0, 0.0, 0, 0.0),
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
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
        databases=AUTODISCOVERY_DBS + ['tempdb'],
    )

    if db_fragmentation_object_names:
        assert db_fragmentation_metrics.db_fragmentation_object_names == db_fragmentation_object_names

    expected_collection_interval = db_fragmentation_metrics_interval or db_fragmentation_metrics.collection_interval
    assert db_fragmentation_metrics.queries[0]['collection_interval'] == expected_collection_interval

    sqlserver_check._database_metrics = [db_fragmentation_metrics]

    dd_run_check(sqlserver_check)

    if not include_db_fragmentation_metrics:
        assert db_fragmentation_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            for row in result:
                database_name, object_name, schema, index_id, index_name, *metric_values = row
                metrics = zip(db_fragmentation_metrics.metric_names()[0], metric_values)
                expected_tags = [
                    f'db:{database_name}',
                    f'database_name:{database_name}',
                    f'object_name:{object_name}',
                    f'schema:{schema}',
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
@pytest.mark.parametrize('include_task_scheduler_metrics', [True, False])
def test_sqlserver_os_schedulers_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_task_scheduler_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'task_scheduler_metrics': {'enabled': include_task_scheduler_metrics},
    }

    mocked_results = [
        (0, 0, 4, 6, 4, 0, 0),
        (1, 0, 5, 7, 4, 0, 0),
        (2, 0, 5, 6, 5, 0, 0),
        (3, 0, 4, 6, 4, 0, 0),
        (4, 0, 4, 7, 3, 0, 0),
        (1048578, 0, 1, 1, 1, 0, 0),
        (5, 1, 5, 7, 4, 0, 0),
        (6, 1, 4, 6, 3, 0, 0),
        (7, 1, 4, 7, 4, 0, 0),
        (8, 1, 3, 5, 3, 0, 0),
        (9, 1, 4, 7, 3, 0, 0),
        (1048579, 1, 1, 1, 1, 0, 0),
        (1048576, 64, 2, 3, 1, 0, 0),
        (1048580, 0, 1, 1, 1, 0, 0),
        (1048581, 0, 1, 1, 1, 0, 0),
        (1048582, 0, 1, 1, 1, 0, 0),
        (1048583, 0, 1, 1, 1, 0, 0),
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    os_schedulers_metrics = SqlserverOsSchedulersMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [os_schedulers_metrics]

    dd_run_check(sqlserver_check)

    if not include_task_scheduler_metrics:
        assert os_schedulers_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            scheduler_id, parent_node_id, *metric_values = result
            metrics = zip(os_schedulers_metrics.metric_names()[0], metric_values)
            expected_tags = [
                f'scheduler_id:{scheduler_id}',
                f'parent_node_id:{parent_node_id}',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_task_scheduler_metrics', [True, False])
def test_sqlserver_os_tasks_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_task_scheduler_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'task_scheduler_metrics': {'enabled': include_task_scheduler_metrics},
    }
    mocked_results = [
        (0, 40, 0, 0, 0),
        (9, 46, 0, 0, 0),
        (3, 17, 0, 0, 0),
        (6, 14, 0, 0, 0),
        (1048580, 427, 89, 0, 0),
        (7, 353, 0, 0, 0),
        (1, 201, 3, 0, 0),
        (1048583, 4, 0, 0, 0),
        (4, 734, 0, 0, 0),
        (1048578, 5, 0, 0, 0),
        (5, 152, 12, 0, 0),
        (1048581, 429, 92, 0, 0),
        (2, 1590, 223, 0, 0),
        (1048582, 56, 0, 0, 0),
        (1048579, 5, 0, 0, 0),
        (1048576, 6, 0, 0, 0),
        (8, 150, 43, 0, 0),
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    os_tasks_metrics = SqlserverOsTasksMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [os_tasks_metrics]

    dd_run_check(sqlserver_check)

    if not include_task_scheduler_metrics:
        assert os_tasks_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            scheduler_id, *metric_values = result
            metrics = zip(os_tasks_metrics.metric_names()[0], metric_values)
            expected_tags = [
                f'scheduler_id:{scheduler_id}',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_master_files_metrics', [True, False])
def test_sqlserver_master_files_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_master_files_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'master_files_metrics': {'enabled': include_master_files_metrics},
    }
    mocked_results = [
        ('master', 'master', 1, 'data', '/var/opt/mssql/data/master.mdf', 'ONLINE', 4096, 0),
        ('master', 'master', 2, 'transaction_log', '/var/opt/mssql/data/mastlog.ldf', 'ONLINE', 512, 0),
        ('tempdb', 'tempdb', 1, 'data', '/var/opt/mssql/data/tempdb.mdf', 'ONLINE', 8192, 0),
        ('tempdb', 'tempdb', 2, 'transaction_log', '/var/opt/mssql/data/templog.ldf', 'ONLINE', 8192, 0),
        ('model', 'model', 1, 'data', '/var/opt/mssql/data/model.mdf', 'ONLINE', 8192, 0),
        ('model', 'model', 2, 'transaction_log', '/var/opt/mssql/data/modellog.ldf', 'ONLINE', 8192, 0),
        ('msdb', 'msdb', 1, 'data', '/var/opt/mssql/data/MSDBData.mdf', 'ONLINE', 13696, 0),
        ('msdb', 'msdb', 2, 'transaction_log', '/var/opt/mssql/data/MSDBLog.ldf', 'ONLINE', 512, 0),
        ('datadog_test', 'datadog_test', 1, 'data', '/var/opt/mssql/data/datadog_test.mdf', 'ONLINE', 8192, 0),
        (
            'datadog_test',
            'datadog_test',
            2,
            'transaction_log',
            '/var/opt/mssql/data/datadog_test_log.ldf',
            'ONLINE',
            8192,
            0,
        ),
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    master_files_metrics = SqlserverMasterFilesMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [master_files_metrics]

    dd_run_check(sqlserver_check)

    if not include_master_files_metrics:
        assert master_files_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            db, database, file_id, file_type, file_location, database_files_state_desc, size, state = result
            size *= 8  # size is in pages, 1 page = 8 KB
            metrics = zip(master_files_metrics.metric_names()[0], [state, size])
            expected_tags = [
                f'db:{db}',
                f'database:{database}',
                f'file_id:{file_id}',
                f'file_type:{file_type}',
                f'file_location:{file_location}',
                f'database_files_state_desc:{database_files_state_desc}',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_database_files_metrics', [True, False])
def test_sqlserver_database_files_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_database_files_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'db_files_metrics': {'enabled': include_database_files_metrics},
    }

    mocked_results = [
        [
            (1, 'data', '/var/opt/mssql/data/master.mdf', 'master', 'ONLINE', 4096, 0, 4096),
            (2, 'transaction_log', '/var/opt/mssql/data/mastlog.ldf', 'mastlog', 'ONLINE', 768, 0, 424),
        ],
        [
            (1, 'data', '/var/opt/mssql/data/MSDBData.mdf', 'MSDBData', 'ONLINE', 13696, 0, 13696),
            (2, 'transaction_log', '/var/opt/mssql/data/MSDBLog.ldf', 'MSDBLog', 'ONLINE', 512, 0, 432),
        ],
        [
            (1, 'data', '/var/opt/mssql/data/datadog_test.mdf', 'datadog_test', 'ONLINE', 8192, 0, 2624),
            (
                2,
                'transaction_log',
                '/var/opt/mssql/data/datadog_test_log.ldf',
                'datadog_test_log',
                'ONLINE',
                8192,
                0,
                488,
            ),
        ],
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    execute_query_handler_mocked = mock.MagicMock()
    execute_query_handler_mocked.side_effect = mocked_results

    database_files_metrics = SqlserverDatabaseFilesMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
        databases=AUTODISCOVERY_DBS,
    )

    sqlserver_check._database_metrics = [database_files_metrics]

    dd_run_check(sqlserver_check)

    if not include_database_files_metrics:
        assert database_files_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for db, result in zip(AUTODISCOVERY_DBS, mocked_results):
            for row in result:
                file_id, file_type, file_location, file_name, database_files_state_desc, size, space_used, state = row
                size *= 8  # size is in pages, 1 page = 8 KB
                space_used *= 8  # space_used is in pages, 1 page = 8 KB
                metrics = zip(database_files_metrics.metric_names()[0], [state, size, space_used])
                expected_tags = [
                    f'db:{db}',
                    f'database:{db}',
                    f'file_id:{file_id}',
                    f'file_type:{file_type}',
                    f'file_location:{file_location}',
                    f'file_name:{file_name}',
                    f'database_files_state_desc:{database_files_state_desc}',
                ] + tags
                for metric_name, metric_value in metrics:
                    aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('include_database_files_metrics', [True, False])
def test_sqlserver_database_stats_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    include_database_files_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'db_stats_metrics': {'enabled': include_database_files_metrics},
    }

    mocked_results = [
        ('master', 'master', 'ONLINE', 'SIMPLE', 0, False, False, False),
        ('tempdb', 'tempdb', 'ONLINE', 'SIMPLE', 0, False, False, False),
        ('model', 'model', 'ONLINE', 'FULL', 0, False, False, False),
        ('msdb', 'msdb', 'ONLINE', 'SIMPLE', 0, False, False, False),
        ('datadog_test', 'datadog_test', 'ONLINE', 'FULL', 0, False, False, False),
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    database_stats_metrics = SqlserverDatabaseStatsMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    sqlserver_check._database_metrics = [database_stats_metrics]

    dd_run_check(sqlserver_check)

    if not include_database_files_metrics:
        assert database_stats_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
        for result in mocked_results:
            db, database, database_state_desc, database_recovery_model_desc, *metric_values = result
            metrics = zip(database_stats_metrics.metric_names()[0], metric_values)
            expected_tags = [
                f'db:{db}',
                f'database:{database}',
                f'database_state_desc:{database_state_desc}',
                f'database_recovery_model_desc:{database_recovery_model_desc}',
            ] + tags
            for metric_name, metric_value in metrics:
                aggregator.assert_metric(metric_name, value=metric_value, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('database_backup_metrics_interval', [None, 600])
@pytest.mark.parametrize('include_database_backup_metrics', [True, False])
def test_sqlserver_database_backup_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    database_backup_metrics_interval,
    include_database_backup_metrics,
):
    instance_docker_metrics['database_autodiscovery'] = True
    instance_docker_metrics['database_metrics'] = {
        'db_backup_metrics': {'enabled': include_database_backup_metrics},
    }
    if database_backup_metrics_interval:
        instance_docker_metrics['database_metrics']['db_backup_metrics'][
            'collection_interval'
        ] = database_backup_metrics_interval

    mocked_results = [
        ('master', 'master', 0),
        ('model', 'model', 2),
        ('msdb', 'msdb', 0),
        ('tempdb', 'tempdb', 0),
        ('datadog_test-1', 'datadog_test-1', 10),
    ]

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    def execute_query_handler_mocked(query, db=None):
        return mocked_results

    database_backup_metrics = SqlserverDatabaseBackupMetrics(
        config=sqlserver_check._config,
        new_query_executor=sqlserver_check._new_query_executor,
        server_static_info=STATIC_SERVER_INFO,
        execute_query_handler=execute_query_handler_mocked,
    )

    expected_collection_interval = database_backup_metrics_interval or database_backup_metrics.collection_interval
    assert database_backup_metrics.queries[0]['collection_interval'] == expected_collection_interval

    sqlserver_check._database_metrics = [database_backup_metrics]

    dd_run_check(sqlserver_check)
    if not include_database_backup_metrics:
        assert database_backup_metrics.enabled is False
    else:
        tags = sqlserver_check._config.tags
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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'config_options',
    [
        {'include_xe_metrics': True},
        {'deadlocks_collection': {'enabled': True}},
    ],
)
def test_sqlserver_xe_session_metrics(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
    config_options,
):
    modified_instance = deepcopy(instance_docker_metrics)
    for key, value in config_options.items():
        modified_instance[key] = value
    sqlserver_check = SQLServer(CHECK_NAME, init_config, [modified_instance])
    dd_run_check(sqlserver_check)
    expected_tags = sqlserver_check._config.tags
    expected_tags.append('session_name:datadog')
    aggregator.assert_metric("sqlserver.xe.session_status", value=1, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_sqlserver_database_metrics_defaults(
    aggregator,
    dd_run_check,
    init_config,
    instance_docker_metrics,
):
    include_defaults = {
        SqlserverAoMetrics: False,
        SqlserverAvailabilityGroupsMetrics: False,
        SqlserverAvailabilityReplicasMetrics: False,
        SqlserverDatabaseBackupMetrics: True,
        SqlserverDatabaseFilesMetrics: True,
        SqlserverDatabaseReplicationStatsMetrics: False,
        SqlserverDatabaseStatsMetrics: True,
        SqlserverDBFragmentationMetrics: False,
        SqlserverFciMetrics: False,
        SqlserverFileStatsMetrics: True,
        SqlserverIndexUsageMetrics: True,
        SqlserverMasterFilesMetrics: False,
        SqlserverOsSchedulersMetrics: False,
        SqlserverOsTasksMetrics: False,
        SqlserverPrimaryLogShippingMetrics: False,
        SqlserverSecondaryLogShippingMetrics: False,
        SqlserverServerStateMetrics: True,
        SqlserverTempDBFileSpaceUsageMetrics: True,
    }
    instance_docker_metrics['database_autodiscovery'] = True

    sqlserver_check = SQLServer(CHECK_NAME, init_config, [instance_docker_metrics])

    for metric, enabled in include_defaults.items():
        database_metrics = metric(
            config=sqlserver_check._config,
            new_query_executor=sqlserver_check._new_query_executor,
            server_static_info=STATIC_SERVER_INFO,
            execute_query_handler=None,
            databases=AUTODISCOVERY_DBS,
        )
        assert database_metrics.enabled == enabled
