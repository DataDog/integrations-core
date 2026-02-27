# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

MISSING_INDEX_METRICS_QUERY = {
    "name": "sys.dm_db_missing_index_group_stats",
    "query": """
    SELECT
        DB_NAME(mid.database_id)                                AS db,
        OBJECT_SCHEMA_NAME(mid.object_id, mid.database_id)     AS [schema],
        OBJECT_NAME(mid.object_id, mid.database_id)            AS table_name,
        ISNULL(mid.equality_columns, '')                        AS equality_columns,
        ISNULL(mid.inequality_columns, '')                      AS inequality_columns,
        ISNULL(mid.included_columns, '')                        AS included_columns,
        migs.user_seeks                                         AS user_seeks,
        migs.user_scans                                         AS user_scans,
        migs.avg_user_impact                                    AS avg_user_impact,
        migs.avg_total_user_cost                                AS avg_total_user_cost
    FROM sys.dm_db_missing_index_group_stats migs
    JOIN sys.dm_db_missing_index_groups      mig  ON migs.group_handle = mig.index_group_handle
    JOIN sys.dm_db_missing_index_details     mid  ON mig.index_handle  = mid.index_handle
    WHERE DB_NAME(mid.database_id) IS NOT NULL
    """,
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "schema", "type": "tag"},
        {"name": "table", "type": "tag"},
        {"name": "equality_columns", "type": "tag"},
        {"name": "inequality_columns", "type": "tag"},
        {"name": "included_columns", "type": "tag"},
        {"name": "missing_index.user_seeks", "type": "monotonic_count"},
        {"name": "missing_index.user_scans", "type": "monotonic_count"},
        {"name": "missing_index.avg_user_impact", "type": "gauge"},
        {"name": "missing_index.avg_total_user_cost", "type": "gauge"},
    ],
}


# https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-db-missing-index-details-transact-sql
class SqlserverMissingIndexMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_missing_index_metrics(self) -> bool:
        return self.config.database_metrics_config["missing_index_metrics"]["enabled"]

    @property
    def collection_interval(self) -> int:
        return self.config.database_metrics_config["missing_index_metrics"]["collection_interval"]

    @property
    def enabled(self) -> bool:
        return self.include_missing_index_metrics

    @property
    def queries(self) -> list[dict]:
        query = MISSING_INDEX_METRICS_QUERY.copy()
        query['collection_interval'] = self.collection_interval
        return [query]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(enabled={self.enabled}, collection_interval={self.collection_interval})"
