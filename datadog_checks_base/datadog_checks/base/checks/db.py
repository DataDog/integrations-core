# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import abstractmethod

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
    @abstractmethod
    def reported_hostname(self) -> str | None:
        pass

    @property
    @abstractmethod
    def database_identifier(self) -> str:
        pass

    @property
    def dbms(self) -> str:
        return self.__class__.__name__.lower()

    @property
    @abstractmethod
    def dbms_version(self) -> str:
        pass

    @property
    @abstractmethod
    def tags(self) -> list[str]:
        pass

    @property
    @abstractmethod
    def cloud_metadata(self) -> dict:
        pass
