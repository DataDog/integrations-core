# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

QUERY_SERVER_STATIC_INFO = {
    'name': 'sys.dm_os_sys_info',
    'query': """
        SELECT (os.ms_ticks/1000) AS [Server Uptime]
        ,os.cpu_count AS [CPU Count]
        ,(os.physical_memory_kb*1024) AS [Physical Memory Bytes]
        ,os.virtual_memory_kb AS [Virtual Memory Bytes]
        ,(os.committed_kb*1024) AS [Total Server Memory Bytes]
        ,(os.committed_target_kb*1024) AS [Target Server Memory Bytes]
      FROM sys.dm_os_sys_info os""".strip(),
    'columns': [
        {'name': 'server.uptime', 'type': 'gauge'},
        {'name': 'server.cpu_count', 'type': 'gauge'},
        {'name': 'server.physical_memory', 'type': 'gauge'},
        {'name': 'server.virtual_memory', 'type': 'gauge'},
        {'name': 'server.committed_memory', 'type': 'gauge'},
        {'name': 'server.target_memory', 'type': 'gauge'},
    ],
}

QUERY_AO_FAILOVER_CLUSTER = {
    'name': 'sys.dm_hadr_cluster',
    'query': """
        SELECT
            1,
            LOWER(quorum_type_desc) AS quorum_type_desc,
            1,
            LOWER(quorum_state_desc) AS quorum_state_desc,
            cluster_name
        FROM sys.dm_hadr_cluster
    """.strip(),
    'columns': [
        {'name': 'ao.quorum_type', 'type': 'gauge'},
        {'name': 'quorum_type', 'type': 'tag'},
        {'name': 'ao.quorum_state', 'type': 'gauge'},
        {'name': 'quorum_state', 'type': 'tag'},
        {'name': 'failover_cluster', 'type': 'tag'},
    ],
}

QUERY_AO_FAILOVER_CLUSTER_MEMBER = {
    'name': 'sys.dm_hadr_cluster_members',
    'query': """
        SELECT
            member_name,
            1,
            LOWER(member_type_desc) AS member_type_desc,
            1,
            LOWER(member_state_desc) AS member_state_desc,
            number_of_quorum_votes,
            FC.cluster_name
        FROM sys.dm_hadr_cluster_members
        -- `sys.dm_hadr_cluster` does not have a related column to join on, this cross join will add the
        -- `cluster_name` column to every row by multiplying all the rows in the left table against
        -- all the rows in the right table. Note, there will only be one row from `sys.dm_hadr_cluster`.
        CROSS JOIN (SELECT TOP 1 cluster_name FROM sys.dm_hadr_cluster) AS FC
    """.strip(),
    'columns': [
        {'name': 'member_name', 'type': 'tag'},
        {'name': 'ao.member.type', 'type': 'gauge'},
        {'name': 'member_type', 'type': 'tag'},
        {'name': 'ao.member.state', 'type': 'gauge'},
        {'name': 'member_state', 'type': 'tag'},
        {'name': 'ao.member.number_of_quorum_votes', 'type': 'gauge'},
        {'name': 'failover_cluster', 'type': 'tag'},
    ],
}

QUERY_AO_AVAILABILITY_GROUPS = {
    'name': 'sys.availability_groups',
    'query': """
        SELECT
            AG.group_id AS availability_group,
            AG.name AS availability_group_name,
            AR.replica_server_name,
            LOWER(AR.failover_mode_desc) AS failover_mode_desc,
            LOWER(AR.availability_mode_desc) AS failover_mode_desc,
            ADC.database_name,
            DRS.replica_id,
            DRS.database_id,
            DRS.is_primary_replica,
            DRS.database_state,
            LOWER(DRS.synchronization_state_desc) AS synchronization_state_desc,
            (DRS.log_send_queue_size * 1024) AS log_send_queue_size,
            (DRS.log_send_rate * 1024) AS log_send_rate,
            (DRS.redo_queue_size * 1024) AS redo_queue_size,
            (DRS.redo_rate * 1024) AS redo_rate,
            DRS.low_water_mark_for_ghosts,
            (DRS.filestream_send_rate * 1024) AS filestream_send_rate,
            DRS.secondary_lag_seconds,
            FC.cluster_name
        FROM
            sys.availability_groups AS AG
            INNER JOIN sys.availability_replicas AS AR ON AG.group_id = AR.group_id
            INNER JOIN sys.availability_databases_cluster AS ADC ON AG.group_id = ADC.group_id
            INNER JOIN sys.dm_hadr_database_replica_states AS DRS ON AG.group_id = DRS.group_id
                AND ADC.group_database_id = DRS.group_database_id
                AND AR.replica_id = DRS.replica_id
            -- `sys.dm_hadr_cluster` does not have a related column to join on, this cross join will add the
            -- `cluster_name` column to every row by multiplying all the rows in the left table against
            -- all the rows in the right table. Note, there will only be one row from `sys.dm_hadr_cluster`.
            CROSS JOIN (SELECT TOP 1 cluster_name FROM sys.dm_hadr_cluster) AS FC
    """.strip(),
    'columns': [
        # AG - sys.availability_groups
        {'name': 'availability_group', 'type': 'tag'},
        {'name': 'availability_group_name', 'type': 'tag'},
        # AR - sys.availability_replicas
        {'name': 'replica_server_name', 'type': 'tag'},
        {'name': 'failover_mode', 'type': 'tag'},
        {'name': 'availability_mode', 'type': 'tag'},
        # ADC - sys.availability_databases_cluster
        {'name': 'database_name', 'type': 'tag'},
        # DRS - sys.dm_hadr_database_replica_states
        {'name': 'replica_id', 'type': 'tag'},
        {'name': 'database_id', 'type': 'tag'},
        {'name': 'ao.is_primary_replica', 'type': 'gauge'},
        {'name': 'database_state', 'type': 'tag'},
        {'name': 'synchronization_state', 'type': 'tag'},
        {'name': 'ao.log_send_queue_size', 'type': 'gauge'},
        {'name': 'ao.log_send_rate', 'type': 'gauge'},
        {'name': 'ao.redo_queue_size', 'type': 'gauge'},
        {'name': 'ao.redo_rate', 'type': 'gauge'},
        {'name': 'ao.low_water_mark_for_ghosts', 'type': 'gauge'},
        {'name': 'ao.filestream_send_rate', 'type': 'gauge'},
        {'name': 'ao.secondary_lag_seconds', 'type': 'gauge'},
        # FC - sys.dm_hadr_cluster
        {'name': 'failover_cluster', 'type': 'tag'},
    ],
}

QUERY_FAILOVER_CLUSTER_INSTANCE = {
    'name': 'sys.dm_os_cluster_nodes',
    'query': """
        SELECT
            NodeName AS node_name,
            status,
            LOWER(status_description) AS status_description,
            is_current_owner,
            FC.cluster_name
        FROM sys.dm_os_cluster_nodes
        -- `sys.dm_hadr_cluster` does not have a related column to join on, this cross join will add the
        -- `cluster_name` column to every row by multiplying all the rows in the left table against
        -- all the rows in the right table. Note, there will only be one row from `sys.dm_hadr_cluster`.
        CROSS JOIN (SELECT TOP 1 cluster_name FROM sys.dm_hadr_cluster) AS FC
    """.strip(),
    'columns': [
        {'name': 'node_name', 'type': 'tag'},
        {'name': 'fci.status', 'type': 'gauge'},
        {'name': 'status', 'type': 'tag'},
        {'name': 'fci.is_current_owner', 'type': 'gauge'},
        {'name': 'failover_cluster', 'type': 'tag'},
    ],
}


def get_query_file_stats(sqlserver_major_version):
    """
    Construct the dm_io_virtual_file_stats QueryExecutor configuration based on the SQL Server major version

    :param sqlserver_major_version: SQL Server major version (i.e. 2012, 2019, ...)
    :return: a QueryExecutor query config object
    """

    column_definitions = {
        'size_on_disk_bytes': {'name': 'files.size_on_disk', 'type': 'gauge'},
        'num_of_reads': {'name': 'files.reads', 'type': 'monotonic_count'},
        'num_of_bytes_read': {'name': 'files.read_bytes', 'type': 'monotonic_count'},
        'io_stall_read_ms': {'name': 'files.read_io_stall', 'type': 'monotonic_count'},
        'io_stall_queued_read_ms': {'name': 'files.read_io_stall_queued', 'type': 'monotonic_count'},
        'num_of_writes': {'name': 'files.writes', 'type': 'monotonic_count'},
        'num_of_bytes_written': {'name': 'files.written_bytes', 'type': 'monotonic_count'},
        'io_stall_write_ms': {'name': 'files.write_io_stall', 'type': 'monotonic_count'},
        'io_stall_queued_write_ms': {'name': 'files.write_io_stall_queued', 'type': 'monotonic_count'},
        'io_stall': {'name': 'files.io_stall', 'type': 'monotonic_count'},
    }

    if sqlserver_major_version <= 2012:
        column_definitions.pop("io_stall_queued_read_ms")
        column_definitions.pop("io_stall_queued_write_ms")

    # sort columns to ensure a static column order
    sql_columns = []
    metric_columns = []
    for column in sorted(column_definitions.keys()):
        sql_columns.append("fs.{} AS {}".format(column, column))
        metric_columns.append(column_definitions[column])

    return {
        'name': 'sys.dm_io_virtual_file_stats',
        'query': """
        SELECT
            DB_NAME(fs.database_id) AS database_name,
            mf.state_desc AS state_desc,
            mf.name AS logical_name,
            mf.physical_name AS physical_name,
            {columns}
        FROM sys.dm_io_virtual_file_stats(NULL, NULL) fs
            LEFT JOIN sys.master_files mf
                ON mf.database_id = fs.database_id
                AND mf.file_id = fs.file_id;
    """.strip().format(
            columns=", ".join(sql_columns)
        ),
        'columns': [
            {'name': 'db', 'type': 'tag'},
            {'name': 'state', 'type': 'tag'},
            {'name': 'logical_name', 'type': 'tag'},
            {'name': 'file_location', 'type': 'tag'},
        ]
        + metric_columns,
    }
