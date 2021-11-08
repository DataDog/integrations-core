import json
import os
import time
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy

import mock
import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.activity import dm_exec_requests_exclude_keys

from .common import CHECK_NAME
from .utils import not_windows_ci

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


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collect_activity(aggregator, dd_run_check, dbm_instance):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    # run the check, which should only see the current
    # session as active, and report that
    dd_run_check(check)

    expected_instance_tags = set(dbm_instance.get('tags', []))

    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    assert len(dbm_activity) == 1, "should have collected exactly one dbm-activity payload"
    only_active_event = dbm_activity[0]
    # validate common host fields
    assert only_active_event['host'] == "stubbed.hostname", "wrong hostname"
    assert only_active_event['dbm_type'] == "activity", "wrong dbm_type"
    assert only_active_event['ddsource'] == "sqlserver", "wrong source"
    assert only_active_event['ddagentversion'], "missing ddagentversion"
    assert set(only_active_event['ddtags'].split(',')) == expected_instance_tags, "wrong instance tags activity"
    assert type(only_active_event['collection_interval']) in (float, int), "invalid collection_interval"

    assert len(only_active_event['sqlserver_activity']) > 0
    for row in only_active_event['sqlserver_activity']:
        assert row['user_name'] == "datadog", "incorrect user_name"
        assert row['database_name'] == "master", "incorrect database_name"
        assert row['session_status'] != "sleeping", "incorrect session_status"
        assert row['query_signature'], "missing query signature"
        assert row['transaction_begin_time'], "missing tx begin time"
        for val in dm_exec_requests_exclude_keys:
            assert val not in row

    assert len(only_active_event['sqlserver_connections']) > 0
    dd_conn = None
    for conn in only_active_event['sqlserver_connections']:
        if conn['user_name'] == "datadog":
            dd_conn = conn
    assert dd_conn is not None
    assert dd_conn['connections'] == 1

    # internal debug metrics
    aggregator.assert_metric(
        "dd.sqlserver.activity.collect_activity.time",
        tags=['agent_hostname:stubbed.hostname'] + _expected_dbm_instance_tags(dbm_instance),
    )


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collect_idle_open_transactions(aggregator, instance_docker, dd_run_check, dbm_instance):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    query = "select * from things"
    bob_conn = _get_conn_for_user(instance_docker, "bob")
    with bob_conn.cursor() as cursor:
        cursor.execute("USE {}".format("datadog_test"))
        cursor.execute(query)

    fred_conn = _get_conn_for_user(instance_docker, "fred")
    with fred_conn.cursor() as cursor:
        cursor.execute("USE {}".format("datadog_test"))
        cursor.execute(query)

    # run the check once first
    # as idle sessions are skipped on first run
    time.sleep(1)
    dd_run_check(check)
    aggregator.reset()
    time.sleep(1)  # wait for coll interval
    dd_run_check(check)
    fred_conn.commit()  # close the open tx that belongs to fred
    time.sleep(1)  # wait for coll interval
    dd_run_check(check)  # run check again

    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    assert len(dbm_activity) == 2, "should have collected exactly two dbm-activity payloads"
    first = dbm_activity[0]
    second = dbm_activity[1]
    assert len(first['sqlserver_activity']) > 0 and len(second['sqlserver_activity']) > 0
    # bob and fred's open transactions should have been
    # collected on first iteration. and bob's has been open longer
    # so it should come first in the payload
    first_users = [f['user_name'] for f in first['sqlserver_activity']]
    assert "bob" and "fred" in first_users
    assert first['sqlserver_activity'][0]['user_name'] == "bob"
    assert first['sqlserver_activity'][1]['user_name'] == "fred"
    # ... but on the second iteration, only bob's transaction is still open
    # and we don't need to collect fred's old transaction
    second_users = [f['user_name'] for f in second['sqlserver_activity']]
    assert "bob" in second_users and "fred" not in second_users

    # clean up connections
    bob_conn.close()
    fred_conn.close()


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
        instance_docker['driver'], instance_docker['host'], user, "hey-there-{}123".format(user)
    )
    conn = pyodbc.connect(conn_str, timeout=30, autocommit=False)
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
