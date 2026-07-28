# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import abstractmethod
from string import Template
from typing import TYPE_CHECKING, Dict, List

from datadog_checks.base.agent import datadog_agent
from datadog_checks.base.utils.db.utils import TagManager

from . import AgentCheck

if TYPE_CHECKING:
    from datadog_checks.base.utils.db.utils import DBMAsyncJob


class DatabaseCheck(AgentCheck):
    """
    Base class for Database Monitoring (DBM) integrations.
    """

    #: Authoritative DBM platform identifier for this integration.
    #: Subclasses should set this explicitly; it is the value surfaced by
    #: :attr:`dbms` and used across DBM payloads, metric name prefixes and async jobs.
    DBMS: str | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent_hostname = None
        self._database_identifier = None
        self._dbms_fallback_warning_logged = False
        self.tag_manager = TagManager()
        #: Async jobs owned by this check, keyed by job name, populated via
        #: :meth:`register_async_job`.
        self._async_job_registry: Dict[str, "DBMAsyncJob"] = {}

    def register_async_job(self, job: "DBMAsyncJob") -> "DBMAsyncJob":
        """
        Register ``job`` under its ``job_name`` so the check manages its lifecycle, and return it
        unchanged.

        Registering a job whose name matches an already-registered job replaces it. Raises
        ``ValueError`` if the job has no name.
        """
        if job.job_name is None:
            raise ValueError("Cannot register an async job without a job_name")
        self._async_job_registry[job.job_name] = job
        return job

    def run_async_jobs(self, tags: List[str]) -> None:
        """Run each registered job's loop, forwarding ``tags`` to every job."""
        for job in self._async_job_registry.values():
            job.run_job_loop(tags)

    def cancel_async_jobs(self) -> None:
        """
        Signal every registered job to stop, without waiting for loops to finish or releasing
        resources.

        Safe to call while ``check()`` is running. Follow with :meth:`shutdown_async_jobs` to wait
        for the loops and release resources.
        """
        for job in self._async_job_registry.values():
            job.cancel()

    def shutdown_async_jobs(self) -> None:
        """
        Wait for every registered job's loop to finish (:meth:`~DBMAsyncJob.wait_for_completion`)
        and run its teardown (:meth:`~DBMAsyncJob.shutdown`).

        Must not run concurrently with ``check()``.
        """
        for job in self._async_job_registry.values():
            job.wait_for_completion()
            job.shutdown()

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
        """
        The DBM platform identifier for this integration.

        Returns the :attr:`DBMS` class attribute when set. Integrations that have not yet declared
        ``DBMS`` fall back to a deprecated derivation from the class name; that fallback is
        unreliable (it only matches for some integrations) and will be removed in a future version.
        """
        if self.DBMS is not None:
            return self.DBMS
        if not self._dbms_fallback_warning_logged:
            self.log.warning(
                "%s does not set the `DBMS` class attribute; falling back to a name-derived value. "
                "This fallback is deprecated and will be removed; set `DBMS` explicitly.",
                type(self).__name__,
            )
            self._dbms_fallback_warning_logged = True
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
