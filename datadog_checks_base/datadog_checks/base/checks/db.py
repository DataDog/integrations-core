# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from . import AgentCheck

if TYPE_CHECKING:
    from datadog_checks.base.utils.db.utils import DBMAsyncJob


class DatabaseCheck(AgentCheck):
    """
    Base class for database integrations with Database Monitoring (DBM) support.

    Provides:
    - Event platform submission methods for DBM data
    - DBM job registry for lifecycle management
    - Test mode coordination for deterministic testing
    """

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self._dbm_jobs: list[DBMAsyncJob] = []

    def register_dbm_job(self, job: DBMAsyncJob) -> DBMAsyncJob:
        """
        Register a DBM async job for lifecycle management.

        Registered jobs will be automatically cancelled when cancel() is called
        and can be waited on collectively using wait_for_all_jobs().

        Args:
            job: The DBMAsyncJob instance to register

        Returns:
            The same job instance, allowing for chaining with assignment:
                self.statement_metrics = self.register_dbm_job(StatementMetrics(...))
        """
        self._dbm_jobs.append(job)
        return job

    def cancel(self):
        """
        Cancel all registered DBM jobs.

        This sends a cancel signal to all jobs. To wait for jobs to actually
        terminate, call wait_for_all_jobs() after cancel().

        Subclasses that override this method should call super().cancel()
        to ensure all registered jobs are cancelled.
        """
        for job in self._dbm_jobs:
            job.cancel()

    def wait_for_all_jobs(self, timeout: float = 10.0):
        """
        Wait for all registered DBM job loops to terminate.

        Should be called after cancel() to ensure clean shutdown and
        prevent orphaned threads.

        Args:
            timeout: Maximum time to wait for each job in seconds
        """
        for job in self._dbm_jobs:
            if job._job_loop_future is not None:
                try:
                    job._job_loop_future.result(timeout=timeout)
                except Exception as e:
                    # Log but don't raise - we want to try waiting for all jobs
                    self.log.warning("Error waiting for job '%s' to terminate: %s", job._job_name, e)

    def enable_test_mode(self):
        """
        Enable test mode on all registered DBM jobs.

        This enables test synchronization primitives on each job,
        allowing tests to use wait_for_completion() for deterministic
        execution verification.

        This method should only be called in test code.
        """
        for job in self._dbm_jobs:
            job.enable_test_mode()

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
