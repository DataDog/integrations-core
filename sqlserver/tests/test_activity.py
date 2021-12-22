# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import os
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy

import mock
import pytest
from dateutil import parser

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.sqlserver import SQLServer

from .common import CHECK_NAME
from .conftest import DEFAULT_TIMEOUT
from .utils import not_windows_ci, windows_ci

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
    instance_docker['query_activity'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    # do not need query_metrics for these tests
    instance_docker['query_metrics'] = {'enabled': False}
    return copy(instance_docker)


@pytest.fixture
def instance_sql_msoledb_dbm(instance_sql_msoledb):
    instance_sql_msoledb['dbm'] = True
    instance_sql_msoledb['min_collection_interval'] = 1
    instance_sql_msoledb['query_activity'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    # not needed for this test
    instance_sql_msoledb['query_metrics'] = {'enabled': False}
    instance_sql_msoledb['tags'] = ['optional:tag1']
    return instance_sql_msoledb


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collect_activity(aggregator, instance_docker, dd_run_check, dbm_instance):
    _run_test_collect_activity(aggregator, instance_docker, dd_run_check, dbm_instance)


@windows_ci
@pytest.mark.integration
def test_collect_activity_windows(aggregator, instance_docker, dd_run_check, instance_sql_msoledb_dbm):
    _run_test_collect_activity(aggregator, instance_docker, dd_run_check, instance_sql_msoledb_dbm)


def _run_test_collect_activity(aggregator, instance_docker, dd_run_check, dbm_instance):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    query = "SELECT * FROM ϑings"
    bob_conn = _get_conn_for_user(instance_docker, "bob")
    with bob_conn.cursor() as cursor:
        cursor.execute("USE {}".format("datadog_test"))
        cursor.execute(query)
        cursor.fetchall()

    fred_conn = _get_conn_for_user(instance_docker, "fred")
    with fred_conn.cursor() as cursor:
        cursor.execute("USE {}".format("datadog_test"))
        cursor.execute(query)
        cursor.fetchall()

    dd_run_check(check)
    fred_conn.close()  # close the open tx that belongs to fred
    dd_run_check(check)  # run check again
    expected_instance_tags = set(dbm_instance.get('tags', []))

    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    assert len(dbm_activity) == 2, "should have collected exactly two dbm-activity payloads"
    first = dbm_activity[0]
    # validate common host fields
    assert first['host'] == "stubbed.hostname", "wrong hostname"
    assert first['dbm_type'] == "activity", "wrong dbm_type"
    assert first['ddsource'] == "sqlserver", "wrong source"
    assert first['ddagentversion'], "missing ddagentversion"
    assert set(first['ddtags']) == expected_instance_tags, "wrong instance tags activity"
    assert type(first['collection_interval']) in (float, int), "invalid collection_interval"

    assert len(first['sqlserver_activity']) > 0
    # bob and fred's open transactions should have been
    # collected on first iteration. and bob's has been open longer
    # so it should come first in the payload
    first_users = [f['user_name'] for f in first['sqlserver_activity']]
    bobs_row = first['sqlserver_activity'][0]
    assert "bob" in first_users
    assert "fred" in first_users
    assert bobs_row['user_name'] == "bob"
    assert first['sqlserver_activity'][1]['user_name'] == "fred"

    # assert the data that was collected is correct
    assert bobs_row['user_name'] == "bob", "incorrect user_name"
    assert bobs_row['database_name'] == "datadog_test", "incorrect database_name"
    assert bobs_row['session_status'] == "sleeping", "incorrect session_status"
    assert bobs_row['id'], "missing session id"
    assert bobs_row['now'], "missing current timestamp"
    assert bobs_row['transaction_begin_time'], "missing tx begin time"

    # assert that the tx begin time is being collected as an ISO timestamp with TZ info
    assert parser.isoparse(bobs_row['transaction_begin_time']).tzinfo, "tx begin timestamp not formatted correctly"
    # assert that the current timestamp is being collected as an ISO timestamp with TZ info
    assert parser.isoparse(bobs_row['now']).tzinfo, "current timestamp not formatted correctly"

    assert len(first['sqlserver_connections']) > 0
    b_conn = None
    for conn in first['sqlserver_connections']:
        if conn['user_name'] == "bob":
            b_conn = conn
    assert b_conn is not None
    assert b_conn['connections'] == 1
    assert b_conn['status'] == "sleeping"

    # internal debug metrics
    aggregator.assert_metric(
        "dd.sqlserver.operation.time",
        tags=['agent_hostname:stubbed.hostname', 'operation:collect_activity']
        + _expected_dbm_instance_tags(dbm_instance),
    )

    # finally, on the second iteration, only bob's transaction is still open
    # and we don't need to collect fred's old transaction
    second = dbm_activity[1]
    assert len(second['sqlserver_activity']) > 0
    second_users = [f['user_name'] for f in second['sqlserver_activity']]
    assert "bob" in second_users and "fred" not in second_users

    # clean up bob's connection
    bob_conn.close()


@pytest.mark.parametrize(
    "rows,expected_len",
    [
        [
            [
                {'session_status': 'suspended', 'text': "something", 'start_time': 2},
                {'session_status': 'suspended', 'text': "something", 'start_time': 2, 'toobig': "shame" * 1000},
            ],
            1,
        ],
        [
            [
                {'session_status': 'suspended', 'text': "something", 'start_time': 2},
                {'session_status': 'suspended', 'text': "something", 'start_time': 2},
            ],
            2,
        ],
        [
            [
                {'session_status': 'suspended', 'text': "something", 'start_time': 2, 'toobig': "shame" * 1000},
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


def _load_test_activity_json(filename):
    with open(os.path.join(ACTIVITY_JSON_PLANS_DIR, filename), 'r') as f:
        return json.load(f)


def _get_conn_for_user(instance_docker, user):
    # Make DB connection
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};'.format(
        instance_docker['driver'], instance_docker['host'], user, "Password12!"
    )
    conn = pyodbc.connect(conn_str, timeout=DEFAULT_TIMEOUT, autocommit=False)
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


@not_windows_ci
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


@not_windows_ci
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
