# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import functools

from datadog_checks.base.errors import ConfigurationError

from .base import SqlserverDatabaseMetricsBase

INDEX_USAGE_STATS_QUERY = {
    "name": "sys.dm_db_index_usage_stats",
    "query": """
    SELECT
         DB_NAME(ixus.database_id) as db,
         CASE
            WHEN ind.name IS NULL THEN 'HeapIndex_' + OBJECT_NAME(ind.object_id)
            ELSE ind.name
         END AS index_name,
         OBJECT_SCHEMA_NAME(ind.object_id, ixus.database_id) as "schema",
         OBJECT_NAME(ind.object_id) as table_name,
        user_seeks,
        user_scans,
        user_lookups,
        user_updates
    FROM sys.indexes ind
             INNER JOIN sys.dm_db_index_usage_stats ixus
             ON ixus.index_id = ind.index_id AND ixus.object_id = ind.object_id
    WHERE OBJECTPROPERTY(ind.object_id, 'IsUserTable') = 1 AND DB_NAME(ixus.database_id) = db_name()
    GROUP BY ixus.database_id, ind.object_id, ind.name, user_seeks, user_scans, user_lookups, user_updates
""",
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "index_name", "type": "tag"},
        {"name": "schema", "type": "tag"},
        {"name": "table", "type": "tag"},
        {"name": "index.user_seeks", "type": "monotonic_count"},
        {"name": "index.user_scans", "type": "monotonic_count"},
        {"name": "index.user_lookups", "type": "monotonic_count"},
        {"name": "index.user_updates", "type": "monotonic_count"},
    ],
}


# https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-db-index-usage-stats-transact-sql?view=sql-server-ver15
class SqlserverIndexUsageMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_index_usage_metrics(self) -> bool:
        return self.config.database_metrics_config["index_usage_metrics"]["enabled"]

    @property
    def include_index_usage_metrics_tempdb(self) -> bool:
        return self.config.database_metrics_config["index_usage_metrics"]["enabled_tempdb"]

    @property
    def collection_interval(self) -> int:
        '''
        Returns the interval in seconds at which to collect index usage metrics.
        Note: The index usage metrics query can be expensive, so it is recommended to set a higher interval.
        '''
        return self.config.database_metrics_config["index_usage_metrics"]["collection_interval"]

    @property
    def databases(self):
        '''
        Returns a list of databases to collect index usage metrics for.
        By default, tempdb is excluded.
        '''
        if not self._databases:
            raise ConfigurationError("No databases configured for index usage metrics")
        if not self.include_index_usage_metrics_tempdb:
            try:
                self._databases.remove('tempdb')
            except ValueError:
                pass
        return self._databases

    @property
    def enabled(self):
        if not self.include_index_usage_metrics:
            return False
        return True

    @property
    def queries(self):
        # make a copy of the query to avoid modifying the original
        # in case different instances have different collection intervals
        query = INDEX_USAGE_STATS_QUERY.copy()
        query['collection_interval'] = self.collection_interval
        return [query]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_index_usage_metrics={self.include_index_usage_metrics}), "
            f"include_index_usage_metrics_tempdb={self.include_index_usage_metrics_tempdb}, "
            f"collection_interval={self.collection_interval})"
        )

    def _build_query_executors(self):
        executors = []
        for database in self.databases:
            executor = self.new_query_executor(
                self.queries,
                executor=functools.partial(self.execute_query_handler, db=database),
                track_operation_time=self.track_operation_time,
            )
            executor.compile_queries()
            executors.append(executor)
        return executors
