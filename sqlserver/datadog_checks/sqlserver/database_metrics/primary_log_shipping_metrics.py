# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

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


class SqlserverPrimaryLogShippingMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_primary_log_shipping_metrics(self) -> bool:
        return self.config.database_metrics_config["primary_log_shipping_metrics"]["enabled"]

    @property
    def enabled(self):
        if not self.include_primary_log_shipping_metrics:
            return False
        return True

    @property
    def queries(self):
        return [QUERY_LOG_SHIPPING_PRIMARY]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_primary_log_shipping_metrics={self.include_primary_log_shipping_metrics})"
        )
