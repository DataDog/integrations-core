# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import abstractmethod

from datadog_checks.base.utils.db.utils import resolve_db_host

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
        if getattr(self._config, 'exclude_hostname', False):
            return None
        return self.resolved_hostname

    @property
    def resolved_hostname(self) -> str:
        if self._resolved_hostname is None:
            configured = getattr(self._config, 'reported_hostname', None)
            self._resolved_hostname = configured if configured else resolve_db_host(self._config_host)
        return self._resolved_hostname

    @property
    @abstractmethod
    def _config_host(self) -> str:
        """Return the raw connection host from the check config."""
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
