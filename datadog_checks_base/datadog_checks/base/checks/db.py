# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from . import AgentCheck


class DatabaseCheck(AgentCheck):
    def database_monitoring_query_sample(self, raw_event: str):
        self.event_platform_event(raw_event, "dbm-samples")

    def database_monitoring_query_metrics(self, raw_event: str):
        self.event_platform_event(raw_event, "dbm-metrics")

    def database_monitoring_query_activity(self, raw_event: str):
        self.event_platform_event(raw_event, "dbm-activity")

    def database_monitoring_metadata(self, raw_event: str):
        self.event_platform_event(raw_event, "dbm-metadata")

    def database_monitoring_health(self, raw_event: str):
        self.event_platform_event(raw_event, "dbm-health")

    @property
    def reported_hostname(self) -> str | None:
        raise NotImplementedError("reported_hostname is not implemented for this check")

    @property
    def database_identifier(self) -> str:
        raise NotImplementedError("database_identifier is not implemented for this check")

    @property
    def dbms_version(self) -> str:
        raise NotImplementedError("dbms_version is not implemented for this check")

    @property
    def tags(self) -> list[str]:
        raise NotImplementedError("tags is not implemented for this check")

    @property
    def cloud_metadata(self) -> dict:
        raise NotImplementedError("cloud_metadata is not implemented for this check")
