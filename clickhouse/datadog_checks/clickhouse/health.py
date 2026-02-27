# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
ClickHouse health event reporting.

Provides health event submission for DBM monitoring, including:
- Configuration validation results
- Query collection errors
- Connection issues
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

from datadog_checks.base.utils.db.health import Health, HealthEvent, HealthStatus


class ClickhouseHealthEvent(Enum):
    """
    Enum representing ClickHouse-specific health events.
    """

    QUERY_LOG_ERROR = 'query_log_error'
    CONNECTION_ERROR = 'connection_error'


class ClickhouseHealth(Health):
    """
    ClickHouse-specific health event handler.

    Extends the base Health class to include ClickHouse-specific metadata
    in health events (database_instance, ddagenthostname, etc.).
    """

    def __init__(self, check: ClickhouseCheck):
        """
        Initialize the ClickhouseHealth instance.

        Args:
            check: The ClickhouseCheck instance that will be used to submit health events.
        """
        super().__init__(check)
        self.check = check

    def submit_health_event(
        self,
        name: HealthEvent | ClickhouseHealthEvent,
        status: HealthStatus,
        tags: list[str] | None = None,
        data: dict | None = None,
        **kwargs,
    ):
        """
        Submit a health event to the aggregator.

        Args:
            name: The name of the health event (HealthEvent or ClickhouseHealthEvent).
            status: The health status to submit (OK, WARNING, ERROR).
            tags: Additional tags to include with the event.
            data: A dictionary to be submitted as `data`. Must be JSON serializable.
            **kwargs: Additional arguments passed to the base class (e.g., cooldown_time, cooldown_values).
        """
        super().submit_health_event(
            name=name,
            status=status,
            # Handle case where check tags may not be available yet during initialization
            tags=(self.check.tags if hasattr(self.check, 'tags') else []) + (tags or []),
            data={
                "database_instance": (
                    self.check.database_identifier if hasattr(self.check, 'database_identifier') else None
                ),
                "ddagenthostname": self.check.agent_hostname if hasattr(self.check, 'agent_hostname') else None,
                **(data or {}),
            },
            **kwargs,
        )


# Re-export for convenience
__all__ = ['ClickhouseHealth', 'ClickhouseHealthEvent', 'HealthEvent', 'HealthStatus']
