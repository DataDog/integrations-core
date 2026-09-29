# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import functools

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.sqlserver.const import SQLSERVER_PARAMETER_LIMIT

from .base import SqlserverDatabaseMetricsBase

TABLE_SIZE_STATS_QUERY = {
    "name": "sys.dm_db_partition_stats",
    "query": """
    SELECT
        t.name AS table_name,
        s.name AS schema_name,
        db_name() AS database_name,
        SUM(
            CASE
                WHEN p.index_id IN (0, 1) THEN p.row_count
                ELSE 0
            END
        ) AS row_count,
        CAST(SUM(a.total_pages) * 8.0 AS DECIMAL(18,2)) AS total_size,
        CAST(SUM(a.used_pages) * 8.0 AS DECIMAL(18,2)) AS used_size,
        CAST(SUM(a.data_pages) * 8.0 AS DECIMAL(18,2)) AS data_size
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
""",
    "columns": [
        {"name": "table", "type": "tag"},
        {"name": "schema", "type": "tag"},
        {"name": "database", "type": "tag"},
        {"name": "table.row_count", "type": "gauge"},
        {"name": "table.total_size", "type": "gauge"},
        {"name": "table.used_size", "type": "gauge"},
        {"name": "table.data_size", "type": "gauge"},
    ],
}


# https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-db-index-usage-stats-transact-sql?view=sql-server-ver15
class SqlserverTableSizeMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_table_size_metrics(self) -> bool:
        return self.config.database_metrics_config["table_size_metrics"]["enabled"]

    @property
    def collection_interval(self) -> int:
        '''
        Returns the interval in seconds at which to collect table size metrics.
        Note: The table size metrics query can be expensive, so it is recommended to set a higher interval.
        '''
        return self.config.database_metrics_config["table_size_metrics"]["collection_interval"]

    @property
    def table_size_table_names(self) -> list[str]:
        return self.config.table_size_table_names

    @property
    def databases(self):
        '''
        Returns a list of databases to collect table size metrics for.
        tempdb is excluded.
        '''
        if not self._databases:
            raise ConfigurationError("No databases configured for table size metrics")
        if 'tempdb' in self._databases:
            self._databases.remove('tempdb')
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
        return f"{self.__class__.__name__}(enabled={self.enabled}, collection_interval={self.collection_interval})"

    def _build_query_executors(self):
        executors = []
        if self.table_size_table_names:
            table_name_batches = [
                self.table_size_table_names[start : start + SQLSERVER_PARAMETER_LIMIT]
                for start in range(0, len(self.table_size_table_names), SQLSERVER_PARAMETER_LIMIT)
            ]
        else:
            table_name_batches = [None]
        for database in self.databases:
            queries = []
            for table_names in table_name_batches:
                batch_queries = copy.deepcopy(self.queries)
                if table_names:
                    placeholders = ','.join(['?'] * len(table_names))
                    table_name_filter = f" WHERE t.name IN ({placeholders})"
                    for query in batch_queries:
                        query['query'] = query['query'].replace("    GROUP BY", table_name_filter + "\n    GROUP BY")
                        query['params'] = tuple(table_names)
                queries.extend(batch_queries)
            executor = self.new_query_executor(
                queries,
                executor=functools.partial(self.execute_query_handler, db=database),
                track_operation_time=self.track_operation_time,
                operation_tags=['database:{}'.format(database)],
            )
            executor.compile_queries()
            executors.append(executor)
        return executors
