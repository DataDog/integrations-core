# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

from enum import Enum

from datadog_checks.base.utils.db.health import Health, HealthEvent, HealthStatus


class ClickhouseHealthEvent(Enum):
    """
    Enum representing the health events for ClickHouse monitoring.
    """

    # Placeholder for future ClickHouse-specific health events
    pass


class ClickhouseHealth(Health):
    def __init__(self, check: ClickhouseCheck):
        """
        Initialize the ClickhouseHealth instance.

        :param check: ClickhouseCheck
            The check instance that will be used to submit health events.
        """
        super().__init__(check)
        self.check = check

    def submit_health_event(
        self,
        name: HealthEvent | ClickhouseHealthEvent,
        status: HealthStatus,
        tags: list[str] = None,
        data: dict = None,
        **kwargs,
    ):
        """
        Submit a health event to the aggregator.

        :param name: HealthEvent | ClickhouseHealthEvent
            The name of the health event.
        :param status: HealthStatus
            The health status to submit.
        :param tags: list[str]
            Additional tags to include with the health event.
        :param data: dict
            A dictionary to be submitted as `data`. Must be JSON serializable.
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
