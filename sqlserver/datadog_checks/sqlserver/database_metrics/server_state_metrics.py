# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.const import (
    ENGINE_EDITION_SQL_DATABASE,
)

from .base import SqlserverDatabaseMetricsBase

QUERY_SERVER_STATIC_INFO = {
    "name": "sys.dm_os_sys_info",
    "query": """
        SELECT (os.ms_ticks/1000) AS [Server Uptime]
        ,os.cpu_count AS [CPU Count]
        ,(os.physical_memory_kb*1024) AS [Physical Memory Bytes]
        ,os.virtual_memory_kb AS [Virtual Memory Bytes]
        ,(os.committed_kb*1024) AS [Total Server Memory Bytes]
        ,(os.committed_target_kb*1024) AS [Target Server Memory Bytes]
      FROM sys.dm_os_sys_info os""".strip(),
    "columns": [
        {"name": "server.uptime", "type": "gauge"},
        {"name": "server.cpu_count", "type": "gauge"},
        {"name": "server.physical_memory", "type": "gauge"},
        {"name": "server.virtual_memory", "type": "gauge"},
        {"name": "server.committed_memory", "type": "gauge"},
        {"name": "server.target_memory", "type": "gauge"},
    ],
}


class SqlserverServerStateMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_server_state_metrics(self) -> bool:
        return self.config.database_metrics_config['server_state_metrics']['enabled']

    @property
    def enabled(self):
        # Server state queries require VIEW SERVER STATE permissions, which some managed database
        # versions do not support.

        if not self.include_server_state_metrics:
            return False
        if self.engine_edition in [ENGINE_EDITION_SQL_DATABASE]:
            return False
        return True

    @property
    def queries(self):
        return [QUERY_SERVER_STATIC_INFO]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_server_state_metrics={self.include_server_state_metrics}, "
            f"major_version={self.major_version}, "
            f"engine_edition={self.engine_edition})"
        )
