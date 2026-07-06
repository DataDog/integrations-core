# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import abstractmethod
from string import Template

from datadog_checks.base.agent import datadog_agent
from datadog_checks.base.utils.db.utils import TagManager

from . import AgentCheck


class DatabaseCheck(AgentCheck):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent_hostname = None
        self._database_identifier = None
        self.tag_manager = TagManager()

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
    def database_identifier(self) -> str:
        """
        The unique identifier for this database instance, used as the ``database_instance`` tag and
        in DBM metadata payloads.

        The value is built once (and cached) from :attr:`database_identifier_template` and
        :attr:`database_identifier_params` via :meth:`_build_database_identifier`. Integrations
        customize the result by overriding those two hooks instead of reimplementing the templating
        logic.
        """
        if self._database_identifier is None:
            self._database_identifier = self._build_database_identifier(
                self.database_identifier_template,
                self.database_identifier_params,
            )
        return self._database_identifier

    @property
    def database_identifier_template(self) -> str:
        """
        The ``string.Template``-style template used to build :attr:`database_identifier`.

        Defaults to ``"$resolved_hostname"``. Integrations typically override this to return the
        template from their configuration (e.g. ``self._config.database_identifier.template``).
        """
        return "$resolved_hostname"

    @property
    def database_identifier_params(self) -> dict:
        """
        Connection-derived values exposed to :attr:`database_identifier_template`.

        These are applied after tags, so they take precedence over any tag of the same name.
        Values are stringified by the template engine, so callers need not cast them. Defaults to an
        empty mapping.
        """
        return {}

    def _build_database_identifier(self, template: str, connection_params: dict | None = None) -> str:
        """
        Build a database identifier string from a template and the check's tags.

        Each ``key:value`` tag is exposed to the template as a ``$key`` variable, with duplicate
        keys joined by commas (after sorting tags for a stable ordering). The ``connection_params``
        mapping is applied last so connection-derived values (e.g. ``resolved_hostname``, ``host``,
        ``port``) take precedence over any tag of the same name.

        :param template: A ``string.Template``-style template, e.g. ``"$resolved_hostname"``.
        :param connection_params: Optional mapping of additional template variables.
        :return: The substituted identifier. Unknown ``$variables`` are left intact.
        """
        tag_dict: dict[str, str] = {}
        for tag in sorted(self.tags):
            if ':' in tag:
                key, value = tag.split(':', 1)
                if key in tag_dict:
                    tag_dict[key] += f",{value}"
                else:
                    tag_dict[key] = value
        if connection_params:
            tag_dict.update(connection_params)
        return Template(template).safe_substitute(**tag_dict)

    @property
    def agent_hostname(self) -> str:
        if self._agent_hostname is None:
            self._agent_hostname = datadog_agent.get_hostname()
        return self._agent_hostname

    @property
    def dbms(self) -> str:
        return self.__class__.__name__.lower()

    @property
    @abstractmethod
    def dbms_version(self) -> str:
        pass

    @property
    def tags(self) -> list[str]:
        return self.tag_manager.get_tags()

    @property
    @abstractmethod
    def cloud_metadata(self) -> dict:
        pass
