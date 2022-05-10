# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

QUERY_FAILOVER_CLUSTER = {
    'name': 'sys.dm_hadr_cluster',
    'query': """
        SELECT
            cluster_name,
            quorum_type,
            quorum_type_desc,
            quorum_state,
            quorum_state_desc
        FROM sys.dm_hadr_cluster
    """.strip(),
    'columns': [
        {'name': 'failover_cluster', 'type': 'tag'},
        {'name': 'fc.quorum_type', 'type': 'gauge'},
        {'name': 'quorum_type_desc', 'type': 'tag'},
        {'name': 'fc.quorum_state', 'type': 'gauge'},
        {'name': 'quorum_state_desc', 'type': 'tag'},
    ],
}

QUERY_FAILOVER_CLUSTER_MEMBER = {
    'name': 'sys.dm_hadr_cluster_members',
    'query': """
        SELECT
            member_name,
            member_type,
            member_type_desc,
            member_state,
            member_state_desc,
            number_of_quorum_votes,
            FC.cluster_name
        FROM sys.dm_hadr_cluster_members
        CROSS APPLY (SELECT cluster_name FROM sys.dm_hadr_cluster) AS FC
    """.strip(),
    'columns': [
        {'name': 'member_name', 'type': 'tag'},
        {'name': 'fc.member.type', 'type': 'gauge'},
        {'name': 'member_type_desc', 'type': 'tag'},
        {'name': 'fc.member.state', 'type': 'gauge'},
        {'name': 'member_state_desc', 'type': 'tag'},
        {'name': 'fc.member.number_of_quorum_votes', 'type': 'gauge'},
        {'name': 'failover_cluster', 'type': 'tag'},
    ],
}

QUERY_FAILOVER_CLUSTER_INSTANCE = {
    'name': 'sys.dm_os_cluster_nodes',
    'query': """
        SELECT
            NodeName AS node_name,
            status,
            status_description,
            is_current_owner,
            FC.cluster_name
        FROM sys.dm_os_cluster_nodes
        CROSS APPLY (SELECT cluster_name FROM sys.dm_hadr_cluster) AS FC
    """.strip(),
    'columns': [
        {'name': 'node_name', 'type': 'tag'},
        {'name': 'fci.status', 'type': 'gauge'},
        {'name': 'status_desc', 'type': 'tag'},
        {'name': 'fci.is_current_owner', 'type': 'gauge'},
        {'name': 'failover_cluster', 'type': 'tag'},
    ],
}

QUERY_AVAILABILITY_GROUP_REPLICA_STATES = {
    'name': 'sys.dm_hadr_database_replica_states',
    'query': """
        SELECT
            DRS.group_id,
            DRS.replica_id,
            DRS.database_id,
            DRS.is_primary_replica,
            DRS.synchronization_state_desc,
            DRS.log_send_queue_size,
            DRS.log_send_rate,
            DRS.redo_queue_size,
            DRS.redo_rate,
            DRS.low_water_mark_for_ghosts,
            DRS.filestream_send_rate,
            DRS.secondary_lag_seconds,
            AG.name,
            AR.replica_server_name,
            AR.failover_mode_desc,
            ADC.database_name,
            FC.cluster_name
        FROM sys.dm_hadr_database_replica_states AS DRS
        INNER JOIN sys.availability_groups AS AG ON DRS.group_id = AG.group_id
        INNER JOIN sys.availability_replicas AS AR ON DRS.group_id = AR.group_id AND DRS.replica_id = AR.replica_id
        INNER JOIN sys.availability_databases_cluster AS ADC ON DRS.group_id = ADC.group_id 
            AND DRS.group_database_id = ADC.group_database_id
        CROSS APPLY (SELECT cluster_name FROM sys.dm_hadr_cluster) AS FC
    """.strip(),
    'columns': [
        # DRS - sys.dm_hadr_database_replica_states
        {'name': 'availability_group', 'type': 'tag'},
        {'name': 'replica_id', 'type': 'tag'},
        {'name': 'database_id', 'type': 'tag'},
        {'name': 'ao.is_primary_replica', 'type': 'gauge'},
        {'name': 'synchronization_state_desc', 'type': 'tag'},
        {'name': 'ao.log_send_queue_size', 'type': 'gauge'},
        {'name': 'ao.log_send_rate', 'type': 'gauge'},
        {'name': 'ao.redo_queue_size', 'type': 'gauge'},
        {'name': 'ao.redo_rate', 'type': 'gauge'},
        {'name': 'ao.low_water_mark_for_ghosts', 'type': 'gauge'},
        {'name': 'ao.filestream_send_rate', 'type': 'gauge'},
        {'name': 'ao.secondary_lag_seconds', 'type': 'gauge'},
        # AG - sys.availability_groups
        {'name': 'availability_group_name', 'type': 'tag'},
        # AR - sys.availability_replicas
        {'name': 'replica_server_name', 'type': 'tag'},
        {'name': 'failover_mode_desc', 'type': 'tag'},
        # ADC - sys.availability_databases_cluster
        {'name': 'database_name', 'type': 'tag'},
        # FC - sys.dm_hadr_cluster
        {'name': 'failover_cluster', 'type': 'tag'},
    ],
}
