# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from .base import SqlserverDatabaseMetricsBase

DATABASE_STATS_METRICS_QUERY = {
    "name": "sys.databases",
    "query": """SELECT
        name as db,
        name as database_name,
        state_desc,
        recovery_model_desc,
        state,
        is_sync_with_backup,
        is_in_standby,
        is_read_only
        from sys.databases
    """,
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "database", "type": "tag"},
        {"name": "database_state_desc", "type": "tag"},
        {"name": "database_recovery_model_desc", "type": "tag"},
        {"name": "database.state", "type": "gauge"},
        {"name": "database.is_sync_with_backup", "type": "gauge"},
        {"name": "database.is_in_standby", "type": "gauge"},
        {"name": "database.is_read_only", "type": "gauge"},
    ],
}


class SqlserverDatabaseStatsMetrics(SqlserverDatabaseMetricsBase):
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-databases-transact-sql?view=sql-server-ver15
    @property
    def include_database_stats_metrics(self) -> bool:
        return self.config.database_metrics_config["db_stats_metrics"]["enabled"]

    @property
    def enabled(self):
        if not self.include_database_stats_metrics:
            return False
        return True

    @property
    def queries(self):
        return [DATABASE_STATS_METRICS_QUERY]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_database_stats_metrics={self.include_database_stats_metrics})"
        )
