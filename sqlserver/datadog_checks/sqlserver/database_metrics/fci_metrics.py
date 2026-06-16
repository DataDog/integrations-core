# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.const import (
    ENGINE_EDITION_AZURE_MANAGED_INSTANCE,
)

from .base import SqlserverDatabaseMetricsBase

QUERY_FAILOVER_CLUSTER_INSTANCE = {
    "name": "sys.dm_os_cluster_nodes",
    "query": """
        SELECT
            NodeName AS node_name,
            LOWER(status_description) AS status_description,
            FC.cluster_name,
            status,
            is_current_owner
        FROM sys.dm_os_cluster_nodes
        -- `sys.dm_hadr_cluster` does not have a related column to join on. OUTER APPLY attaches the
        -- `cluster_name` column to every row from `sys.dm_os_cluster_nodes`, preserving those rows
        -- even when `sys.dm_hadr_cluster` returns no rows (e.g. when Always On is not enabled, in
        -- which case `cluster_name` is NULL). Note, there will only be at most one row from
        -- `sys.dm_hadr_cluster`.
        OUTER APPLY (SELECT TOP 1 cluster_name FROM sys.dm_hadr_cluster) AS FC
    """.strip(),
    "columns": [
        {"name": "node_name", "type": "tag"},
        {"name": "status", "type": "tag"},
        {"name": "failover_cluster", "type": "tag_not_null"},
        {"name": "fci.status", "type": "gauge"},
        {"name": "fci.is_current_owner", "type": "gauge"},
    ],
}


class SqlserverFciMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_fci_metrics(self) -> bool:
        return self.config.database_metrics_config["fci_metrics"]["enabled"]

    @property
    def enabled(self):
        if not self.include_fci_metrics:
            return False
        if self.engine_edition == ENGINE_EDITION_AZURE_MANAGED_INSTANCE:
            return True
        if self.major_version > 11:
            return True
        return False

    @property
    def queries(self):
        return [QUERY_FAILOVER_CLUSTER_INSTANCE]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"major_version={self.major_version}, "
            f"engine_edition={self.engine_edition}, "
            f"include_fci_metrics={self.include_fci_metrics})"
        )
