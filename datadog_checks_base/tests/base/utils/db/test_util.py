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
from datadog_checks.base.utils.db.health import Health, HealthEvent, HealthStatus
from datadog_checks.base.utils.db.utils import (
    ConstantRateLimiter,
    DBMAsyncJob,
    RateLimitingTTLCache,
    TagManager,
    TagType,
    default_json_event_encoding,
    get_agent_host_tags,
    obfuscate_sql_with_metadata,
    resolve_db_host,
    tracked_query,
)
from datadog_checks.base.utils.format import json


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
        ("postgres.svc.local", "some-pod", "postgres.svc.local"),
    ],
)
def test_resolve_db_host(db_host, agent_hostname, want):
    datadog_agent.set_hostname(agent_hostname)
    assert resolve_db_host(db_host) == want
    datadog_agent.reset_hostname()


def test_get_agent_host_tags():
    # happy path
    datadog_agent._set_host_tags(
        {
            "system": ["tag1:value1", "tag2:value2"],
            "google cloud platform": ["tag3:value3", "tag4:value4"],
        }
    )
    want = ["tag1:value1", "tag2:value2", "tag3:value3", "tag4:value4"]
    got = get_agent_host_tags()
    assert got == want

    # invalid tags json
    datadog_agent._set_host_tags("{")
    with pytest.raises(ValueError):
        get_agent_host_tags()

    # invalid tags value
    datadog_agent._set_host_tags(
        {
            "system": ["tag1:value1", "tag2:value2"],
            "google cloud platform": "tag3:value3",
        }
    )
    with pytest.raises(ValueError):
        get_agent_host_tags()

    # clean up
    datadog_agent._reset_host_tags()


def test_constant_rate_limiter():
    rate_limit = 8
    test_duration_s = 0.5
    ratelimiter = ConstantRateLimiter(rate_limit)
    start = time.time()
    sleep_count = 0
    while time.time() - start < test_duration_s:
        ratelimiter.update_last_time_and_sleep()
        sleep_count += 1
    max_expected_count = rate_limit * test_duration_s
    assert max_expected_count - 1 <= sleep_count <= max_expected_count + 1


def test_constant_rate_limiter_shell_execute():
    rate_limit = 1
    ratelimiter = ConstantRateLimiter(rate_limit)
    assert ratelimiter.shall_execute()
    ratelimiter.update_last_time()
    assert not ratelimiter.shall_execute()
    time.sleep(1)
    assert ratelimiter.shall_execute()


def test_ratelimiting_ttl_cache():
    ttl = 2
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




def test_dbm_async_job_missed_collection_interval(aggregator):
    check = AgentCheck()
    health = Health(check)
    check.health = health    
    job = JobForTesting(check, min_collection_interval=1, job_execution_time=3)
    job.run_job_loop([])
    # Sleep longer than the target collection interval
    time.sleep(1.5)
    # Simulate the check calling run_job_loop on its run
    job.run_job_loop([])
    # One more run to check the cooldown
    job.run_job_loop([])
    job.cancel()

    events = aggregator.get_event_platform_events("dbm-health")

    # The cooldown should prevent the event from being submitted again
    assert len(events) == 1
    health_event = events[0]
    print(health_event)
    assert health_event['name'] == HealthEvent.MISSED_COLLECTION.value
    assert health_event['status'] == HealthStatus.WARNING.value
    assert health_event['data']['job_name'] == 'test-job'
    # This might be flakey, we can adjust the timing if needed
    assert health_event['data']['elapsed_time'] > 1500
    assert health_event['data']['elapsed_time'] < 2000


class DBExceptionForTests(BaseException):
    pass


@pytest.mark.parametrize(
    "obfuscator_return_value,expected_value",
    [
        (
            json.encode(
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
            json.encode(
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
            json.encode(
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
        return json.encode({'query': query, 'metadata': {}})

    # Check that it can handle null characters
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = _mock_obfuscate_sql
        statement = obfuscate_sql_with_metadata(input_query, None, replace_null_character=replace_null_character)
        assert statement['query'] == expected_query


class JobForTesting(DBMAsyncJob):
    def __init__(
        self,
        check,
        run_sync=False,
        enabled=True,
        rate_limit=10,
        min_collection_interval=15,
        job_execution_time=0,
        max_sleep_chunk_s=5,
    ):
        super(JobForTesting, self).__init__(
            check,
            run_sync=run_sync,
            enabled=enabled,
            expected_db_exceptions=(DBExceptionForTests,),
            min_collection_interval=min_collection_interval,
            config_host="test-host",
            dbms="test-dbms",
            rate_limit=rate_limit,
            max_sleep_chunk_s=max_sleep_chunk_s,
            job_name="test-job",
            shutdown_callback=self.test_shutdown,
        )
        self._job_execution_time = job_execution_time
        self.count_executed = 0

    def test_shutdown(self):
        self._check.count("dbm.async_job_test.shutdown", 1)

    def run_job(self):
        self._check.count("dbm.async_job_test.run_job", 1)
        self.count_executed += 1
        time.sleep(self._job_execution_time)


def test_dbm_async_job():
    check = AgentCheck()
    JobForTesting(check)


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.mark.parametrize("enabled", [True, False])
def test_dbm_async_job_enabled(enabled):
    check = AgentCheck()
    job = JobForTesting(check, enabled=enabled)
    job.run_job_loop([])
    if enabled:
        assert job._job_loop_future is not None
        job.cancel()
        job._job_loop_future.result()
    else:
        assert job._job_loop_future is None


def test_dbm_async_job_cancel(aggregator):
    job = JobForTesting(AgentCheck())
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


def test_dbm_async_job_cancel_returns_early_on_long_sleep():
    # Configure a very low rate so the sleep interval would be ~60s without cancellation
    job = JobForTesting(AgentCheck(), rate_limit=1 / 60.0, max_sleep_chunk_s=0.1)
    job.run_job_loop([])
    # Allow the thread to start and enter the sleep window
    time.sleep(0.2)
    start = time.time()
    job.cancel()
    # Should finish well before the full ~10s timeout and 60s rate-limiter interval
    job._job_loop_future.result(timeout=10)
    elapsed = time.time() - start
    assert elapsed < 10, "Job did not cancel before the full sleep interval"


def test_dbm_async_job_run_sync(aggregator):
    job = JobForTesting(AgentCheck(), run_sync=True)
    job.run_job_loop([])
    assert job._job_loop_future is None
    aggregator.assert_metric("dbm.async_job_test.run_job")


def test_dbm_sync_job_rate_limit(aggregator):
    rate_limit = 1
    job = JobForTesting(AgentCheck(), run_sync=True, rate_limit=rate_limit)
    for _ in range(0, 2):
        # 2 runs out of 3 should be skipped
        job.run_job_loop([])
    time.sleep(1 / rate_limit)
    # this run should be allowed
    job.run_job_loop([])
    assert job.count_executed == 2


def test_dbm_sync_long_job_rate_limit(aggregator):
    collection_interval = 0.5
    rate_limit = 1 / collection_interval
    job = JobForTesting(AgentCheck(), run_sync=True, rate_limit=rate_limit, job_execution_time=2 * collection_interval)
    job.run_job_loop([])
    # despite jobs being executed one after another rate limiter shouldn't block execution
    # as jobs are slower than the collection interval
    job.run_job_loop([])
    assert job.count_executed == 2


def test_dbm_async_job_rate_limit(aggregator):
    # test the main collection loop rate limit
    rate_limit = 10
    limit_time = 1.0
    sleep_time = 0.9  # just below what the rate limit should hit to buffer before cancelling the loop

    job = JobForTesting(AgentCheck(), rate_limit=rate_limit)
    job.run_job_loop([])

    time.sleep(sleep_time)
    max_collections = int(rate_limit * limit_time) + 1
    job.cancel()

    metrics = aggregator.metrics("dbm.async_job_test.run_job")
    assert max_collections / 2.0 <= len(metrics) <= max_collections


def test_dbm_async_job_inactive_stop(aggregator):
    job = JobForTesting(AgentCheck(), rate_limit=10, min_collection_interval=1)
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
        pytest.param({"foo": IPv4Address("192.168.1.1")}, id='dict-with-IPv4Address'),
    ],
)
def test_default_json_event_encoding(input):
    # assert that the default json event encoding can handle all defined types without raising TypeError
    assert json.encode(input, default=default_json_event_encoding)


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


class TestTagManager:
    def test_init(self):
        """Test initialization of TagManager"""
        tag_manager = TagManager()
        assert tag_manager._tags == {}
        assert tag_manager._cached_tag_list is None
        assert tag_manager._keyless == TagType.KEYLESS

    @pytest.mark.parametrize(
        'key,value,expected_tags',
        [
            ('test_key', 'test_value', {'test_key': ['test_value']}),
            (None, 'test_value', {TagType.KEYLESS: ['test_value']}),
        ],
    )
    def test_set_tag(self, key, value, expected_tags):
        """Test setting tags with various combinations of key and value"""
        tag_manager = TagManager()
        tag_manager.set_tag(key, value)
        assert tag_manager._tags == expected_tags
        assert tag_manager._cached_tag_list is None

    def test_set_tag_existing_key_append(self):
        """Test appending a value to an existing key"""
        tag_manager = TagManager()
        tag_manager.set_tag('test_key', 'value1')
        tag_manager.set_tag('test_key', 'value2')
        assert tag_manager._tags == {'test_key': ['value1', 'value2']}
        assert tag_manager._cached_tag_list is None

    def test_set_tag_existing_key_replace(self):
        """Test replacing values for an existing key"""
        tag_manager = TagManager()
        tag_manager.set_tag('test_key', 'value1')
        tag_manager.set_tag('test_key', 'value2', replace=True)
        assert tag_manager._tags == {'test_key': ['value2']}
        assert tag_manager._cached_tag_list is None

    def test_set_tag_duplicate_value(self):
        """Test setting a duplicate value for a key"""
        tag_manager = TagManager()
        tag_manager.set_tag('test_key', 'test_value')
        tag_manager.set_tag('test_key', 'test_value')
        assert tag_manager._tags == {'test_key': ['test_value']}
        assert tag_manager._cached_tag_list is None

    @pytest.mark.parametrize(
        'key,values,delete_key,delete_value,expected_tags,description',
        [
            (
                'test_key',
                ['value1', 'value2'],
                'test_key',
                'value1',
                {'test_key': ['value2']},
                'deleting specific value',
            ),
            ('test_key', ['value1', 'value2'], 'test_key', None, {}, 'deleting all values for key'),
            (
                None,
                ['value1', 'value2'],
                None,
                'value1',
                {TagType.KEYLESS: ['value2']},
                'deleting specific keyless value',
            ),
            (None, ['value1', 'value2'], None, None, {}, 'deleting all keyless values'),
        ],
    )
    def test_delete_tag(self, key, values, delete_key, delete_value, expected_tags, description):
        """Test various tag deletion scenarios"""
        tag_manager = TagManager()
        # Set up initial tags
        for value in values:
            tag_manager.set_tag(key, value)

        # Generate initial cache
        tag_manager.get_tags()
        assert tag_manager._cached_tag_list is not None

        # Perform deletion
        assert tag_manager.delete_tag(delete_key, delete_value)

        # Verify cache is invalidated
        assert tag_manager._cached_tag_list is None

        # Verify internal state
        assert tag_manager._tags == expected_tags

    @pytest.mark.parametrize(
        'initial_tags,tag_list,replace,expected_tags,description',
        [
            (
                [],
                ['key1:value1', 'key2:value2', 'value3'],
                False,
                ['key1:value1', 'key2:value2', 'value3'],
                'setting new tags',
            ),
            (
                ['key1:old_value', 'key2:old_value', 'keyless1'],
                ['key1:new_value', 'key3:new_value', 'keyless2'],
                True,
                ['key1:new_value', 'key3:new_value', 'keyless2'],
                'replacing all existing tags with new ones',
            ),
            (
                ['key1:old_value'],
                ['key1:new_value'],
                False,
                ['key1:new_value', 'key1:old_value'],
                'appending to existing tags',
            ),
            ([], ['key1:value1', 'key1:value1'], False, ['key1:value1'], 'setting duplicate values'),
            (
                [],
                ['key1:value1', 'value2', 'key2:value3'],
                False,
                ['key1:value1', 'key2:value3', 'value2'],
                'setting mixed format tags',
            ),
        ],
    )
    def test_set_tags_from_list(self, initial_tags, tag_list, replace, expected_tags, description):
        """Test various tag list setting scenarios"""
        tag_manager = TagManager()
        # Set up initial tags if any
        for tag in initial_tags:
            if ':' in tag:
                key, value = tag.split(':', 1)
                tag_manager.set_tag(key, value)
            else:
                tag_manager.set_tag(None, tag)

        # Generate cache to ensure it exists
        _ = tag_manager.get_tags()
        assert tag_manager._cached_tag_list is not None

        tag_manager.set_tags_from_list(tag_list, replace=replace)

        # Verify cache was invalidated when needed
        if replace:
            assert tag_manager._cached_tag_list is None

        # Verify final state
        assert sorted(tag_manager.get_tags()) == sorted(expected_tags)

    def test_get_tags_empty(self):
        tag_manager = TagManager()
        assert tag_manager.get_tags() == []

    @pytest.mark.parametrize(
        'regular_tags,expected_tags',
        [
            ({'key1': ['value1']}, ['key1:value1']),
            ({'key1': ['value1', 'value2']}, ['key1:value1', 'key1:value2']),
        ],
    )
    def test_get_tags(self, regular_tags, expected_tags):
        """Test getting tags with various combinations of regular tags"""
        tag_manager = TagManager()

        # Set up regular tags
        for key, values in regular_tags.items():
            for value in values:
                tag_manager.set_tag(key, value)

        # Verify tags
        assert sorted(tag_manager.get_tags()) == sorted(expected_tags)

    def test_cache_management(self):
        """Test that tag caches are properly managed"""
        tag_manager = TagManager()

        # Set initial tags
        tag_manager.set_tag('regular_key', 'regular_value')

        # First call should generate cache
        _ = tag_manager.get_tags()
        assert tag_manager._cached_tag_list is not None

        # Modify regular tags
        tag_manager.set_tag('regular_key2', 'regular_value2')
        assert tag_manager._cached_tag_list is None

        # Verify all tags are included
        second_result = tag_manager.get_tags()
        assert sorted(second_result) == sorted(['regular_key:regular_value', 'regular_key2:regular_value2'])

    def test_get_tags_mutation(self):
        """Test that modifying the returned list from get_tags() does not affect the internal cache"""
        tag_manager = TagManager()
        tag_manager.set_tag('test_key', 'test_value')

        # Get the tags list
        tags = tag_manager.get_tags()
        assert tags == ['test_key:test_value']

        # Modify the returned list
        tags.append('modified_tag')
        tags[0] = 'modified_existing_tag'

        # Get tags again - should be unchanged
        new_tags = tag_manager.get_tags()
        assert new_tags == ['test_key:test_value']
        assert new_tags != tags  # The lists should be different objects

    # Normalization tests
    def mock_tag_normalizer(self, tag):
        """Mock normalizer that replaces spaces and hyphens with underscores and lowercases"""
        return tag.replace(' ', '_').replace('-', '_').lower()

    def test_init_with_normalizer(self):
        """Test initialization of TagManager with normalizer"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)
        assert tag_manager._normalizer == self.mock_tag_normalizer
        assert tag_manager._tags == {}
        assert tag_manager._cached_tag_list is None

    def test_set_tag_with_normalization(self):
        """Test setting tags with normalization enabled"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        # Test with normalize=True - only value should be normalized, not key
        tag_manager.set_tag('test-key', 'value with spaces', normalize=True)
        assert tag_manager._tags == {'test-key': ['value_with_spaces']}

        # Test keyless tag normalization
        tag_manager.set_tag(None, 'keyless value', normalize=True)
        assert TagType.KEYLESS in tag_manager._tags
        assert tag_manager._tags[TagType.KEYLESS] == ['keyless_value']

    def test_set_tag_without_normalization(self):
        """Test setting tags without normalization"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        # Test with normalize=False
        tag_manager.set_tag('test-key', 'value with spaces', normalize=False)
        assert tag_manager._tags == {'test-key': ['value with spaces']}

        # Test with no normalize parameter (should default to False)
        tag_manager.set_tag('another-key', 'another value')
        assert tag_manager._tags == {'test-key': ['value with spaces'], 'another-key': ['another value']}

    def test_set_tags_from_list_with_normalization(self):
        """Test setting tags from list with normalization enabled"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        tag_list = ['env:prod-test', 'service:web app', 'keyless-tag']
        tag_manager.set_tags_from_list(tag_list, normalize=True)

        expected_tags = sorted(['env:prod_test', 'service:web_app', 'keyless_tag'])
        assert sorted(tag_manager.get_tags()) == expected_tags

    def test_set_tags_from_list_without_normalization(self):
        """Test setting tags from list without normalization"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        tag_list = ['env:prod-test', 'service:web app', 'keyless-tag']
        tag_manager.set_tags_from_list(tag_list, normalize=False)

        expected_tags = sorted(['env:prod-test', 'service:web app', 'keyless-tag'])
        assert sorted(tag_manager.get_tags()) == expected_tags

    def test_delete_tag_with_normalization(self):
        """Test deleting tags with normalization enabled"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        # Set tag with normalization (only value normalized)
        tag_manager.set_tag('test-key', 'value with spaces', normalize=True)
        assert 'test-key' in tag_manager._tags
        assert tag_manager._tags['test-key'] == ['value_with_spaces']

        # Delete with normalization - should find the normalized value
        result = tag_manager.delete_tag('test-key', 'value with spaces', normalize=True)
        assert result is True
        assert tag_manager._tags == {}

    def test_delete_tag_without_normalization(self):
        """Test deleting tags without normalization"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        # Set tag without normalization
        tag_manager.set_tag('test-key', 'value with spaces', normalize=False)
        assert tag_manager._tags == {'test-key': ['value with spaces']}

        # Delete without normalization
        result = tag_manager.delete_tag('test-key', 'value with spaces', normalize=False)
        assert result is True
        assert tag_manager._tags == {}

    def test_delete_tag_normalization_mismatch(self):
        """Test that deletion fails when normalization doesn't match storage"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        # Set tag with normalization (only value normalized)
        tag_manager.set_tag('test-key', 'value with spaces', normalize=True)
        assert tag_manager._tags == {'test-key': ['value_with_spaces']}

        # Try to delete without normalization - should fail
        result = tag_manager.delete_tag('test-key', 'value with spaces', normalize=False)
        assert result is False
        assert tag_manager._tags == {'test-key': ['value_with_spaces']}

        # Delete with normalization - should succeed
        result = tag_manager.delete_tag('test-key', 'value with spaces', normalize=True)
        assert result is True
        assert tag_manager._tags == {}

    def test_delete_entire_key_with_normalization(self):
        """Test deleting entire key with normalization"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        # Set multiple values for a key with normalization (only values normalized)
        tag_manager.set_tag('test-key', 'value1', normalize=True)
        tag_manager.set_tag('test-key', 'value2', normalize=True)
        assert tag_manager._tags == {'test-key': ['value1', 'value2']}

        # Delete entire key - key doesn't need normalization
        result = tag_manager.delete_tag('test-key', normalize=True)
        assert result is True
        assert tag_manager._tags == {}

    def test_normalization_with_no_normalizer(self):
        """Test that normalize parameter is ignored when no normalizer is provided"""
        tag_manager = TagManager()  # No normalizer

        # Should work the same regardless of normalize parameter
        tag_manager.set_tag('test-key', 'value with spaces', normalize=True)
        assert tag_manager._tags == {'test-key': ['value with spaces']}

        tag_manager.set_tags_from_list(['env:prod-test'], normalize=True)
        expected_tags = sorted(['test-key:value with spaces', 'env:prod-test'])
        assert sorted(tag_manager.get_tags()) == expected_tags

        # Delete should also work
        result = tag_manager.delete_tag('test-key', 'value with spaces', normalize=True)
        assert result is True

    def test_case_sensitivity_normalization(self):
        """Test that normalization handles case sensitivity correctly (only values normalized)"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        # Test only value gets normalized, key assumed to be lowercase already
        tag_manager.set_tag('test_key', 'UPPERCASE-VALUE', normalize=True)
        assert tag_manager._tags == {'test_key': ['uppercase_value']}

        # Test mixed case value normalization
        tag_manager.set_tag('another_key', 'SoMe VaLuE', normalize=True)
        assert 'another_key' in tag_manager._tags
        assert tag_manager._tags['another_key'] == ['some_value']

        # Verify final tags - keys lowercase, values normalized
        expected_tags = sorted(['test_key:uppercase_value', 'another_key:some_value'])
        assert sorted(tag_manager.get_tags()) == expected_tags

        # Test deletion with case sensitivity
        result = tag_manager.delete_tag('test_key', 'UPPERCASE-VALUE', normalize=True)
        assert result is True
        assert tag_manager._tags == {'another_key': ['some_value']}

    def test_case_sensitivity_in_tag_list(self):
        """Test case sensitivity normalization in tag lists"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        tag_list = ['env:PRODUCTION', 'service:WEB-APP', 'datacenter:US-EAST-1', 'KEYLESS-TAG-UPPERCASE']
        tag_manager.set_tags_from_list(tag_list, normalize=True)

        # When normalize_tag is applied to the full tag string, it normalizes everything
        expected_tags = sorted(['env:production', 'service:web_app', 'datacenter:us_east_1', 'keyless_tag_uppercase'])
        assert sorted(tag_manager.get_tags()) == expected_tags

    def test_case_sensitivity_without_normalization(self):
        """Test that case sensitivity is preserved without normalization"""
        tag_manager = TagManager(normalizer=self.mock_tag_normalizer)

        # Set tags without normalization - case should be preserved
        tag_manager.set_tag('test_key', 'UPPERCASE-VALUE', normalize=False)
        assert tag_manager._tags == {'test_key': ['UPPERCASE-VALUE']}

        # Set tag list without normalization - case should be preserved
        tag_list = ['env:PRODUCTION', 'KEYLESS-TAG-UPPERCASE']
        tag_manager.set_tags_from_list(tag_list, normalize=False)

        expected_tags = sorted(['test_key:UPPERCASE-VALUE', 'env:PRODUCTION', 'KEYLESS-TAG-UPPERCASE'])
        assert sorted(tag_manager.get_tags()) == expected_tags
