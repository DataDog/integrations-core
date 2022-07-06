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


def get_query_ao_availability_groups(sqlserver_major_version):
    """
    Construct the sys.availability_groups QueryExecutor configuration based on the SQL Server major version

    :params sqlserver_major_version: SQL Server major version (i.e. 2012, 2019, ...)
    :return: a QueryExecutor query config object
    """

    # AG - sys.availability_groups
    ag_column_definitions = {
        'availability_group': {
            'sql_column': 'AG.group_id AS availability_group',
            'metric_definition': {'name': 'availability_group', 'type': 'tag'},
        },
        'availability_group_name': {
            'sql_column': 'AG.name AS availability_group_name',
            'metric_definition': {'name': 'availability_group_name', 'type': 'tag'},
        },
    }

    # AR - sys.availability_replicas
    ar_column_definitions = {
        'replica_server_name': {
            'sql_column': 'AR.replica_server_name',
            'metric_definition': {'name': 'replica_server_name', 'type': 'tag'},
        },
        'failover_mode': {
            'sql_column': 'LOWER(AR.failover_mode_desc) AS failover_mode_desc',
            'metric_definition': {'name': 'failover_mode', 'type': 'tag'},
        },
        'availability_mode': {
            'sql_column': 'LOWER(AR.availability_mode_desc) AS availability_mode_desc',
            'metric_definition': {'name': 'availability_mode', 'type': 'tag'},
        },
    }

    # ADC - sys.availability_databases_cluster
    adc_column_definitions = {
        'database_name': {
            'sql_column': 'ADC.database_name',
            'metric_definition': {'name': 'database_name', 'type': 'tag'},
        },
    }

    # DRS - sys.dm_hadr_database_replica_states
    drs_column_definitions = {
        'replica_id': {
            'sql_column': 'DRS.replica_id',
            'metric_definition': {'name': 'replica_id', 'type': 'tag'},
        },
        'database_id': {
            'sql_column': 'DRS.database_id',
            'metric_definition': {'name': 'database_id', 'type': 'tag'},
        },
        'database_state': {
            'sql_column': 'DRS.database_state',
            'metric_definition': {'name': 'database_state', 'type': 'tag'},
        },
        'synchronization_state': {
            'sql_column': 'LOWER(DRS.synchronization_state_desc) AS synchronization_state_desc',
            'metric_definition': {'name': 'synchronization_state', 'type': 'tag'},
        },
        'ao_log_send_queue_size': {
            'sql_column': '(DRS.log_send_queue_size * 1024) AS log_send_queue_size',
            'metric_definition': {'name': 'ao.log_send_queue_size', 'type': 'gauge'},
        },
        'ao_log_send_rate': {
            'sql_column': '(DRS.log_send_rate * 1024) AS log_send_rate',
            'metric_definition': {'name': 'ao.log_send_rate', 'type': 'gauge'},
        },
        'ao_redo_queue_size': {
            'sql_column': '(DRS.redo_queue_size * 1024) AS redo_queue_size',
            'metric_definition': {'name': 'ao.redo_queue_size', 'type': 'gauge'},
        },
        'ao_redo_rate': {
            'sql_column': '(DRS.redo_rate * 1024) AS redo_rate',
            'metric_definition': {'name': 'ao.redo_rate', 'type': 'gauge'},
        },
        'ao_low_water_mark_for_ghosts': {
            'sql_column': 'DRS.low_water_mark_for_ghosts',
            'metric_definition': {'name': 'ao.low_water_mark_for_ghosts', 'type': 'gauge'},
        },
        'ao_filestream_send_rate': {
            'sql_column': '(DRS.filestream_send_rate * 1024) AS filestream_send_rate',
            'metric_definition': {'name': 'ao.filestream_send_rate', 'type': 'gauge'},
        },
    }

    # FC - sys.dm_hadr_cluster
    fc_column_definitions = {
        'failover_cluster': {
            'sql_column': 'FC.cluster_name',
            'metric_definition': {'name': 'failover_cluster', 'type': 'tag'},
        },
    }

    # Include metrics based on version
    if sqlserver_major_version >= 2016:
        drs_column_definitions['ao_secondary_lag_seconds'] = {
            'sql_column': 'DRS.secondary_lag_seconds',
            'metric_definition': {'name': 'ao.secondary_lag_seconds', 'type': 'gauge'},
        }
    if sqlserver_major_version >= 2014:
        drs_column_definitions['ao_is_primary_replica'] = {
            'sql_column': 'DRS.is_primary_replica',
            'metric_definition': {'name': 'ao.is_primary_replica', 'type': 'gauge'},
        }

    def _sort_column_definitions(column_definitions):
        sql_columns = []
        metric_columns = []
        for column in sorted(column_definitions.keys()):
            sql_columns.append(column_definitions[column]['sql_column'])
            metric_columns.append(column_definitions[column]['metric_definition'])
        return sql_columns, metric_columns

    # Sort columns to ensure a static column order
    ag_sql_columns, ag_metric_columns = _sort_column_definitions(ag_column_definitions)
    ar_sql_columns, ar_metric_columns = _sort_column_definitions(ar_column_definitions)
    adc_sql_columns, adc_metric_columns = _sort_column_definitions(adc_column_definitions)
    drs_sql_columns, drs_metric_columns = _sort_column_definitions(drs_column_definitions)
    fc_sql_columns, fc_metric_columns = _sort_column_definitions(fc_column_definitions)

    return {
        'name': 'sys.availability_groups',
        'query': """
        SELECT
            {ag_sql_columns},
            {ar_sql_columns},
            {adc_sql_columns},
            {drs_sql_columns},
            {fc_sql_columns}
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
    """.strip().format(
            ag_sql_columns=", ".join(ag_sql_columns),
            ar_sql_columns=", ".join(ar_sql_columns),
            adc_sql_columns=", ".join(adc_sql_columns),
            drs_sql_columns=", ".join(drs_sql_columns),
            fc_sql_columns=", ".join(fc_sql_columns),
        ),
        'columns': ag_metric_columns + ar_metric_columns + adc_metric_columns + drs_metric_columns + fc_metric_columns,
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
        sql_columns.append("fs.{}".format(column))
        metric_columns.append(column_definitions[column])

    return {
        'name': 'sys.dm_io_virtual_file_stats',
        'query': """
        SELECT
            DB_NAME(fs.database_id),
            mf.state_desc,
            mf.name,
            mf.physical_name,
            {sql_columns}
        FROM sys.dm_io_virtual_file_stats(NULL, NULL) fs
            LEFT JOIN sys.master_files mf
                ON mf.database_id = fs.database_id
                AND mf.file_id = fs.file_id;
    """.strip().format(
            sql_columns=", ".join(sql_columns)
        ),
        'columns': [
            {'name': 'db', 'type': 'tag'},
            {'name': 'state', 'type': 'tag'},
            {'name': 'logical_name', 'type': 'tag'},
            {'name': 'file_location', 'type': 'tag'},
        ]
        + metric_columns,
    }
