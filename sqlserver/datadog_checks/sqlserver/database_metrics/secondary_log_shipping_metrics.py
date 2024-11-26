# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

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


class SqlserverSecondaryLogShippingMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_secondary_log_shipping_metrics(self) -> bool:
        return self.config.database_metrics_config['secondary_log_shipping_metrics']['enabled']

    @property
    def enabled(self):
        if not self.include_secondary_log_shipping_metrics:
            return False
        return True

    @property
    def queries(self):
        return [QUERY_LOG_SHIPPING_SECONDARY]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(enabled={self.enabled}, "
            f"include_secondary_log_shipping_metrics={self.include_secondary_log_shipping_metrics})"
        )
