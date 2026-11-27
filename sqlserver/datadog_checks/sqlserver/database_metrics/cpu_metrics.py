# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.const import (
    ENGINE_EDITION_AZURE_MANAGED_INSTANCE,
    ENGINE_EDITION_AZURE_SYNAPSE_ANALYTICS,
    ENGINE_EDITION_AZURE_SYNAPSE_SERVERLESS_POOL,
    ENGINE_EDITION_SQL_DATABASE,
)

from .base import SqlserverDatabaseMetricsBase

SQLSERVER_2016_MAJOR_VERSION = 13

UNSUPPORTED_ENGINE_EDITIONS = (
    ENGINE_EDITION_SQL_DATABASE,
    ENGINE_EDITION_AZURE_SYNAPSE_ANALYTICS,
    ENGINE_EDITION_AZURE_SYNAPSE_SERVERLESS_POOL,
)

CPU_SCHEDULERS_QUERY = {
    "name": "cpu_metrics.schedulers",
    "query": """SELECT
        SUM(total_cpu_usage_ms),
        SUM(total_scheduler_delay_ms),
        COUNT(*)
        FROM sys.dm_os_schedulers
        WHERE status = 'VISIBLE ONLINE'
    """,
    "columns": [
        {"name": "cpu.usage_ms", "type": "monotonic_count"},
        {"name": "cpu.scheduler_delay_ms", "type": "monotonic_count"},
        {"name": "cpu.online_schedulers", "type": "gauge"},
    ],
}

CPU_WAIT_STATS_QUERY = {
    "name": "cpu_metrics.wait_stats",
    "query": "SELECT SUM(signal_wait_time_ms) FROM sys.dm_os_wait_stats",
    "columns": [
        {"name": "cpu.signal_wait_ms", "type": "monotonic_count"},
    ],
}


class SqlserverCpuMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_cpu_metrics(self) -> bool:
        return self.config.database_metrics_config["cpu_metrics"]["enabled"]

    @property
    def enabled(self) -> bool:
        if not self.include_cpu_metrics:
            return False
        if self.engine_edition in UNSUPPORTED_ENGINE_EDITIONS:
            return False
        return (
            self.engine_edition == ENGINE_EDITION_AZURE_MANAGED_INSTANCE
            or self.major_version >= SQLSERVER_2016_MAJOR_VERSION
        )

    @property
    def queries(self) -> list[dict]:
        return [CPU_SCHEDULERS_QUERY, CPU_WAIT_STATS_QUERY]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_cpu_metrics={self.include_cpu_metrics}, "
            f"major_version={self.major_version}, "
            f"engine_edition={self.engine_edition})"
        )
