# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

from enum import Enum

from datadog_checks.base.utils.db.health import Health, HealthEvent, HealthStatus


class PostgresHealthEvent(Enum):
    """
    Enum representing the health events for PostgreSQL monitoring.
    """

    EXPLAIN_PLAN_ERROR = 'explain_plan_error'


class PostgresHealth(Health):
    def __init__(self, check: PostgreSql):
        # type: (PostgreSql) -> None
        """
        Initialize the PostgresHealth instance.

        :param check: PostgreSql
            The check instance that will be used to submit health events.
        """
        super().__init__(check)
        self.check = check

    def submit_health_event(
        self,
        name: HealthEvent | PostgresHealthEvent,
        status: HealthStatus,
        data: dict,
    ):
        """
        Submit a health event to the aggregator.

        :param name: PostgresHealthEvent
            The name of the health event.
        :param status: HealthStatus
            The health status to submit.
        :param data: A dictionary to be submitted as `data`. Must be JSON serializable.
        """
        super().submit_health_event(
            name=name,
            status=status,
            # If we have an error parsing the config we may not have tags yet
            tags=self.check.tags if hasattr(self.check, 'tags') else [],
            data={
                "database_instance": self.check.database_identifier,
                "ddagenthostname": self.check.agent_hostname,
                **(data or {}),
            },
        )
