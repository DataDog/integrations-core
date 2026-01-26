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

import time
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.db.health import Health, HealthEvent, HealthStatus
from datadog_checks.base.utils.serialization import json


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
        cooldown_time: int | None = None,
        cooldown_values: list[str] | None = None,
    ):
        """
        Submit a health event to the aggregator.

        This overrides the base implementation to:
        1. Add ClickHouse-specific metadata (database_instance, ddagenthostname)
        2. Properly serialize enum values for JSON

        Args:
            name: The name of the health event (HealthEvent or ClickhouseHealthEvent).
            status: The health status to submit (OK, WARNING, ERROR).
            tags: Additional tags to include with the event.
            data: A dictionary to be submitted as `data`. Must be JSON serializable.
            cooldown_time: Optional cooldown period in seconds.
            cooldown_values: Optional additional values for cooldown key.
        """
        # Build tags - handle case where check tags may not be available yet
        event_tags = []
        if hasattr(self.check, 'tags') and self.check.tags:
            event_tags = list(self.check.tags)
        if tags:
            event_tags.extend(tags)

        # Build data with ClickHouse-specific fields
        event_data = {
            "database_instance": (
                self.check.database_identifier if hasattr(self.check, 'database_identifier') else None
            ),
            "ddagenthostname": self.check.agent_hostname if hasattr(self.check, 'agent_hostname') else None,
        }
        if data:
            event_data.update(data)

        # Handle cooldown
        category = self.check.__NAMESPACE__ or self.check.__class__.__name__.lower()
        name_value = name.value if hasattr(name, 'value') else str(name)
        status_value = status.value if hasattr(status, 'value') else str(status)

        if cooldown_time:
            cooldown_key = "|".join([category, name_value, status_value])
            if cooldown_values:
                cooldown_key = "|".join([cooldown_key, "|".join([f"{v}" for v in cooldown_values])])
            with self._cache_lock:
                if self._ttl_cache.get(cooldown_key, None):
                    return
                self._ttl_cache[cooldown_key] = cooldown_time

        # Submit the event with properly serialized enum values
        self.check.event_platform_event(
            json.dumps(
                {
                    'timestamp': time.time() * 1000,
                    'version': 1,
                    'check_id': self.check.check_id,
                    'category': category,
                    'name': name_value,
                    'status': status_value,
                    'tags': event_tags,
                    'ddagentversion': datadog_agent.get_version(),
                    'ddagenthostname': datadog_agent.get_hostname(),
                    'data': event_data,
                }
            ),
            "dbm-health",
        )


# Re-export for convenience
__all__ = ['ClickhouseHealth', 'ClickhouseHealthEvent', 'HealthEvent', 'HealthStatus']
