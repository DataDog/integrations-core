# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# This is the base implementation of the Agent Health reporting system.
# It provides a structure for health events and codes that can be extended by specific checks.

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from datadog_checks.base.utils.serialization import json

if TYPE_CHECKING:
    from datadog_checks.base import DatabaseCheck
try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


import traceback
from enum import Enum


class HealthEvent(Enum):
    """
    Enum representing the health events.
    """

    INITIALIZATION = 'initialization'
    UNKNOWN_ERROR = 'unknown_error'


class HealthStatus(Enum):
    """
    Enum representing the health statuses for a given event.
    """

    OK = 'ok'
    WARNING = 'warning'
    ERROR = 'error'


class Health:
    def __init__(self, check: DatabaseCheck):
        """
        Initialize the HealthCheck instance.

        :param check: AgentCheck
            The check instance that will be used to submit health events.
        """
        self.check = check

    def submit_health_event(self, name: HealthEvent, status: HealthStatus, tags: list[str] = None, **kwargs):
        """
        Submit a health event to the aggregator.

        :param name: HealthEvent
            The name of the health event.
        :param status: HealthStatus
            The health status to submit.
        :param tags: list of str
            Tags to associate with the health event.
        :param kwargs: Additional keyword arguments to include in the event under `data`.
        """
        self.check.event_platform_event(
            json.dumps(
                {
                    'timestamp': time.time() * 1000,
                    'version': 1,
                    'check_id': self.check.check_id,
                    'category': self.check.__NAMESPACE__ or self.check.__class__.__name__.lower(),
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

    def submit_exception_health_event(self, exception: Exception, **kwargs):
        trace = traceback.extract_tb(exception.__traceback__)
        exc = trace.pop()
        if exc:
            self.submit_health_event(
                name=HealthEvent.UNKNOWN_ERROR,
                status=HealthStatus.ERROR,
                file=exc.filename,
                line=exc.lineno,
                function=exc.name,
                exception_type=type(exception).__name__,
                **kwargs,
            )
