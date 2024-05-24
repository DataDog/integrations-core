# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.const import ENGINE_EDITION_SQL_DATABASE
from datadog_checks.sqlserver.utils import is_azure_database

QUERY_SERVER_STATIC_INFO = {
    "name": "sys.dm_os_sys_info",
    "query": """
        SELECT (os.ms_ticks/1000) AS [Server Uptime]
        ,os.cpu_count AS [CPU Count]
        ,(os.physical_memory_kb*1024) AS [Physical Memory Bytes]
        ,os.virtual_memory_kb AS [Virtual Memory Bytes]
        ,(os.committed_kb*1024) AS [Total Server Memory Bytes]
        ,(os.committed_target_kb*1024) AS [Target Server Memory Bytes]
      FROM sys.dm_os_sys_info os""".strip(),
    "columns": [
        {"name": "server.uptime", "type": "gauge"},
        {"name": "server.cpu_count", "type": "gauge"},
        {"name": "server.physical_memory", "type": "gauge"},
        {"name": "server.virtual_memory", "type": "gauge"},
        {"name": "server.committed_memory", "type": "gauge"},
        {"name": "server.target_memory", "type": "gauge"},
    ],
}

QUERY_AO_FAILOVER_CLUSTER = {
    "name": "sys.dm_hadr_cluster",
    "query": """
        SELECT
            1,
            LOWER(quorum_type_desc) AS quorum_type_desc,
            1,
            LOWER(quorum_state_desc) AS quorum_state_desc,
            cluster_name
        FROM sys.dm_hadr_cluster
    """.strip(),
    "columns": [
        {"name": "ao.quorum_type", "type": "gauge"},
        {"name": "quorum_type", "type": "tag"},
        {"name": "ao.quorum_state", "type": "gauge"},
        {"name": "quorum_state", "type": "tag"},
        {"name": "failover_cluster", "type": "tag"},
    ],
}

QUERY_AO_FAILOVER_CLUSTER_MEMBER = {
    "name": "sys.dm_hadr_cluster_members",
    "query": """
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
    "columns": [
        {"name": "member_name", "type": "tag"},
        {"name": "ao.member.type", "type": "gauge"},
        {"name": "member_type", "type": "tag"},
        {"name": "ao.member.state", "type": "gauge"},
        {"name": "member_state", "type": "tag"},
        {"name": "ao.member.number_of_quorum_votes", "type": "gauge"},
        {"name": "failover_cluster", "type": "tag"},
    ],
}

QUERY_FAILOVER_CLUSTER_INSTANCE = {
    "name": "sys.dm_os_cluster_nodes",
    "query": """
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
    "columns": [
        {"name": "node_name", "type": "tag"},
        {"name": "fci.status", "type": "gauge"},
        {"name": "status", "type": "tag"},
        {"name": "fci.is_current_owner", "type": "gauge"},
        {"name": "failover_cluster", "type": "tag"},
    ],
}

QUERY_LOG_SHIPPING_PRIMARY = {
    "name": "msdb.dbo.log_shipping_monitor_primary",
    "query": """
        SELECT primary_id
            ,primary_server
            ,primary_database
            ,DATEDIFF(SECOND, last_backup_date, GETDATE()) AS time_since_backup
            ,backup_threshold*60 as backup_threshold
        FROM msdb.dbo.log_shipping_monitor_primary
    """.strip(),
    "columns": [
        {"name": "primary_id", "type": "tag"},
        {"name": "primary_server", "type": "tag"},
        {"name": "primary_db", "type": "tag"},
        {"name": "log_shipping_primary.time_since_backup", "type": "gauge"},
        {"name": "log_shipping_primary.backup_threshold", "type": "gauge"},
    ],
}

QUERY_LOG_SHIPPING_SECONDARY = {
    "name": "msdb.dbo.log_shipping_monitor_secondary",
    "query": """
        SELECT secondary_server
            ,secondary_database
            ,secondary_id
            ,primary_server
            ,primary_database
            ,DATEDIFF(SECOND, last_restored_date, GETDATE()) AS time_since_restore
            ,DATEDIFF(SECOND, last_copied_date, GETDATE()) AS time_since_copy
            ,last_restored_latency*60 as last_restored_latency
            ,restore_threshold*60 as restore_threshold
        FROM msdb.dbo.log_shipping_monitor_secondary
    """.strip(),
    "columns": [
        {"name": "secondary_server", "type": "tag"},
        {"name": "secondary_db", "type": "tag"},
        {"name": "secondary_id", "type": "tag"},
        {"name": "primary_server", "type": "tag"},
        {"name": "primary_db", "type": "tag"},
        {"name": "log_shipping_secondary.time_since_restore", "type": "gauge"},
        {"name": "log_shipping_secondary.time_since_copy", "type": "gauge"},
        {"name": "log_shipping_secondary.last_restored_latency", "type": "gauge"},
        {"name": "log_shipping_secondary.restore_threshold", "type": "gauge"},
    ],
}


def get_query_ao_availability_groups(sqlserver_major_version):
    """
    Construct the sys.availability_groups QueryExecutor configuration based on the SQL Server major version

    :params sqlserver_major_version: SQL Server major version (i.e. 2012, 2019, ...)
    :return: a QueryExecutor query config object
    """
    column_definitions = {
        # AG - sys.availability_groups
        "AG.group_id AS availability_group": {
            "name": "availability_group",
            "type": "tag",
        },
        "AG.name AS availability_group_name": {
            "name": "availability_group_name",
            "type": "tag",
        },
        # AR - sys.availability_replicas
        "AR.replica_server_name": {"name": "replica_server_name", "type": "tag"},
        "LOWER(AR.failover_mode_desc) AS failover_mode_desc": {
            "name": "failover_mode",
            "type": "tag",
        },
        "LOWER(AR.availability_mode_desc) AS availability_mode_desc": {
            "name": "availability_mode",
            "type": "tag",
        },
        # ADC - sys.availability_databases_cluster
        "ADC.database_name": {"name": "database_name", "type": "tag"},
        # DRS - sys.dm_hadr_database_replica_states
        "DRS.replica_id": {"name": "replica_id", "type": "tag"},
        "DRS.database_id": {"name": "database_id", "type": "tag"},
        "LOWER(DRS.database_state_desc) AS database_state_desc": {
            "name": "database_state",
            "type": "tag",
        },
        "LOWER(DRS.synchronization_state_desc) AS synchronization_state_desc": {
            "name": "synchronization_state",
            "type": "tag",
        },
        "(DRS.log_send_queue_size * 1024) AS log_send_queue_size": {
            "name": "ao.log_send_queue_size",
            "type": "gauge",
        },
        "(DRS.log_send_rate * 1024) AS log_send_rate": {
            "name": "ao.log_send_rate",
            "type": "gauge",
        },
        "(DRS.redo_queue_size * 1024) AS redo_queue_size": {
            "name": "ao.redo_queue_size",
            "type": "gauge",
        },
        "(DRS.redo_rate * 1024) AS redo_rate": {
            "name": "ao.redo_rate",
            "type": "gauge",
        },
        "DRS.low_water_mark_for_ghosts": {
            "name": "ao.low_water_mark_for_ghosts",
            "type": "gauge",
        },
        "(DRS.filestream_send_rate * 1024) AS filestream_send_rate": {
            "name": "ao.filestream_send_rate",
            "type": "gauge",
        },
        # FC - sys.dm_hadr_cluster
        "FC.cluster_name": {
            "name": "failover_cluster",
            "type": "tag",
        },
        # Other
        "1 AS replica_sync_topology_indicator": {
            "name": "ao.replica_status",
            "type": "gauge",
        },
    }

    # Include metrics based on version
    if sqlserver_major_version >= 2016:
        column_definitions["DRS.secondary_lag_seconds"] = {
            "name": "ao.secondary_lag_seconds",
            "type": "gauge",
        }
    if sqlserver_major_version >= 2014:
        column_definitions["DRS.is_primary_replica"] = {
            "name": "ao.is_primary_replica",
            "type": "gauge",
        }
        column_definitions[
            """
        CASE
            WHEN DRS.is_primary_replica = 1 THEN 'primary'
            WHEN DRS.is_primary_replica = 0 THEN 'secondary'
        END AS replica_role_desc
        """
        ] = {"name": "replica_role", "type": "tag"}

    # Sort columns to ensure a static column order
    sql_columns = []
    metric_columns = []
    for column in sorted(column_definitions.keys()):
        sql_columns.append(column)
        metric_columns.append(column_definitions[column])

    return {
        "name": "sys.availability_groups",
        "query": """
        SELECT
            {sql_columns}
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
            sql_columns=", ".join(sql_columns),
        ),
        "columns": metric_columns,
    }


def get_query_file_stats(sqlserver_major_version, sqlserver_engine_edition):
    """
    Construct the dm_io_virtual_file_stats QueryExecutor configuration based on the SQL Server major version

    :param sqlserver_engine_edition: The engine version (i.e. 5 for Azure SQL DB...)
    :param sqlserver_major_version: SQL Server major version (i.e. 2012, 2019, ...)
    :return: a QueryExecutor query config object
    """

    column_definitions = {
        "size_on_disk_bytes": {"name": "files.size_on_disk", "type": "gauge"},
        "num_of_reads": {"name": "files.reads", "type": "monotonic_count"},
        "num_of_bytes_read": {"name": "files.read_bytes", "type": "monotonic_count"},
        "io_stall_read_ms": {"name": "files.read_io_stall", "type": "monotonic_count"},
        "io_stall_queued_read_ms": {
            "name": "files.read_io_stall_queued",
            "type": "monotonic_count",
        },
        "num_of_writes": {"name": "files.writes", "type": "monotonic_count"},
        "num_of_bytes_written": {
            "name": "files.written_bytes",
            "type": "monotonic_count",
        },
        "io_stall_write_ms": {
            "name": "files.write_io_stall",
            "type": "monotonic_count",
        },
        "io_stall_queued_write_ms": {
            "name": "files.write_io_stall_queued",
            "type": "monotonic_count",
        },
        "io_stall": {"name": "files.io_stall", "type": "monotonic_count"},
    }

    if sqlserver_major_version <= 2012 and not is_azure_database(sqlserver_engine_edition):
        column_definitions.pop("io_stall_queued_read_ms")
        column_definitions.pop("io_stall_queued_write_ms")

    # sort columns to ensure a static column order
    sql_columns = []
    metric_columns = []
    for column in sorted(column_definitions.keys()):
        sql_columns.append("fs.{}".format(column))
        metric_columns.append(column_definitions[column])

    query_filter = ""
    if sqlserver_major_version == 2022:
        query_filter = "WHERE DB_NAME(fs.database_id) not like 'model_%'"

    query = """
    SELECT
        DB_NAME(fs.database_id),
        mf.state_desc,
        mf.name,
        mf.physical_name,
        {sql_columns}
    FROM sys.dm_io_virtual_file_stats(NULL, NULL) fs
        LEFT JOIN sys.master_files mf
            ON mf.database_id = fs.database_id
            AND mf.file_id = fs.file_id {filter};
    """

    if sqlserver_engine_edition == ENGINE_EDITION_SQL_DATABASE:
        # Azure SQL DB does not have access to the sys.master_files view
        query = """
        SELECT
            DB_NAME(DB_ID()),
            df.state_desc,
            df.name,
            df.physical_name,
            {sql_columns}
        FROM sys.dm_io_virtual_file_stats(DB_ID(), NULL) fs
            LEFT JOIN sys.database_files df
                ON df.file_id = fs.file_id;
        """

    return {
        "name": "sys.dm_io_virtual_file_stats",
        "query": query.strip().format(sql_columns=", ".join(sql_columns), filter=query_filter),
        "columns": [
            {"name": "db", "type": "tag"},
            {"name": "state", "type": "tag"},
            {"name": "logical_name", "type": "tag"},
            {"name": "file_location", "type": "tag"},
        ]
        + metric_columns,
    }
