# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

# Excldue internal databases
# 32767: mssqlsystemresource
# 32761: model_msdb
# 32762: model_replicatedmaster
DATABASE_MEMORY_METRICS_QUERY = """
    SELECT
        DB_NAME(database_id) as database_name,
        database_id,
        COUNT(*) * 8 / 1024.0 as buffer_pool_size_mb,
        SUM(CAST(is_modified AS INT)) * 8 / 1024.0 as dirty_pages_mb
    FROM sys.dm_os_buffer_descriptors WITH (NOLOCK)
    WHERE database_id NOT IN (32767,32761,32762)
    GROUP BY database_id;
"""

DATABASE_MEMORY_METRICS_QUERY_MAPPING = {
    "name": "database_memory_metrics",
    "query": DATABASE_MEMORY_METRICS_QUERY,
    "columns": [
        {"name": "database_name", "type": "tag"},
        {"name": "database_id", "type": "tag"},
        {"name": "database.buffer_pool.size", "type": "gauge"},
        {"name": "database.buffer_pool.dirty_pages", "type": "gauge"},
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
    def collection_interval(self) -> int:
        '''
        Returns the interval in seconds at which to collect database memory metrics.
        Note: Querying sys.dm_os_buffer_descriptors can be resource intensive on systems with large buffer pools.
        '''
        value = self.config.database_metrics_config["db_memory_metrics"].get("collection_interval", 300)
        # Validate to ensure it's a reasonable positive integer
        if not isinstance(value, (int, float)) or value < 60:
            self.log.warning("Invalid collection_interval value: %s, using default of 300", value)
            return 300
        # Convert to int and cap at a reasonable maximum (1 hour)
        value = int(value)
        if value > 3600:
            self.log.warning("collection_interval value too high: %s, capping at 3600", value)
            return 3600
        return value

    @property
    def min_page_count(self) -> int:
        '''
        Returns the minimum number of pages a database must have in the buffer pool to be reported.
        This helps reduce noise from databases with minimal memory usage.
        '''
        value = self.config.database_metrics_config["db_memory_metrics"].get("min_page_count", 1)
        # Validate to prevent SQL injection - must be a positive integer
        if not isinstance(value, int) or value < 0:
            self.log.warning("Invalid min_page_count value: %s, using default of 1", value)
            return 1
        # Cap at a reasonable maximum to prevent issues
        if value > 1000000:  # ~7.8GB worth of pages
            self.log.warning("min_page_count value too high: %s, capping at 1000000", value)
            return 1000000
        return value

    @property
    def enabled(self) -> bool:
        return self.include_database_memory_metrics

    @property
    def queries(self):
        # Add collection interval to the query mapping and apply min_page_count filter
        query_mapping = DATABASE_MEMORY_METRICS_QUERY_MAPPING.copy()
        query_mapping['collection_interval'] = self.collection_interval

        # Modify query to apply min_page_count filter if set
        # Use validated integer value to prevent SQL injection
        min_count = self.min_page_count
        if min_count > 1:
            # Ensure min_count is an integer (redundant but safe)
            min_count = int(min_count)
            query = query_mapping['query'].replace("HAVING COUNT(*) > 0", f"HAVING COUNT(*) >= {min_count}")
            query_mapping['query'] = query

        return [query_mapping]

    @property
    def databases(self):
        """
        This metric runs at instance level since we aggregate across all databases
        in a single query for performance reasons.
        """
        return [None]

    @property
    def is_database_instance_query(self) -> bool:
        """
        Returns False since we handle the database tagging manually in execute_query_handler.
        """
        return False

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"collection_interval={self.collection_interval}, "
            f"min_page_count={self.min_page_count})"
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
        Includes error handling and logging for production stability.
        """
        try:
            with ctx.executor(self.check.autodiscovery_query_timeout) as conn:
                with conn.cursor() as cursor:
                    self.log.debug("Executing database memory metrics query")
                    cursor.execute(query)
                    result = cursor.fetchall()

                    if not result:
                        self.log.debug("No database memory metrics results returned")
                        return

                    # Log query execution time for monitoring
                    self.log.debug(
                        "Database memory metrics query completed in %d ms with %d databases",
                        elapsed_time_ms,
                        len(result),
                    )

                    # Warn if query is taking too long (more than 5 seconds)
                    if elapsed_time_ms > 5000:
                        self.log.warning(
                            "Database memory metrics query took %d ms, consider increasing collection_interval "
                            "or min_page_count to reduce load",
                            elapsed_time_ms,
                        )

                    # Process each row (database) separately
                    databases_processed = 0
                    metrics_submitted = 0
                    for row in result:
                        try:
                            database_name = row[0]
                            if not database_name:
                                continue

                            # Sanitize database name for tagging (handle special characters)
                            # This prevents issues with database names containing colons or other special chars
                            safe_db_name = str(database_name).replace(':', '_').replace(',', '_')

                            # Add database tags for each metric
                            tags = ctx.tags + [f'db:{safe_db_name}', f'database:{safe_db_name}']

                            # Submit metrics for this database
                            for i, column in enumerate(ctx.columns):
                                if column['type'] == 'gauge' and i < len(row):
                                    value = row[i]
                                    if value is not None:
                                        self.check.gauge(f"sqlserver.{column['name']}", value, tags=tags)
                                        metrics_submitted += 1
                            databases_processed += 1
                        except Exception as e:
                            self.log.warning(
                                "Error processing database memory metrics for row %s: %s",
                                row[0] if row and len(row) > 0 else "unknown",
                                str(e),
                            )
                            continue

                    # Log summary statistics
                    if databases_processed > 0:
                        self.log.debug(
                            "Successfully processed %d databases and submitted %d metrics",
                            databases_processed,
                            metrics_submitted,
                        )

        except Exception as e:
            self.log.error(
                "Failed to execute database memory metrics query: %s",
                str(e),
                exc_info=self.log.isEnabledFor(self.log.DEBUG),
            )
