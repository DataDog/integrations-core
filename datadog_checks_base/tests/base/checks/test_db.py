# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Tests for DatabaseCheck base class.
"""

from concurrent.futures.thread import ThreadPoolExecutor

import pytest

from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.utils.db.utils import DBMAsyncJob


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    """Ensure a fresh ThreadPoolExecutor for each test."""
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


class JobForTesting(DBMAsyncJob):
    """Simple DBMAsyncJob implementation for testing."""

    def __init__(self, check, enabled=True, rate_limit=10):
        super().__init__(
            check,
            run_sync=False,
            enabled=enabled,
            expected_db_exceptions=(),
            min_collection_interval=15,
            config_host="test-host",
            dbms="test-dbms",
            rate_limit=rate_limit,
            job_name="test-job",
        )
        self.run_count = 0

    def run_job(self):
        self.run_count += 1


class DatabaseCheckForTesting(DatabaseCheck):
    """Concrete implementation of DatabaseCheck for testing."""

    def __init__(self):
        super().__init__("test_db_check", {}, [{}])
        self._reported_hostname = "test-host"
        self._database_identifier = "test-db"
        self._dbms_version = "1.0"
        self._tags_list = ["env:test"]
        self._cloud_metadata_dict = {}

    @property
    def reported_hostname(self) -> str | None:
        return self._reported_hostname

    @property
    def database_identifier(self) -> str:
        return self._database_identifier

    @property
    def dbms_version(self) -> str:
        return self._dbms_version

    @property
    def tags(self) -> list[str]:
        return self._tags_list

    @property
    def cloud_metadata(self) -> dict:
        return self._cloud_metadata_dict


class TestDatabaseCheckRegistry:
    """Tests for DBM job registry functionality."""

    def test_register_dbm_job(self):
        """Test that jobs can be registered with chaining pattern."""
        check = DatabaseCheckForTesting()
        assert len(check._dbm_jobs) == 0

        # Test the chaining pattern used in integrations
        check.my_job = check.register_dbm_job(JobForTesting(check))

        assert check.my_job in check._dbm_jobs
        assert len(check._dbm_jobs) == 1

        # Register a second job
        check.register_dbm_job(JobForTesting(check))
        assert len(check._dbm_jobs) == 2

    def test_cancel_and_wait(self):
        """Test that cancel() and wait_for_all_jobs() work together."""
        check = DatabaseCheckForTesting()
        job1 = check.register_dbm_job(JobForTesting(check, rate_limit=10))
        job2 = check.register_dbm_job(JobForTesting(check, rate_limit=10))

        # Start the jobs
        job1.run_job_loop([])
        job2.run_job_loop([])

        # Cancel and wait
        check.cancel()
        check.wait_for_all_jobs(timeout=5)

        # Both should be cancelled and stopped
        assert job1._cancel_event.is_set()
        assert job2._cancel_event.is_set()
        assert not job1._job_loop_future.running()
        assert not job2._job_loop_future.running()

    def test_wait_for_all_jobs_handles_none_futures(self):
        """Test that wait_for_all_jobs handles jobs that were never started."""
        check = DatabaseCheckForTesting()
        job1 = check.register_dbm_job(JobForTesting(check, enabled=False))
        job2 = check.register_dbm_job(JobForTesting(check))

        # Only job2 starts (job1 disabled)
        job1.run_job_loop([])
        job2.run_job_loop([])

        assert job1._job_loop_future is None
        assert job2._job_loop_future is not None

        # Should not raise even though job1 has no future
        check.cancel()
        check.wait_for_all_jobs(timeout=5)

    def test_enable_test_mode(self):
        """Test that enable_test_mode enables test mode on all jobs."""
        check = DatabaseCheckForTesting()
        job1 = check.register_dbm_job(JobForTesting(check))
        job2 = check.register_dbm_job(JobForTesting(check))

        check.enable_test_mode()

        assert job1._test_mode is True
        assert job2._test_mode is True
