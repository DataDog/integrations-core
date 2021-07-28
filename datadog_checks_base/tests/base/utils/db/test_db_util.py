# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from concurrent.futures.thread import ThreadPoolExecutor

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db.utils import ConstantRateLimiter, DBMAsyncJob, RateLimitingTTLCache


def test_constant_rate_limiter():
    rate_limit = 8
    test_duration_s = 0.5
    ratelimiter = ConstantRateLimiter(rate_limit)
    start = time.time()
    sleep_count = 0
    while time.time() - start < test_duration_s:
        ratelimiter.sleep()
        sleep_count += 1
    max_expected_count = rate_limit * test_duration_s
    assert max_expected_count - 1 <= sleep_count <= max_expected_count + 1


def test_ratelimiting_ttl_cache():
    ttl = 0.1
    cache = RateLimitingTTLCache(maxsize=5, ttl=ttl)

    for i in range(5):
        assert cache.acquire(i), "cache is empty so the first set of keys should pass"
    for i in range(5, 10):
        assert not cache.acquire(i), "cache is full so we do not expect any more new keys to pass"
    for i in range(5):
        assert not cache.acquire(i), "none of the first set of keys should pass because they're still under TTL"

    assert len(cache) == 5, "cache should be at the max size"
    time.sleep(ttl * 2)
    assert len(cache) == 0, "cache should be empty after the TTL has kicked in"

    for i in range(5, 10):
        assert cache.acquire(i), "cache should be empty again so these keys should go in OK"


class TestDBExcepption(BaseException):
    pass


class TestJob(DBMAsyncJob):
    def __init__(self, check, run_sync=False, enabled=True, rate_limit=10, min_collection_interval=15):
        super(TestJob, self).__init__(
            check,
            run_sync=run_sync,
            enabled=enabled,
            expected_db_exceptions=(TestDBExcepption,),
            min_collection_interval=min_collection_interval,
            config_host="test-host",
            dbms="test-dbms",
            rate_limit=rate_limit,
            job_name="test-job",
            shutdown_callback=self.test_shutdown,
        )

    def test_shutdown(self):
        self._check.count("dbm.async_job_test.shutdown", 1)

    def run_job(self):
        self._check.count("dbm.async_job_test.run_job", 1)


def test_dbm_async_job():
    check = AgentCheck()
    TestJob(check)


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.mark.parametrize("enabled", [True, False])
def test_dbm_async_job_enabled(enabled):
    check = AgentCheck()
    job = TestJob(check, enabled=enabled)
    job.run_job_loop([])
    if enabled:
        assert job._job_loop_future is not None
        job.cancel()
        job._job_loop_future.result()
    else:
        assert job._job_loop_future is None


def test_dbm_async_job_cancel(aggregator):
    job = TestJob(AgentCheck())
    tags = ["hello:there"]
    job.run_job_loop(tags)
    job.cancel()
    job._job_loop_future.result()
    assert not job._job_loop_future.running(), "thread should be stopped"
    # if the thread doesn't start until after the cancel signal is set then the db connection will never
    # be created in the first place
    expected_tags = tags + ['job:test-job']
    aggregator.assert_metric("dd.test-dbms.async_job.cancel", tags=expected_tags)
    aggregator.assert_metric("dbm.async_job_test.shutdown")


def test_dbm_async_job_run_sync(aggregator):
    job = TestJob(AgentCheck(), run_sync=True)
    job.run_job_loop([])
    assert job._job_loop_future is None
    aggregator.assert_metric("dbm.async_job_test.run_job")


def test_dbm_async_job_rate_limit(aggregator):
    # test the main collection loop rate limit
    rate_limit = 10
    sleep_time = 1

    job = TestJob(AgentCheck(), rate_limit=rate_limit)
    job.run_job_loop([])

    time.sleep(sleep_time)
    max_collections = int(rate_limit * sleep_time) + 1
    job.cancel()

    metrics = aggregator.metrics("dbm.async_job_test.run_job")
    assert max_collections / 2.0 <= len(metrics) <= max_collections


def test_dbm_async_job_inactive_stop(aggregator):
    job = TestJob(AgentCheck(), rate_limit=10, min_collection_interval=1)
    job.run_job_loop([])
    job._job_loop_future.result()
    aggregator.assert_metric("dd.test-dbms.async_job.inactive_stop", tags=['job:test-job'])
