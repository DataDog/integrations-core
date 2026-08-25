# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.sqlserver import SqlServer

from enum import Enum

from datadog_checks.base.utils.db.health import Health, HealthEvent, HealthStatus


class SqlServerHealthEvent(Enum):
    """
    Enum representing the health events for SqlServer monitoring.
    """

    EXPLAIN_PLAN_ERROR = 'explain_plan_error'


class SqlServerHealth(Health):
    def __init__(self, check: SqlServer):
        # type: (SqlServer) -> None
        """
        Initialize the SqlServerHealth instance.

        :param check: SqlServer
            The check instance that will be used to submit health events.
        """
        super().__init__(check)
        self.check = check

    def submit_health_event(
        self,
        name: HealthEvent | SqlServerHealthEvent,
        status: HealthStatus,
        tags: list[str] = None,
        data: dict = None,
        **kwargs,
    ):
        """
        Submit a health event to the aggregator.

        :param name: SqlServerHealthEvent
            The name of the health event.
        :param status: HealthStatus
            The health status to submit.
        :param data: A dictionary to be submitted as `data`. Must be JSON serializable.
        """
        super().submit_health_event(
            name=name,
            status=status,
            # If we have an error parsing the config we may not have tags yet
            tags=(self.check.tags if hasattr(self.check, 'tags') else []) + (tags or []),
            data={
                "database_instance": self.check.database_identifier,
                "ddagenthostname": self.check.agent_hostname,
                **(data or {}),
            },
            **kwargs,
        )
