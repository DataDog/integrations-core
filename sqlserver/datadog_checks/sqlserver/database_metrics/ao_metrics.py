# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import List

from datadog_checks.sqlserver.utils import is_azure_database

from .base import SqlserverDatabaseMetricsBase

QUERY_AO_FAILOVER_CLUSTER = {
    "name": "sys.dm_hadr_cluster",
    "query": """
        SELECT
            LOWER(quorum_type_desc) AS quorum_type_desc,
            LOWER(quorum_state_desc) AS quorum_state_desc,
            cluster_name,
            1,
            1
        FROM sys.dm_hadr_cluster
    """.strip(),
    "columns": [
        {"name": "quorum_type", "type": "tag"},
        {"name": "quorum_state", "type": "tag"},
        {"name": "failover_cluster", "type": "tag"},
        {"name": "ao.quorum_type", "type": "gauge"},
        {"name": "ao.quorum_state", "type": "gauge"},
    ],
}

# sys.dm_hadr_cluster does not have a related column to join on, this cross join will add the
# cluster_name column to every row by multiplying all the rows in the left table against
# all the rows in the right table. Note, there will only be one row from sys.dm_hadr_cluster.
QUERY_AO_FAILOVER_CLUSTER_MEMBER = {
    "name": "sys.dm_hadr_cluster_members",
    "query": """
        SELECT
            member_name,
            LOWER(member_type_desc) AS member_type_desc,
            LOWER(member_state_desc) AS member_state_desc,
            FC.cluster_name,
            1,
            1,
            number_of_quorum_votes
        FROM sys.dm_hadr_cluster_members
        CROSS JOIN (SELECT TOP 1 cluster_name FROM sys.dm_hadr_cluster) AS FC
    """.strip(),
    "columns": [
        {"name": "member_name", "type": "tag"},
        {"name": "member_type", "type": "tag"},
        {"name": "member_state", "type": "tag"},
        {"name": "failover_cluster", "type": "tag"},
        {"name": "ao.member.type", "type": "gauge"},
        {"name": "ao.member.state", "type": "gauge"},
        {"name": "ao.member.number_of_quorum_votes", "type": "gauge"},
    ],
}


class SqlserverAoMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_ao_metrics(self) -> bool:
        return self.config.database_metrics_config["ao_metrics"]["enabled"]

    @property
    def enabled(self) -> bool:
        if not self.include_ao_metrics:
            return False
        if not self.major_version and not is_azure_database(self.engine_edition):
            return False
        if self.major_version > 2012 or is_azure_database(self.engine_edition):
            return True
        return False

    @property
    def queries(self) -> List[dict]:
        return [
            self.__get_query_ao_availability_groups(),
            QUERY_AO_FAILOVER_CLUSTER,
            QUERY_AO_FAILOVER_CLUSTER_MEMBER,
        ]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"major_version={self.major_version}, "
            f"engine_edition={self.engine_edition}, "
            f"include_ao_metrics={self.include_ao_metrics})"
        )

    def __get_query_ao_availability_groups(self) -> dict:
        """
        Construct the sys.availability_groups QueryExecutor configuration based on the SQL Server major version

        :params sqlserver_major_version: SQL Server major version (i.e. 2012, 2019, ...)
        :return: a QueryExecutor query config object
        """
        column_definitions_tags = {
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
            # FC - sys.dm_hadr_cluster
            "FC.cluster_name": {
                "name": "failover_cluster",
                "type": "tag",
            },
        }
        column_definitions_metrics = {
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
            # Other
            "1 AS replica_sync_topology_indicator": {
                "name": "ao.replica_status",
                "type": "gauge",
            },
        }

        # Include metrics based on version
        if self.major_version >= 2016:
            column_definitions_metrics["DRS.secondary_lag_seconds"] = {
                "name": "ao.secondary_lag_seconds",
                "type": "gauge",
            }
        if self.major_version >= 2014:
            column_definitions_metrics["DRS.is_primary_replica"] = {
                "name": "ao.is_primary_replica",
                "type": "gauge",
            }
            column_definitions_tags[
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
        for column in sorted(column_definitions_tags.keys()):
            sql_columns.append(column)
            metric_columns.append(column_definitions_tags[column])
        for column in sorted(column_definitions_metrics.keys()):
            sql_columns.append(column)
            metric_columns.append(column_definitions_metrics[column])

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
