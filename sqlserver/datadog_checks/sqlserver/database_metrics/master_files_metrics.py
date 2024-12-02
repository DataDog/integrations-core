# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

MASTER_FILES_METRICS_QUERY = {
    "name": "sys.master_files",
    "query": """SELECT
        sys.databases.name as db,
        sys.databases.name as database_name,
        file_id,
        CASE type
            WHEN 0 THEN 'data'
            WHEN 1 THEN 'transaction_log'
            WHEN 2 THEN 'filestream'
            WHEN 3 THEN 'unknown'
            WHEN 4 THEN 'full_text'
            ELSE 'other'
        END AS file_type,
        physical_name,
        sys.master_files.state_desc as state_desc,
        ISNULL(size, 0) as size,
        sys.master_files.state as state
        from sys.master_files
        right outer join sys.databases on sys.master_files.database_id = sys.databases.database_id
    """,
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "database", "type": "tag"},
        {"name": "file_id", "type": "tag"},
        {"name": "file_type", "type": "tag"},
        {"name": "file_location", "type": "tag"},
        {"name": "database_files_state_desc", "type": "tag"},
        {"name": "size", "type": "source"},
        {"name": "database.master_files.state", "type": "gauge"},
    ],
    "extras": [
        # size is in pages, 1 page = 8 KB. Calculated after the query to avoid int overflow
        {"name": "database.master_files.size", "expression": "size*8", "submit_type": "gauge"},
    ],
}


class SqlserverMasterFilesMetrics(SqlserverDatabaseMetricsBase):
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-master-files-transact-sql
    @property
    def include_master_files_metrics(self):
        return self.config.database_metrics_config["master_files_metrics"]["enabled"]

    @property
    def enabled(self):
        if not self.include_master_files_metrics:
            return False
        return True

    @property
    def queries(self):
        return [MASTER_FILES_METRICS_QUERY]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_master_files_metrics={self.include_master_files_metrics})"
        )
