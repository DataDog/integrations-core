# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import concurrent
import json
import os
import time
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy

import mock
import pytest
from dateutil import parser

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.sqlserver import SQLServer

from .common import CHECK_NAME
from .conftest import DEFAULT_TIMEOUT

try:
    import pyodbc
except ImportError:
    pyodbc = None

ACTIVITY_JSON_PLANS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "activity")


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    # set a very small collection interval so the tests go fast
    instance_docker['query_activity'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.1,
        'tx_collection_interval': 0.1,
    }
    # do not need query_metrics for these tests
    instance_docker['query_metrics'] = {'enabled': False}
    return copy(instance_docker)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize("use_autocommit", [True, False])
def test_collect_load_activity(aggregator, instance_docker, dd_run_check, dbm_instance, use_autocommit):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    query = "SELECT * FROM ϑings"
    blocking_query = "INSERT INTO ϑings WITH (TABLOCK, HOLDLOCK) (name) VALUES ('puppy')"
    fred_conn = _get_conn_for_user(instance_docker, "fred", _autocommit=use_autocommit)
    bob_conn = _get_conn_for_user(instance_docker, "bob")

    def run_test_query(c, q):
        cur = c.cursor()
        cur.execute("USE {}".format("datadog_test"))
        cur.execute(q)

    # bob's query blocks until the tx is completed,
    # so it needs to be run asynchronously
    executor = concurrent.futures.ThreadPoolExecutor(1)
    executor.submit(run_test_query, bob_conn, blocking_query)
    # fred's query will get blocked by bob, so it needs
    # to be run asynchronously
    executor.submit(run_test_query, fred_conn, query)
    # run the check
    dd_run_check(check)
    # commit and close both transactions
    bob_conn.commit()
    bob_conn.close()
    fred_conn.close()

    expected_instance_tags = set(dbm_instance.get('tags', []))

    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    assert len(dbm_activity) == 1, "should have collected exactly one dbm-activity payload"
    event = dbm_activity[0]
    # validate common host fields
    assert event['host'] == "stubbed.hostname", "wrong hostname"
    assert event['dbm_type'] == "activity", "wrong dbm_type"
    assert event['ddsource'] == "sqlserver", "wrong source"
    assert event['ddagentversion'], "missing ddagentversion"
    assert set(event['ddtags']) == expected_instance_tags, "wrong instance tags activity"
    assert type(event['collection_interval']) in (float, int), "invalid collection_interval"

    # fred's query is the only one present in dm_exec_requests
    # and so the load query should catch it first
    assert len(event['sqlserver_activity']) == 2, "should have collected exactly two activity rows"
    blocked_row = event['sqlserver_activity'][0]
    # assert the data that was collected is correct
    assert blocked_row['user_name'] == "fred", "incorrect user_name"
    assert blocked_row['session_status'] == "running", "incorrect session_status"
    assert blocked_row['blocking_session_id'], "missing blocking_session_id"
    assert blocked_row['text'] == query, "incorrect blocked query"
    assert_common_fields(blocked_row, "query_start")
    # if autocommit is false, we should see fred's query show up in both tables,
    # so we should join tx information to fred's activity row
    if not use_autocommit:
        assert blocked_row["transaction_begin_time"], "missing transaction_begin_time on blocked query"
        assert blocked_row["transaction_type"], "missing transaction_type on blocked query"
        assert blocked_row["transaction_id"], "missing transaction_id on blocked query"

    # the second row in sqlserver_activity should be bob's open
    # idle tx, which is blocking fred's ability to query the ϑings table
    blocking_row = event['sqlserver_activity'][1]
    # assert the data that was collected is correct
    assert blocking_row['user_name'] == "bob", "incorrect user_name"
    assert blocking_row['session_status'] == "sleeping", "incorrect session_status"
    assert (
        blocking_row['id'] == blocked_row['blocking_session_id']
    ), "blocking id does not match blocked blocking_session_id"
    assert blocking_row['text'] == blocking_query, "incorrect blocking query"
    assert_common_fields(blocking_row, "transaction_begin_time")

    # assert connections collection
    assert len(event['sqlserver_connections']) > 0
    b_conn = None
    f_conn = None
    for conn in event['sqlserver_connections']:
        if conn['user_name'] == "bob":
            b_conn = conn
        if conn['user_name'] == "fred":
            f_conn = conn
    assert b_conn is not None
    assert f_conn is not None
    assert b_conn['connections'] == 1
    assert b_conn['status'] == "sleeping"
    assert f_conn['connections'] == 1
    assert f_conn['status'] == "running"

    # internal debug metrics
    aggregator.assert_metric(
        "dd.sqlserver.operation.time",
        tags=['agent_hostname:stubbed.hostname', 'operation:collect_activity']
        + _expected_dbm_instance_tags(dbm_instance),
    )


def assert_common_fields(row, start_key):
    assert row['database_name'] == "datadog_test", "incorrect database_name"
    assert row['id'], "missing session id"
    assert row['now'], "missing current timestamp"
    assert row['last_request_start_time'], "missing last_request_start_time"
    assert row['now'], "missing current time"
    # assert that the current timestamp is being collected as an ISO timestamp with TZ info
    assert parser.isoparse(row['now']).tzinfo, "current timestamp not formatted correctly"
    assert row[start_key], "missing {}".format(start_key)
    assert parser.isoparse(row[start_key]).tzinfo, "{} timestamp not formatted correctly".format(start_key)


def new_time():
    return datetime.datetime(2021, 9, 23, 23, 21, 21, 669330)


def old_time():
    return datetime.datetime(2021, 9, 22, 22, 21, 21, 669330)


@pytest.mark.parametrize(
    "rows,expected_len",
    [
        [
            [
                {
                    'last_request_start_time': 'suspended',
                    'id': 1,
                    'text': "something",
                    'start_time': 2,
                    'query_start': new_time(),
                },
                {
                    'last_request_start_time': 'suspended',
                    'id': 2,
                    'text': "something",
                    'start_time': 2,
                    'query_start': old_time(),
                    'toobig': "shame" * 1000,
                },
            ],
            1,
        ],
        [
            [
                {'last_request_start_time': 'suspended', 'id': 1, 'text': "something", 'query_start': new_time()},
                {'last_request_start_time': 'suspended', 'id': 2, 'text': "something", 'query_start': old_time()},
            ],
            2,
        ],
        [
            [
                {
                    'last_request_start_time': 'suspended',
                    'id': 1,
                    'text': "something",
                    'query_start': new_time(),
                    'toobig': "shame" * 1000,
                },
            ],
            0,
        ],
    ],
)
def test_truncate_on_max_size_bytes(dbm_instance, datadog_agent, rows, expected_len):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = "something"
        result_rows = check.activity._normalize_queries_and_filter_rows(rows, 1000)
        assert len(result_rows) == expected_len


@pytest.mark.parametrize(
    "file",
    [
        "single_activity.json",
        "many_activity.json",
    ],
)
def test_get_estimated_row_size_bytes(dbm_instance, file):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    test_activity = _load_test_activity_json(file)
    actual_size = len(json.dumps(test_activity, default=default_json_event_encoding))
    computed_size = 0
    for a in test_activity:
        computed_size += check.activity._get_estimated_row_size_bytes(a)

    assert abs((actual_size - computed_size) / float(actual_size)) <= 0.10


def test_activity_collection_rate_limit(aggregator, dd_run_check, dbm_instance):
    # test the activity collection loop rate limit
    collection_interval = 0.1
    dbm_instance['query_activity']['collection_interval'] = collection_interval
    dbm_instance['query_activity']['run_sync'] = False
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    sleep_time = 1
    time.sleep(sleep_time)
    max_collections = int(1 / collection_interval * sleep_time) + 1
    check.cancel()
    metrics = aggregator.metrics("dd.sqlserver.activity.collect_activity.payload_size")
    assert max_collections / 2.0 <= len(metrics) <= max_collections


def test_tx_activity_collection_rate_limit(aggregator, dd_run_check, dbm_instance):
    # test the activity collection loop rate limit
    collection_interval = 0.1
    tx_collection_interval = 0.2  # double the main loop
    dbm_instance['query_activity']['collection_interval'] = collection_interval
    dbm_instance['query_activity']['tx_collection_interval'] = tx_collection_interval
    dbm_instance['query_activity']['run_sync'] = False
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    sleep_time = 1
    time.sleep(sleep_time)
    max_tx_activity_collections = int(1 / tx_collection_interval * sleep_time) + 1
    check.cancel()
    activity_metrics = aggregator.metrics("dd.sqlserver.activity.get_tx_activity.tx_rows")
    assert max_tx_activity_collections / 2.0 <= len(activity_metrics) <= max_tx_activity_collections


def _load_test_activity_json(filename):
    with open(os.path.join(ACTIVITY_JSON_PLANS_DIR, filename), 'r') as f:
        return json.load(f)


def _get_conn_for_user(instance_docker, user, _autocommit=False):
    # Make DB connection
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};'.format(
        instance_docker['driver'], instance_docker['host'], user, "Password12!"
    )
    conn = pyodbc.connect(conn_str, timeout=DEFAULT_TIMEOUT, autocommit=_autocommit)
    conn.timeout = DEFAULT_TIMEOUT
    return conn


def _expected_dbm_instance_tags(dbm_instance):
    return dbm_instance['tags']


@pytest.mark.parametrize("activity_enabled", [True, False])
def test_async_job_enabled(dd_run_check, dbm_instance, activity_enabled):
    dbm_instance['query_activity'] = {'enabled': activity_enabled, 'run_sync': False}
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.cancel()
    if activity_enabled:
        assert check.activity._job_loop_future is not None
        check.activity._job_loop_future.result()
    else:
        assert check.activity._job_loop_future is None


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_async_job_inactive_stop(aggregator, dd_run_check, dbm_instance):
    dbm_instance['query_activity']['run_sync'] = False
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.activity._job_loop_future.result()
    aggregator.assert_metric(
        "dd.sqlserver.async_job.inactive_stop",
        tags=['job:query-activity'] + _expected_dbm_instance_tags(dbm_instance),
        hostname='',
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_async_job_cancel_cancel(aggregator, dd_run_check, dbm_instance):
    dbm_instance['query_activity']['run_sync'] = False
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.cancel()
    # wait for it to stop and make sure it doesn't throw any exceptions
    check.activity._job_loop_future.result()
    assert not check.activity._job_loop_future.running(), "activity thread should be stopped"
    # if the thread doesn't start until after the cancel signal is set then the db connection will never
    # be created in the first place
    aggregator.assert_metric(
        "dd.sqlserver.async_job.cancel",
        tags=_expected_dbm_instance_tags(dbm_instance) + ['job:query-activity'],
    )
