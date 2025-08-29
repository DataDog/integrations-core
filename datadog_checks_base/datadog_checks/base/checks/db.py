# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from . import AgentCheck

class DBCheck(AgentCheck):
    def database_monitoring_query_sample(self, raw_event):
        # type: (str) -> None
        if raw_event is None:
            return

        self.event_platform_event(self, raw_event, "dbm-samples")

    def database_monitoring_query_metrics(self, raw_event):
        # type: (str) -> None
        if raw_event is None:
            return

        self.event_platform_event(self, raw_event, "dbm-metrics")

    def database_monitoring_query_activity(self, raw_event):
        # type: (str) -> None
        if raw_event is None:
            return

        self.event_platform_event(self, raw_event, "dbm-activity")

    def database_monitoring_metadata(self, raw_event):
        # type: (str) -> None
        if raw_event is None:
            return

        self.event_platform_event(self, raw_event, "dbm-metadata")

    def database_monitoring_health(self, raw_event):
        # type: (str) -> None
        if raw_event is None:
            return

        self.event_platform_event(self, raw_event, "dbm-health")
