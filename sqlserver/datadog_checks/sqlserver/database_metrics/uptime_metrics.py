# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.const import (
    ENGINE_EDITION_AZURE_SYNAPSE_ANALYTICS,
    ENGINE_EDITION_AZURE_SYNAPSE_SERVERLESS_POOL,
)

from .base import SqlserverDatabaseMetricsBase

QUERY_UPTIME = {
    "name": "sys.dm_os_sys_info.uptime",
    "query": """
        SELECT (os.ms_ticks - os.sqlserver_start_time_ms_ticks)/1000 AS [Uptime]
      FROM sys.dm_os_sys_info os""".strip(),
    "columns": [
        {"name": "uptime", "type": "gauge"},
    ],
}


class SqlserverUptimeMetrics(SqlserverDatabaseMetricsBase):
    """
    Seconds elapsed since the SQL Server database engine last started.
    """

    @property
    def enabled(self) -> bool:
        # Synapse exposes this data through sys.dm_pdw_nodes_os_sys_info, and the serverless pool not at all.
        if self.engine_edition in (
            ENGINE_EDITION_AZURE_SYNAPSE_ANALYTICS,
            ENGINE_EDITION_AZURE_SYNAPSE_SERVERLESS_POOL,
        ):
            return False
        return True

    @property
    def queries(self) -> list[dict]:
        return [QUERY_UPTIME]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"major_version={self.major_version}, "
            f"engine_edition={self.engine_edition})"
        )
