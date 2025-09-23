# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.const import (
    ENGINE_EDITION_AZURE_MANAGED_INSTANCE,
)
from datadog_checks.sqlserver.utils import is_azure_database

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
        -- `sys.dm_hadr_cluster` does not have a related column to join on, this cross join will add the
        -- `cluster_name` column to every row by multiplying all the rows in the left table against
        -- all the rows in the right table. Note, there will only be one row from `sys.dm_hadr_cluster`.
        CROSS JOIN (SELECT TOP 1 cluster_name FROM sys.dm_hadr_cluster) AS FC
    """.strip(),
    "columns": [
        {"name": "node_name", "type": "tag"},
        {"name": "status", "type": "tag"},
        {"name": "failover_cluster", "type": "tag"},
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
        if not self.major_version and not is_azure_database(self.engine_edition):
            return False
        if self.major_version > 2012 or self.engine_edition == ENGINE_EDITION_AZURE_MANAGED_INSTANCE:
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
