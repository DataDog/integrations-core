# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import functools

from datadog_checks.base.errors import ConfigurationError

from .base import SqlserverDatabaseMetricsBase

TABLE_SIZE_STATS_QUERY = {
    "name": "sys.dm_db_partition_stats",
    "query": """
    SELECT 
    t.name AS table,
    s.name AS schema,
    SUM(p.row_count) AS row_count,
    CAST(SUM(a.total_pages) * 8.0 / 1024 AS DECIMAL(18,2)) AS total_size_mb,
    CAST(SUM(a.used_pages) * 8.0 / 1024 AS DECIMAL(18,2)) AS used_size_mb,
    CAST(SUM(a.data_pages) * 8.0 / 1024 AS DECIMAL(18,2)) AS data_size_mb
FROM 
    sys.tables t
INNER JOIN 
    sys.schemas s ON t.schema_id = s.schema_id
INNER JOIN 
    sys.indexes i ON t.object_id = i.object_id
INNER JOIN 
    sys.dm_db_partition_stats p ON i.object_id = p.object_id AND i.index_id = p.index_id
INNER JOIN 
    sys.allocation_units a ON p.partition_id = a.container_id
GROUP BY 
    t.name, s.name
ORDER BY 
    total_size_mb DESC;


""",
    "columns": [
        {"name": "table", "type": "tag"},
        {"name": "schema", "type": "tag"},
        {"name": "row_count", "type": "gauge"},
        {"name": "total_size_mb", "type": "gauge"},
        {"name": "used_size_mb", "type": "gauge"},
        {"name": "data_size_mb", "type": "gauge"},
    ],
}


# https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-db-index-usage-stats-transact-sql?view=sql-server-ver15
class SqlserverTableSizeMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_table_size_metrics(self) -> bool:
        return self.config.database_metrics_config["table_size_metrics"]["enabled"]

    @property
    def include_table_size_metrics_tempdb(self) -> bool:
        return self.config.database_metrics_config["table_size_metrics"]["enabled_tempdb"]

    @property
    def collection_interval(self) -> int:
        '''
        Returns the interval in seconds at which to collect table size metrics.
        Note: The table size metrics query can be expensive, so it is recommended to set a higher interval.
        '''
        return self.config.database_metrics_config["table_size_metrics"]["collection_interval"]

    @property
    def databases(self):
        '''
        Returns a list of databases to collect table size metrics for.
        By default, tempdb is excluded.
        '''
        if not self._databases:
            raise ConfigurationError("No databases configured for table size metrics")
        if not self.include_table_size_metrics_tempdb:
            try:
                self._databases.remove('tempdb')
            except ValueError:
                pass
        return self._databases

    @property
    def enabled(self):
        if not self.include_table_size_metrics:
            return False
        return True

    @property
    def queries(self):
        # make a copy of the query to avoid modifying the original
        # in case different instances have different collection intervals
        query = TABLE_SIZE_STATS_QUERY.copy()
        query['collection_interval'] = self.collection_interval
        return [query]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_table_size_metrics={self.include_table_size_metrics}), "
            f"include_table_size_metrics_tempdb={self.include_table_size_metrics_tempdb}, "
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
