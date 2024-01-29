# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import decimal
import time
from concurrent.futures.thread import ThreadPoolExecutor
from ipaddress import IPv4Address

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.datadog_agent import datadog_agent
from datadog_checks.base.utils.db.utils import (
    ConstantRateLimiter,
    DBMAsyncJob,
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
    resolve_db_host,
    tracked_query,
)
from datadog_checks.base.utils.serialization import json


@pytest.mark.parametrize(
    "db_host, agent_hostname, want",
    [
        (None, "agent_hostname", "agent_hostname"),
        ("localhost", "agent_hostname", "agent_hostname"),
        ("127.0.0.1", "agent_hostname", "agent_hostname"),
        ("192.0.2.1", "agent_hostname", "192.0.2.1"),
        ("socket.gaierror", "agent_hostname", "agent_hostname"),
        ("greater-than-or-equal-to-64-characters-causes-unicode-error-----", "agent_hostname", "agent_hostname"),
        ("192.0.2.1", "socket.gaierror", "192.0.2.1"),
        ("192.0.2.1", "greater-than-or-equal-to-64-characters-causes-unicode-error-----", "192.0.2.1"),
        ("192.0.2.1", "192.0.2.1", "192.0.2.1"),
        ("192.0.2.1", "192.0.2.254", "192.0.2.1"),
    ],
)
def test_resolve_db_host(db_host, agent_hostname, want):
    datadog_agent.set_hostname(agent_hostname)
    assert resolve_db_host(db_host) == want
    datadog_agent.reset_hostname()


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


@pytest.mark.parametrize(
    "obfuscator_return_value,expected_value",
    [
        (
            json.dumps(
                {
                    'query': 'SELECT * FROM datadog',
                    'metadata': {'tables_csv': 'datadog,', 'commands': ['SELECT'], 'comments': None},
                }
            ),
            {
                'query': 'SELECT * FROM datadog',
                'metadata': {'commands': ['SELECT'], 'comments': None, 'tables': ['datadog']},
            },
        ),
        (
            # Whitespace test
            "  {\"query\":\"SELECT * FROM datadog\",\"metadata\":{\"tables_csv\":\"datadog\",\"commands\":[\"SELECT\"],"
            "\"comments\":null}}          ",
            {
                'query': 'SELECT * FROM datadog',
                'metadata': {'commands': ['SELECT'], 'comments': None, 'tables': ['datadog']},
            },
        ),
        (
            json.dumps(
                {
                    'query': 'SELECT * FROM datadog WHERE age = (SELECT AVG(age) FROM datadog2)',
                    'metadata': {
                        'tables_csv': '    datadog,  datadog2      ',
                        'commands': ['SELECT', 'SELECT'],
                        'comments': ['-- Test comment'],
                    },
                }
            ),
            {
                'query': 'SELECT * FROM datadog WHERE age = (SELECT AVG(age) FROM datadog2)',
                'metadata': {
                    'commands': ['SELECT', 'SELECT'],
                    'comments': ['-- Test comment'],
                    'tables': ['datadog', 'datadog2'],
                },
            },
        ),
        (
            json.dumps(
                {
                    'query': 'COMMIT',
                    'metadata': {'tables_csv': '', 'commands': ['COMMIT'], 'comments': None},
                }
            ),
            {
                'query': 'COMMIT',
                'metadata': {'commands': ['COMMIT'], 'comments': None, 'tables': None},
            },
        ),
        (
            'SELECT * FROM datadog',
            {
                'query': 'SELECT * FROM datadog',
                'metadata': {},
            },
        ),
        (
            'SELECT * FROM datadog',
            {
                'query': 'SELECT * FROM datadog',
                'metadata': {},
            },
        ),
    ],
)
def test_obfuscate_sql_with_metadata(obfuscator_return_value, expected_value):
    def _mock_obfuscate_sql(query, options=None):
        return obfuscator_return_value

    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = _mock_obfuscate_sql
        statement = obfuscate_sql_with_metadata('query here does not matter', None)
        assert statement == expected_value

    # Check that it can handle None values
    statement = obfuscate_sql_with_metadata(None)
    assert statement['query'] == ''
    assert statement['metadata'] == {}


@pytest.mark.parametrize(
    "input_query,expected_query,replace_null_character",
    [
        (
            "SELECT * FROM randomtable where name = '123\x00'",
            "SELECT * FROM randomtable where name = '123'",
            True,
        ),
        (
            "SELECT * FROM randomtable where name = '123\x00'",
            "SELECT * FROM randomtable where name = '123\x00'",
            False,
        ),
    ],
)
def test_obfuscate_sql_with_metadata_replace_null_character(input_query, expected_query, replace_null_character):
    def _mock_obfuscate_sql(query, options=None):
        return json.dumps({'query': query, 'metadata': {}})

    # Check that it can handle null characters
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = _mock_obfuscate_sql
        statement = obfuscate_sql_with_metadata(input_query, None, replace_null_character=replace_null_character)
        assert statement['query'] == expected_query


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
    limit_time = 1.0
    sleep_time = 0.9  # just below what the rate limit should hit to buffer before cancelling the loop

    job = TestJob(AgentCheck(), rate_limit=rate_limit)
    job.run_job_loop([])

    time.sleep(sleep_time)
    max_collections = int(rate_limit * limit_time) + 1
    job.cancel()

    metrics = aggregator.metrics("dbm.async_job_test.run_job")
    assert max_collections / 2.0 <= len(metrics) <= max_collections


def test_dbm_async_job_inactive_stop(aggregator):
    job = TestJob(AgentCheck(), rate_limit=10, min_collection_interval=1)
    job.run_job_loop([])
    job._job_loop_future.result()
    aggregator.assert_metric("dd.test-dbms.async_job.inactive_stop", tags=['job:test-job'])


@pytest.mark.parametrize(
    "input",
    [
        pytest.param({"foo": "bar"}, id='dict'),
        pytest.param({"foo": "bar", "baz": 1}, id='dict-with-multiple-keys'),
        pytest.param({"foo": "bar", "baz": 1, "qux": {"quux": "corge"}}, id='nested-dict'),
        pytest.param({"foo": b'bar'}, id='dict-with-bytes'),
        pytest.param({"foo": decimal.Decimal("1.0")}, id='dict-with-decimal'),
        pytest.param({"foo": datetime.datetime(2020, 1, 1, 0, 0, 0)}, id='dict-with-datetime'),
        pytest.param({"foo": datetime.date(2020, 1, 1)}, id='dict-with-date'),
        pytest.param({"foo": IPv4Address(u"192.168.1.1")}, id='dict-with-IPv4Address'),
    ],
)
def test_default_json_event_encoding(input):
    # assert that the default json event encoding can handle all defined types without raising TypeError
    assert json.dumps(input, default=default_json_event_encoding)


def test_tracked_query(aggregator):
    with mock.patch('time.time', side_effect=[100, 101]):
        with tracked_query(
            check=AgentCheck(name="testcheck"),
            operation="test_query",
            tags=["test:tag"],
        ):
            pass
        aggregator.assert_metric(
            "dd.testcheck.operation.time", tags=["test:tag", "operation:test_query"], count=1, value=1000.0
        )
