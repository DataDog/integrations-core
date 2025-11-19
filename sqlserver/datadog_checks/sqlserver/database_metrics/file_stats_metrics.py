# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.const import ENGINE_EDITION_SQL_DATABASE
from datadog_checks.sqlserver.utils import is_azure_database

from .base import SqlserverDatabaseMetricsBase


class SqlserverFileStatsMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_file_stats_metrics(self) -> bool:
        return self.config.database_metrics_config["file_stats_metrics"]["enabled"]

    @property
    def enabled(self):
        if not self.include_file_stats_metrics:
            return False
        if not self.major_version and not is_azure_database(self.engine_edition):
            return False
        return True

    @property
    def queries(self):
        return [self.__get_query_file_stats()]

    def __get_query_file_stats(self) -> dict:
        """
        Construct the dm_io_virtual_file_stats QueryExecutor configuration based on the SQL Server major version
        :return: a QueryExecutor query config object
        """

        column_definitions = {
            "size_on_disk_bytes": {"name": "files.size_on_disk", "type": "gauge"},
            "num_of_reads": {"name": "files.reads", "type": "monotonic_count"},
            "num_of_bytes_read": {"name": "files.read_bytes", "type": "monotonic_count"},
            "io_stall_read_ms": {"name": "files.read_io_stall", "type": "monotonic_count"},
            "io_stall_queued_read_ms": {
                "name": "files.read_io_stall_queued",
                "type": "monotonic_count",
            },
            "num_of_writes": {"name": "files.writes", "type": "monotonic_count"},
            "num_of_bytes_written": {
                "name": "files.written_bytes",
                "type": "monotonic_count",
            },
            "io_stall_write_ms": {
                "name": "files.write_io_stall",
                "type": "monotonic_count",
            },
            "io_stall_queued_write_ms": {
                "name": "files.write_io_stall_queued",
                "type": "monotonic_count",
            },
            "io_stall": {"name": "files.io_stall", "type": "monotonic_count"},
        }

        if self.major_version <= 2012 and not is_azure_database(self.engine_edition):
            column_definitions.pop("io_stall_queued_read_ms")
            column_definitions.pop("io_stall_queued_write_ms")

        # sort columns to ensure a static column order
        sql_columns = []
        metric_columns = []
        for column in sorted(column_definitions.keys()):
            sql_columns.append("fs.{}".format(column))
            metric_columns.append(column_definitions[column])

        query_filter = ""
        if self.major_version == 2022:
            query_filter = "WHERE DB_NAME(fs.database_id) not like 'model_%'"

        query = """
        SELECT
            DB_NAME(fs.database_id),
            mf.state_desc,
            mf.name,
            mf.physical_name,
            {sql_columns}
        FROM sys.dm_io_virtual_file_stats(NULL, NULL) fs
            LEFT JOIN sys.master_files mf
                ON mf.database_id = fs.database_id
                AND mf.file_id = fs.file_id {filter};
        """

        if self.engine_edition == ENGINE_EDITION_SQL_DATABASE:
            # Azure SQL DB does not have access to the sys.master_files view
            query = """
            SELECT
                DB_NAME(DB_ID()),
                df.state_desc,
                df.name,
                df.physical_name,
                {sql_columns}
            FROM sys.dm_io_virtual_file_stats(DB_ID(), NULL) fs
                LEFT JOIN sys.database_files df
                    ON df.file_id = fs.file_id;
            """

        return {
            "name": "sys.dm_io_virtual_file_stats",
            "query": query.strip().format(sql_columns=", ".join(sql_columns), filter=query_filter),
            "columns": [
                {"name": "db", "type": "tag"},
                {"name": "state", "type": "tag"},
                {"name": "logical_name", "type": "tag"},
                {"name": "file_location", "type": "tag"},
            ]
            + metric_columns,
        }
