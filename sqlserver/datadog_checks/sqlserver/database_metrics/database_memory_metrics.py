# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

DATABASE_MEMORY_METRICS_QUERY = """
    SELECT
        DB_NAME(database_id) as database_name,
        database_id,
        COUNT(*) as page_count,
        COUNT(*) * 8 / 1024.0 as buffer_pool_size_mb,
        SUM(CAST(is_modified AS INT)) as dirty_page_count,
        SUM(CAST(is_modified AS INT)) * 8 / 1024.0 as dirty_pages_mb,
        (COUNT(*) - SUM(CAST(is_modified AS INT))) as clean_page_count,
        (COUNT(*) - SUM(CAST(is_modified AS INT))) * 8 / 1024.0 as clean_pages_mb,
        SUM(CASE WHEN page_type = 1 THEN 1 ELSE 0 END) as data_page_count,
        SUM(CASE WHEN page_type = 2 THEN 1 ELSE 0 END) as index_page_count,
        SUM(CASE WHEN page_type = 3 THEN 1 ELSE 0 END) as text_page_count,
        SUM(CASE WHEN page_type IN (4, 5, 6, 7, 8, 9, 10) THEN 1 ELSE 0 END) as other_page_count
    FROM sys.dm_os_buffer_descriptors
    WHERE database_id != 32767  -- Exclude Resource Database
    GROUP BY database_id
"""

DATABASE_MEMORY_METRICS_QUERY_MAPPING = {
    "name": "database_memory_metrics",
    "query": DATABASE_MEMORY_METRICS_QUERY,
    "columns": [
        {"name": "database_name", "type": "tag"},
        {"name": "database_id", "type": "tag"},
        {"name": "database.buffer_pool.page_count", "type": "gauge"},
        {"name": "database.buffer_pool.size", "type": "gauge"},
        {"name": "database.buffer_pool.dirty_page_count", "type": "gauge"},
        {"name": "database.buffer_pool.dirty_pages", "type": "gauge"},
        {"name": "database.buffer_pool.clean_page_count", "type": "gauge"},
        {"name": "database.buffer_pool.clean_pages", "type": "gauge"},
        {"name": "database.buffer_pool.data_page_count", "type": "gauge"},
        {"name": "database.buffer_pool.index_page_count", "type": "gauge"},
        {"name": "database.buffer_pool.text_page_count", "type": "gauge"},
        {"name": "database.buffer_pool.other_page_count", "type": "gauge"},
    ],
}


class SqlserverDatabaseMemoryMetrics(SqlserverDatabaseMetricsBase):
    """
    Collects database memory metrics from sys.dm_os_buffer_descriptors.
    This provides insights into buffer pool usage per database.
    """

    @property
    def include_database_memory_metrics(self) -> bool:
        return self.config.database_metrics_config["db_memory_metrics"]["enabled"]

    @property
    def enabled(self):
        if not self.include_database_memory_metrics:
            return False
        return True

    @property
    def queries(self):
        return [DATABASE_MEMORY_METRICS_QUERY_MAPPING]

    @property
    def databases(self):
        """
        This metric runs at instance level since we aggregate across all databases
        in a single query for performance reasons.
        """
        return [None]

    @property
    def is_database_instance_query(self):
        """
        Returns True since we're querying at the instance level but reporting per database.
        """
        return False

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_database_memory_metrics={self.include_database_memory_metrics})"
        )

    def _build_query_executors(self):
        """
        Build query executors for database memory metrics.
        Since we query at instance level, we only need one executor.
        """
        executors = []
        executor = self.new_query_executor(
            self.queries,
            executor=self.execute_query_handler,
            extra_tags=[],
        )
        executor.compile_queries()
        executors.append(executor)
        return executors

    def execute_query_handler(self, ctx, query, job_name, elapsed_time_ms):
        """
        Executes the query and processes results with proper database tagging.
        """
        with ctx.executor(self.check.autodiscovery_query_timeout) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchall()

                if result:
                    # Process each row (database) separately
                    for row in result:
                        database_name = row[0]
                        if database_name:
                            # Add database tags for each metric
                            tags = ctx.tags + [f'db:{database_name}', f'database:{database_name}']

                            # Submit metrics for this database
                            for i, column in enumerate(ctx.columns):
                                if column['type'] == 'gauge' and i < len(row):
                                    value = row[i]
                                    if value is not None:
                                        self.check.gauge(f"sqlserver.{column['name']}", value, tags=tags)
