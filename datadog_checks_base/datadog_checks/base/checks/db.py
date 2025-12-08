# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import abstractmethod

from datadog_checks.base.utils.db.utils import default_json_event_encoding
from datadog_checks.base.utils.serialization import json

from . import AgentCheck


class DatabaseCheck(AgentCheck):
    def database_monitoring_query_sample(self, raw_event: dict):
        self.set_event_platform_properties(raw_event, "dbm-samples")
        self.event_platform_event(json.dumps(raw_event, default=default_json_event_encoding), "dbm-samples")

    def database_monitoring_query_metrics(self, raw_event: dict):
        self.set_event_platform_properties(raw_event, "dbm-metrics")
        self.event_platform_event(json.dumps(raw_event, default=default_json_event_encoding), "dbm-metrics")

    def database_monitoring_query_activity(self, raw_event: dict):
        self.set_event_platform_properties(raw_event, "dbm-activity")
        self.event_platform_event(json.dumps(raw_event, default=default_json_event_encoding), "dbm-activity")

    def database_monitoring_metadata(self, raw_event: dict):
        self.set_event_platform_properties(raw_event, "dbm-metadata")
        self.event_platform_event(json.dumps(raw_event, default=default_json_event_encoding), "dbm-metadata")

    def database_monitoring_health(self, raw_event: dict):
        self.set_event_platform_properties(raw_event, "dbm-health")
        self.event_platform_event(json.dumps(raw_event, default=default_json_event_encoding), "dbm-health")

    def set_event_platform_properties(self, raw_event: dict, track: str):
        # Ensure all events have shared properties
        raw_event["track"] = track
        raw_event["database_instance"] = self.database_identifier
        raw_event["dbms"] = self.dbms
        raw_event["dbms_version"] = self.dbms_version

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
