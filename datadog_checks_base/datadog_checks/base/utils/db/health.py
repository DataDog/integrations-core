# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# This is the base implementation of the Agent Health reporting system.
# It provides a structure for health events and codes that can be extended by specific checks.

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from cachetools import TLRUCache

from datadog_checks.base.utils.serialization import json

if TYPE_CHECKING:
    from datadog_checks.base import DatabaseCheck
try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


from enum import Enum


class HealthEvent(Enum):
    """
    Enum representing the health events.
    """

    INITIALIZATION = 'initialization'
    MISSED_COLLECTION = 'missed_collection'


class HealthStatus(Enum):
    """
    Enum representing the health statuses for a given event.
    """

    OK = 'ok'
    WARNING = 'warning'
    ERROR = 'error'

DEFAULT_COOLDOWN = 60*5
def ttl(_key, value, now):
    return now + value

class Health:
    def __init__(self, check: DatabaseCheck):
        """
        Initialize the HealthCheck instance.

        :param check: AgentCheck
            The check instance that will be used to submit health events.
        """
        self.check = check
        self._ttl_cache = TLRUCache(maxsize=1000, ttu=ttl)

    def submit_health_event(self, name: HealthEvent, status: HealthStatus, tags: list[str] = None, cooldown: bool = False, cooldown_time: int = DEFAULT_COOLDOWN, cooldown_keys: list[str] = None, **kwargs):
        """
        Submit a health event to the aggregator.

        :param name: HealthEvent
            The name of the health event.
        :param status: HealthStatus
            The health status to submit.
        :param tags: list of str
            Tags to associate with the health event.
        :param cooldown: int
            The cooldown period in seconds to prevent the events with the same name and status from being submitted again.
        :param cooldown_keys: list of str
            Additional kwargs keys to include in the cooldown key.
        :param kwargs: Additional keyword arguments to include in the event under `data`.
        """
        category = self.check.__NAMESPACE__ or self.check.__class__.__name__.lower()
        if cooldown:
            cooldown_key = "|".join([category, name.value, status.value])
            if cooldown_keys:
                cooldown_key = "|".join([cooldown_key, "|".join([f"{k}={kwargs[k]}" for k in cooldown_keys])])
            if self._ttl_cache.get(cooldown_key, None):
                return
            self._ttl_cache[cooldown_key] = cooldown_time
        self.check.event_platform_event(
            json.dumps(
                {
                    'timestamp': time.time() * 1000,
                    'version': 1,
                    'check_id': self.check.check_id,
                    'category': category,
                    'name': name,
                    'status': status,
                    'tags': tags or [],
                    'ddagentversion': datadog_agent.get_version(),
                    'ddagenthostname': datadog_agent.get_hostname(),
                    'data': {**kwargs},
                }
            ),
            "dbm-health",
        )
