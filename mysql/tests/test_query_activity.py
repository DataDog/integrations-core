# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import concurrent.futures.thread
import json
import os
import time
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy
from datetime import datetime
from os import environ

import mock
import pymysql
import pytest
from packaging.version import parse as parse_version

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.mysql import MySql
from datadog_checks.mysql.activity import MySQLActivity
from datadog_checks.mysql.util import StatementTruncationState

from .common import CHECK_NAME, HOST, MYSQL_VERSION_PARSED, PORT

ACTIVITY_JSON_PLANS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "activity")


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.fixture
def dbm_instance(instance_complex):
    instance_complex['dbm'] = True
    # set a very small collection interval so the tests go fast
    instance_complex['query_activity'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.1,
    }
    instance_complex['query_metrics'] = {'enabled': False}
    instance_complex['query_samples'] = {'enabled': False}
    return copy(instance_complex)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "query,query_signature,expected_query_truncated",
    [
        (
            'SELECT id, name FROM testdb.users FOR UPDATE',
            'aca1be410fbadb61',
            StatementTruncationState.not_truncated.value,
        ),
        (
            'SELECT id, {} FROM testdb.users FOR UPDATE'.format(
                ", ".join("name as name{}".format(i) for i in range(254))
            ),
            '63bd1fd025c7f7fb'
            if MYSQL_VERSION_PARSED > parse_version('5.6') and environ.get('MYSQL_FLAVOR') != 'mariadb'
            else '4a12d7afe06cf40',
            StatementTruncationState.truncated.value,
        ),
    ],
)
def test_collect_activity(aggregator, dbm_instance, dd_run_check, query, query_signature, expected_query_truncated):
    check = MySql(CHECK_NAME, {}, [dbm_instance])

    blocking_query = 'SELECT id FROM testdb.users FOR UPDATE'

    def _run_query(conn, _query):
        conn.cursor().execute(_query)

    def _run_blocking(conn):
        conn.begin()
        conn.cursor().execute(blocking_query)

    bob_conn = _get_conn_for_user('bob')
    fred_conn = _get_conn_for_user('fred')

    executor = concurrent.futures.thread.ThreadPoolExecutor(1)
    # bob's query will block until the TX is completed
    executor.submit(_run_blocking, bob_conn)
    # fred's query will get blocked by bob's TX
    executor.submit(_run_query, fred_conn, query)

    dd_run_check(check)
    bob_conn.commit()
    bob_conn.close()
    fred_conn.close()

    executor.shutdown()

    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    assert len(dbm_activity) == 1, "should have collected exactly one activity payload"

    activity = dbm_activity[0]
    assert activity['host'] == 'stubbed.hostname'
    assert activity['dbm_type'] == 'activity'
    assert activity['ddsource'] == 'mysql'
    assert activity['ddagentversion'], "missing agent version"
    assert set(activity['ddtags']) == {'tag1:value1', 'tag2:value2', 'port:13306'}
    assert type(activity['collection_interval']) in (float, int), "invalid collection_interval"

    assert activity['mysql_activity'], "should have at least one activity row"

    # The blocked row should be fred, which is currently blocked by bob's TX
    blocked_row = None
    for activity in dbm_activity:
        for row in activity['mysql_activity']:
            if row.get('query_signature') == query_signature:
                blocked_row = row
                break
    assert blocked_row is not None, "should have activity for fred's query"
    assert blocked_row['processlist_user'] == 'fred'
    assert blocked_row['processlist_command'] == 'Query'
    # The expected sql text for long queries depends on the mysql version/flavor which have different
    # sql text length limits
    expected_sql_text = (
        query[:1021] + '...'
        if len(query) > 1024
        and (MYSQL_VERSION_PARSED == parse_version('5.6') or environ.get('MYSQL_FLAVOR') == 'mariadb')
        else query[:4093] + '...'
        if len(query) > 4096
        else query
    )
    assert blocked_row['sql_text'] == expected_sql_text
    assert blocked_row['processlist_state'], "missing state"
    assert blocked_row['wait_event'] == 'wait/io/table/sql/handler'
    assert blocked_row['thread_id'], "missing thread id"
    assert blocked_row['processlist_id'], "missing processlist id"
    assert blocked_row['wait_timer_start'], "missing wait timer start"
    assert blocked_row['wait_timer_end'], "missing wait timer end"
    assert blocked_row['event_timer_start'], "missing event timer start"
    assert blocked_row['event_timer_end'], "missing event timer end"
    assert blocked_row['lock_time'], "missing lock time"
    assert blocked_row['query_truncated'] == expected_query_truncated


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "reported_hostname,expected_hostname",
    [
        (None, 'stubbed.hostname'),
        ('override.hostname', 'override.hostname'),
    ],
)
def test_activity_reported_hostname(aggregator, dbm_instance, dd_run_check, reported_hostname, expected_hostname):
    dbm_instance['reported_hostname'] = reported_hostname
    check = MySql(CHECK_NAME, {}, [dbm_instance])

    dd_run_check(check)
    dd_run_check(check)

    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    assert dbm_activity, "should have at least one activity sample"
    assert dbm_activity[0]['host'] == expected_hostname


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "metadata,expected_metadata_payload",
    [
        (
            {'tables_csv': 'testdb.users', 'commands': ['SELECT'], 'comments': ['-- Test comment']},
            {'tables': ['testdb.users'], 'commands': ['SELECT'], 'comments': ['-- Test comment']},
        ),
        (
            {'tables_csv': '', 'commands': None, 'comments': None},
            {'tables': None, 'commands': None, 'comments': None},
        ),
    ],
)
def test_activity_metadata(aggregator, dd_run_check, dbm_instance, datadog_agent, metadata, expected_metadata_payload):
    check = MySql(CHECK_NAME, {}, [dbm_instance])

    query = """
    -- Test comment
    SELECT id, name FROM testdb.users FOR UPDATE
    """
    query_signature = 'e7f7cb251194df29'

    def _run_test_query(conn, _query):
        conn.cursor().execute(_query)

    def _run_blocking(conn):
        conn.begin()
        conn.cursor().execute("SELECT id FROM testdb.users FOR UPDATE")

    def _obfuscate_sql(_query, options=None):
        return json.dumps({'query': _query, 'metadata': metadata})

    def _run_query_with_mock_obfuscator(conn, _query):
        # Execute the query with the mocked obfuscate_sql. The result should produce an event payload with the metadata.
        with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
            mock_agent.side_effect = _obfuscate_sql
            _run_test_query(conn, _query)

    bob_conn = _get_conn_for_user('bob')
    fred_conn = _get_conn_for_user('fred')

    executor = concurrent.futures.ThreadPoolExecutor(1)
    # bob's query blocks until the tx is completed
    executor.submit(_run_blocking, bob_conn)
    # fred's query will get blocked by bob, so it needs to be run asynchronously
    executor.submit(_run_query_with_mock_obfuscator, fred_conn, query)

    dd_run_check(check)
    bob_conn.commit()
    bob_conn.close()
    fred_conn.close()
    executor.shutdown()

    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    assert dbm_activity, "should have collected at least one activity"
    matching_activity = []
    for event in dbm_activity:
        for activity in event['mysql_activity']:
            if activity.get('query_signature') == query_signature:
                matching_activity.append(activity)
    assert len(matching_activity) == 1
    activity = matching_activity[0]
    assert activity['dd_tables'] == expected_metadata_payload['tables']
    assert activity['dd_commands'] == expected_metadata_payload['commands']
    assert activity['dd_comments'] == expected_metadata_payload['comments']


@pytest.mark.parametrize(
    "file",
    [
        "single_activity.json",
        "many_activity.json",
    ],
)
def test_get_estimated_row_size_bytes(dbm_instance, file):
    check = MySql(CHECK_NAME, {}, [dbm_instance])
    test_activity = _load_test_activity_json(file)
    actual_size = len(json.dumps(test_activity, default=check._query_activity._json_event_encoding))
    computed_size = 0
    for a in test_activity:
        computed_size += check._query_activity._get_estimated_row_size_bytes(a)
    assert abs((actual_size - computed_size) / float(actual_size)) <= 0.10


def _new_time():
    return _create_time_in_picoseconds(datetime(2021, 9, 23, 23, 21, 21, 669330))


def _old_time():
    return _create_time_in_picoseconds(datetime(2021, 9, 22, 22, 21, 21, 669330))


def _older_time():
    return _create_time_in_picoseconds(datetime(2021, 9, 20, 23, 21, 21, 669330))


def _create_time_in_picoseconds(date_obj):
    time_milli = int(time.mktime(date_obj.utctimetuple()) * 1000 + date_obj.microsecond / 1000)
    return int(round(time_milli * 1e9))


@pytest.mark.parametrize(
    "rows,expected_rows",
    [
        (
            [
                {'thread_id': 3, 'event_timer_start': _old_time()},
                {'thread_id': 1, 'event_timer_start': _new_time()},
                {'thread_id': 4},  # A row without the event timer uses the current time as the timestamp
                {'thread_id': 2, 'event_timer_start': _older_time()},
            ],
            [
                {'thread_id': 2, 'event_timer_start': _older_time()},
                {'thread_id': 3, 'event_timer_start': _old_time()},
                {'thread_id': 1, 'event_timer_start': _new_time()},
                {'thread_id': 4},
            ],
        )
    ],
)
def test_sort_key(dbm_instance, rows, expected_rows):
    check = MySql(CHECK_NAME, {}, [dbm_instance])
    output = sorted(rows, key=lambda r: check._query_activity._sort_key(r))
    assert output == expected_rows


@pytest.mark.parametrize(
    "rows,expected_len,expected_users",
    [
        [
            [
                {
                    "current_schema": "dog",
                    "processlist_command": "Query",
                    "processlist_user": "bob",
                    "sql_text": "something",
                    "event_timer_end": _new_time(),
                    "event_timer_start": _new_time(),
                    "thread_id": 1748,
                    "toobig": "shame" * int(MySQLActivity.MAX_PAYLOAD_BYTES),
                },
                {
                    "current_schema": "dog",
                    "processlist_command": "Query",
                    "processlist_user": "fred",
                    "sql_text": "something",
                    "event_timer_end": _old_time(),
                    "event_timer_start": _older_time(),
                    "thread_id": 48,
                },
                {
                    "current_schema": "dog",
                    "processlist_command": "Query",
                    "processlist_user": "bob",
                    "sql_text": "something",
                    "event_timer_end": _older_time(),
                    "event_timer_start": _old_time(),
                    "thread_id": 178,
                },
            ],
            2,
            ["fred", "bob"],
        ],
        [
            [
                {
                    "current_schema": "dog",
                    "processlist_command": "Query",
                    "processlist_user": "bob",
                    "sql_text": "something",
                    "event_timer_end": 354301626064000,
                    "event_timer_start": 353141155758000,
                    "thread_id": 1748,
                    "toobig": "shame" * int(MySQLActivity.MAX_PAYLOAD_BYTES),
                },
            ],
            0,
            [],
        ],
    ],
)
def test_truncate_on_max_size_bytes(dbm_instance, datadog_agent, rows, expected_len, expected_users):
    check = MySql(CHECK_NAME, {}, [dbm_instance])
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = "something"
        result_rows = check._query_activity._normalize_rows(rows)
        assert len(result_rows) == expected_len
        for index, user in enumerate(expected_users):
            assert result_rows[index]['processlist_user'] == user


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_activity_collection_rate_limit(aggregator, dd_run_check, dbm_instance):
    # test the activity collection loop rate limit
    aggregator.reset()
    collection_interval = 0.1
    dbm_instance['query_activity']['collection_interval'] = collection_interval
    dbm_instance['query_activity']['run_sync'] = False
    check = MySql(CHECK_NAME, {}, [dbm_instance])
    sleep_time = 1
    dd_run_check(check)
    time.sleep(sleep_time)
    check.cancel()
    max_collections = int(1 / collection_interval * sleep_time) + 1
    metrics = aggregator.metrics("dd.mysql.activity.collect_activity.payload_size")
    assert max_collections / 2.0 <= len(metrics) <= max_collections


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize("activity_enabled", [True, False])
def test_async_job_enabled(dd_run_check, dbm_instance, activity_enabled):
    dbm_instance['query_activity'] = {'enabled': activity_enabled, 'run_sync': False}
    check = MySql(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.cancel()
    if activity_enabled:
        assert check._query_activity._job_loop_future is not None
        check._query_activity._job_loop_future.result()
    else:
        assert check._query_activity._job_loop_future is None


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_async_job_inactive_stop(aggregator, dd_run_check, dbm_instance):
    dbm_instance['query_activity']['run_sync'] = False
    check = MySql(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check._query_activity._job_loop_future.result()
    aggregator.assert_metric(
        "dd.mysql.async_job.inactive_stop",
        tags=_expected_dbm_instance_tags(dbm_instance),
        hostname='',
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_async_job_cancel(aggregator, dd_run_check, dbm_instance):
    dbm_instance['query_activity']['run_sync'] = False
    check = MySql(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.cancel()
    # wait for it to stop and make sure it doesn't throw any exceptions
    check._query_activity._job_loop_future.result()
    assert not check._query_activity._job_loop_future.running(), "activity thread should be stopped"
    # if the thread doesn't start until after the cancel signal is set then the db connection will never
    # be created in the first place
    aggregator.assert_metric(
        "dd.mysql.async_job.cancel",
        tags=_expected_dbm_instance_tags(dbm_instance),
    )


def _expected_dbm_instance_tags(dbm_instance):
    return dbm_instance['tags'] + ['job:query-activity', 'port:{}'.format(PORT)]


def _get_conn_for_user(user, _autocommit=False):
    return pymysql.connect(host=HOST, port=PORT, user=user, password=user, autocommit=_autocommit)


def _load_test_activity_json(filename):
    with open(os.path.join(ACTIVITY_JSON_PLANS_DIR, filename), 'r') as f:
        return json.load(f)
