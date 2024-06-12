# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.checks.base import AgentCheck
from datadog_checks.base.utils.serialization import json
import logging
from time import time
from typing import Dict, NamedTuple, Optional
from .utils import default_json_event_encoding
from datadog_checks.base.agent import datadog_agent


logger = logging.getLogger(__name__)

FLUSH_INTERVAL = 60

class TelemetryOperation(NamedTuple):
    operation: str
    elapsed: Optional[float]
    count: Optional[int]

class Telemetry:
    """
    This class supports telemetry collection for database integrations. Telemetry is sent to the instance, then emitted
    to the dbm-metrics event track on an interval. Duplicate operations are deduped to last submitted before an event
    submission.
    """

    _buffer: Dict[str, TelemetryOperation]

    def __init__(self, check: AgentCheck):
        self._buffer = {}
        self._timers = {}
        self._check = check
        print("initing telemetry for", self._check.__class__.__name__) 
        self._last_flush = time()

    def add(self, operation:str, elapsed: Optional[float], count: Optional[int]):
        """
        Add a telemetry event for a given integration and operation. Events can have a count and/or an elapsed time.

        :param integration (_str_): Name of the calling integration. Examples: postgres, mysql
        :param operation (_str_): Name of the event operation. Examples: collect_schema, collect_query_metrics
        :param elapsed (_Optional[float]_): Time elapsed for the operation in milliseconds. Example: 20ms to query for list of tables in schema collection
        :param count (_Optional[int]_): Count of relevant resources. Example: 5 tables collected as part of schema collection        
        """
        self._buffer[operation] = TelemetryOperation(operation, elapsed, count)
        self.flush()

    def start(self, operation):
        """
        Start a telemetry timer for a given operation.

        :param operation (_str_): Name of the event operation. Examples: collect_schema, collect_query_metrics
        """
        self._timers[operation] = time()
    
    def end(self, operation:str, count: Optional[int] = None):
        """
        Finish a telemetry timer for a given operation and add the event with an optional count

        :param operation (_str_): Name of the event operation. Examples: collect_schema, collect_query_metrics
        :param count (_Optional[int]_): Count of relevant resources. Example: 5 tables collected as part of schema collection        
        """
        self.add(operation, time() - self._timers[operation], count)
        del self._timers[operation] 

    
    def flush(self, force = False):
        """
        Flushes any buffered events. The Telemetry instance tracks the time since last flush and will skip executions less than FLUSH_INTERVAL
        since the last events sent.

        :param submit (_function_): Submission function for the event. Typically this would be self.database_monitoring_query_metrics.
        :param force (_bool_): Send events even if less than FLUSH_INTERVAL has elapsed. Only used for testing.
        """
        elapsed_s = time() - self._last_flush 
        if not force and elapsed_s < FLUSH_INTERVAL:
            return
        for op in self._buffer.values():
            event = {
                "ddagentversion": datadog_agent.get_version(),
                "timestamp": time() * 1000,
                "kind": "agent_metrics",
                "integration": self._check.convert_to_underscore_separated(self._check.__class__.__name__),
                "operation": op.operation,
                "elapsed": op.elapsed,
                "count": op.count,
            }

            json_event = json.dumps(event, default=default_json_event_encoding)
            self._check.database_monitoring_query_metrics(json_event)
        self._buffer = {}
        self._last_flush = time()
