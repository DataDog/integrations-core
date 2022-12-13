# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import concurrent
import datetime
import json
import os
import re
import time
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy

import mock
import pytest
from dateutil import parser

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.activity import DM_EXEC_REQUESTS_COLS
from datadog_checks.sqlserver.utils import is_statement_proc

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
    }
    # do not need query_metrics for these tests
    instance_docker['query_metrics'] = {'enabled': False}
    return copy(instance_docker)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize("use_autocommit", [True, False])
@pytest.mark.parametrize(
    "database,query,match_pattern,is_proc",
    [
        [
            "datadog_test",
            "SELECT * FROM ϑings",
            r"SELECT \* FROM ϑings",
            False,
        ],
        [
            "datadog_test",
            "EXEC bobProc",
            r"SELECT \* FROM ϑings",
            True,
        ],
    ],
)
def test_collect_load_activity(
    aggregator,
    instance_docker,
    dd_run_check,
    dbm_instance,
    use_autocommit,
    database,
    query,
    match_pattern,
    is_proc,
):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    blocking_query = "INSERT INTO ϑings WITH (TABLOCK, HOLDLOCK) (name) VALUES ('puppy')"
    fred_conn = _get_conn_for_user(instance_docker, "fred", _autocommit=use_autocommit)
    bob_conn = _get_conn_for_user(instance_docker, "bob")

    def run_test_query(c, q):
        cur = c.cursor()
        cur.execute("USE {}".format(database))
        cur.execute(q)

    # run the test query once before the blocking test to ensure that if it's
    # a procedure then it is populated in the sys.dm_exec_procedure_stats table
    # the first time a procedure is run we won't know it's a procedure because
    # it won't appear in that stats table
    run_test_query(fred_conn, query)

    # bob's query blocks until the tx is completed
    run_test_query(bob_conn, blocking_query)

    # fred's query will get blocked by bob, so it needs
    # to be run asynchronously
    executor = concurrent.futures.ThreadPoolExecutor(1)
    f_q = executor.submit(run_test_query, fred_conn, query)
    while not f_q.running():
        if f_q.done():
            break
        print("waiting on fred's query to execute")
        time.sleep(1)

    # both queries were kicked off, so run the check
    dd_run_check(check)
    # commit and close bob's transaction
    bob_conn.commit()
    bob_conn.close()

    while not f_q.done():
        print("blocking query finished, waiting for fred's query to complete")
        time.sleep(1)
    # clean up fred's connection
    # and shutdown executor
    fred_conn.close()
    executor.shutdown(wait=True)

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

    assert len(event['sqlserver_activity']) == 1, "should have collected exactly one activity row"
    # the second query should be fred's, which is currently blocked on
    # bob who is holding a table lock
    blocked_row = event['sqlserver_activity'][0]
    # assert the data that was collected is correct
    assert blocked_row['user_name'] == "fred", "incorrect user_name"
    assert blocked_row['session_status'] == "running", "incorrect session_status"
    assert blocked_row['request_status'] == "suspended", "incorrect request_status"
    assert blocked_row['blocking_session_id'], "missing blocking_session_id"
    assert blocked_row['is_proc'] == is_proc
    assert 'statement_text' not in blocked_row, "statement_text field should not be forwarded"
    if is_proc:
        assert blocked_row['procedure_signature'], "missing procedure signature"
        assert blocked_row['procedure_name'], "missing procedure name"
    assert re.match(match_pattern, blocked_row['text'], re.IGNORECASE), "incorrect blocked query"
    assert blocked_row['database_name'] == "datadog_test", "incorrect database_name"
    assert blocked_row['id'], "missing session id"
    assert blocked_row['now'], "missing current timestamp"
    assert blocked_row['last_request_start_time'], "missing last_request_start_time"
    assert blocked_row['now'], "missing current time"
    # assert that the current timestamp is being collected as an ISO timestamp with TZ info
    assert parser.isoparse(blocked_row['now']).tzinfo, "current timestamp not formatted correctly"
    assert blocked_row["query_start"], "missing query_start"
    assert parser.isoparse(blocked_row["query_start"]).tzinfo, "query_start timestamp not formatted correctly"
    for r in DM_EXEC_REQUESTS_COLS:
        assert r in blocked_row

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
    # TODO: fix test to ensure there is only a single connection per user
    # for some reason bob's connection is intermittently showing 2 connections
    # To make the tests less flaky we're setting this to >= 1 for now.
    assert b_conn['connections'] >= 1
    assert b_conn['status'] == "sleeping"
    assert f_conn['connections'] >= 1
    assert f_conn['status'] == "running"

    # internal debug metrics
    aggregator.assert_metric(
        "dd.sqlserver.operation.time",
        tags=['agent_hostname:stubbed.hostname', 'operation:collect_activity']
        + _expected_dbm_instance_tags(dbm_instance),
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "metadata,expected_metadata_payload",
    [
        (
            {'tables_csv': 'ϑings', 'commands': ['SELECT'], 'comments': ['-- Test comment']},
            {'tables': ['ϑings'], 'commands': ['SELECT'], 'comments': ['-- Test comment']},
        ),
        (
            {'tables_csv': '', 'commands': None, 'comments': None},
            {'tables': None, 'commands': None, 'comments': None},
        ),
    ],
)
def test_activity_metadata(
    aggregator, instance_docker, dd_run_check, dbm_instance, datadog_agent, metadata, expected_metadata_payload
):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    query = '''
    -- Test comment
    SELECT * FROM ϑings'''
    query_signature = '2fa838aee8217d23'
    blocking_query = "INSERT INTO ϑings WITH (TABLOCK, HOLDLOCK) (name) VALUES ('puppy')"

    bob_conn = _get_conn_for_user(instance_docker, 'bob')
    fred_conn = _get_conn_for_user(instance_docker, 'fred')

    def _run_test_query(conn, q):
        cur = conn.cursor()
        cur.execute("USE {}".format("datadog_test"))
        cur.execute(q)

    def _obfuscate_sql(sql_query, options=None):
        return json.dumps({'query': sql_query, 'metadata': metadata})

    def _run_query_with_mock_obfuscator(conn, query):
        # Execute the query with the mocked obfuscate_sql. The result should produce an event payload with the metadata.
        with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
            mock_agent.side_effect = _obfuscate_sql
            _run_test_query(conn, query)

    # bob's query blocks until the tx is completed
    _run_query_with_mock_obfuscator(bob_conn, blocking_query)

    # fred's query will get blocked by bob, so it needs
    # to be run asynchronously
    executor = concurrent.futures.ThreadPoolExecutor(1)
    f_q = executor.submit(_run_query_with_mock_obfuscator, fred_conn, query)
    while not f_q.running():
        if f_q.done():
            break
        print("waiting on fred's query to execute")
        time.sleep(1)

    dd_run_check(check)

    bob_conn.commit()
    bob_conn.close()

    while not f_q.done():
        print("blocking query finished, waiting for fred's query to complete")
        time.sleep(1)

    fred_conn.close()
    executor.shutdown(wait=True)

    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    assert dbm_activity, "should have collected at least one activity"
    matching_activity = []
    for event in dbm_activity:
        for activity in event['sqlserver_activity']:
            if activity['query_signature'] == query_signature:
                matching_activity.append(activity)
    assert len(matching_activity) == 1
    activity = matching_activity[0]
    assert activity['dd_tables'] == expected_metadata_payload['tables']
    assert activity['dd_commands'] == expected_metadata_payload['commands']
    assert activity['dd_comments'] == expected_metadata_payload['comments']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "reported_hostname,expected_hostname",
    [
        (None, 'stubbed.hostname'),
        ('override.hostname', 'override.hostname'),
    ],
)
def test_activity_reported_hostname(
    aggregator, instance_docker, dd_run_check, dbm_instance, reported_hostname, expected_hostname
):
    dbm_instance['reported_hostname'] = reported_hostname
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    dd_run_check(check)
    dd_run_check(check)

    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    assert dbm_activity, "should have at least one activity"
    assert dbm_activity[0]['host'] == expected_hostname


def new_time():
    return datetime.datetime(2021, 9, 23, 23, 21, 21, 669330)


def old_time():
    return datetime.datetime(2021, 9, 22, 22, 21, 21, 669330)


def very_old_time():
    return datetime.datetime(2021, 9, 20, 23, 21, 21, 669330)


@pytest.mark.parametrize(
    "rows,expected_len,expected_users",
    [
        [
            [
                {
                    'last_request_start_time': 'suspended',
                    'id': 1,
                    'user_name': 'oldbob',
                    'text': "something",
                    'start_time': 2,
                    'query_start': old_time(),
                },
                {
                    'last_request_start_time': 'suspended',
                    'id': 1,
                    'user_name': 'olderbob',
                    'text': "something",
                    'start_time': 2,
                    'query_start': very_old_time(),
                },
                {
                    'last_request_start_time': 'suspended',
                    'id': 2,
                    'text': "something",
                    'user_name': 'bigbob',
                    'start_time': 2,
                    'query_start': new_time(),
                    'toobig': "shame" * 10000,
                },
                {
                    'last_request_start_time': 'suspended',
                    'id': 1,
                    'user_name': 'onlytxbob',
                    'text': "something",
                    'start_time': 2,
                    'transaction_begin_time': very_old_time(),
                },
            ],
            2,
            ["olderbob", "oldbob"],
        ],
        [
            [
                {
                    'last_request_start_time': 'suspended',
                    'id': 1,
                    'user_name': 'newbob',
                    'text': "something",
                    'start_time': 2,
                    'query_start': new_time(),
                },
                {
                    'last_request_start_time': 'suspended',
                    'id': 1,
                    'user_name': 'oldestbob',
                    'text': "something",
                    'start_time': 2,
                    'query_start': very_old_time(),
                },
                {
                    'last_request_start_time': 'suspended',
                    'id': 2,
                    'text': "something",
                    'user_name': 'bigbob',
                    'start_time': 2,
                    'query_start': old_time(),
                    'toobig': "shame" * 10000,
                },
            ],
            1,
            ["oldestbob"],
        ],
        [
            [
                {'user_name': 'newbob', 'id': 1, 'text': "something", 'query_start': new_time()},
                {'user_name': 'oldbob', 'id': 2, 'text': "something", 'query_start': old_time()},
                {'user_name': 'olderbob', 'id': 2, 'text': "something", 'query_start': very_old_time()},
            ],
            3,
            ["olderbob", "oldbob", "newbob"],
        ],
        [
            [
                {
                    'user_name': 'bigbob',
                    'id': 1,
                    'text': "something",
                    'toobig': "shame" * 10000,
                },
            ],
            0,
            [],
        ],
    ],
)
def test_truncate_on_max_size_bytes(dbm_instance, datadog_agent, rows, expected_len, expected_users):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = "something"
        result_rows = check.activity._normalize_queries_and_filter_rows(rows, 10000)
        assert len(result_rows) == expected_len
        for index, user in enumerate(expected_users):
            assert result_rows[index]['user_name'] == user


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


@pytest.mark.parametrize(
    "query,is_proc,expected_name",
    [
        [
            """\
            CREATE PROCEDURE bobProcedure
            BEGIN
                SELECT name FROM bob
            END;
            """,
            True,
            "bobProcedure",
        ],
        [
            """\
            CREATE PROC bobProcedure
            BEGIN
                SELECT name FROM bob
            END;
            """,
            True,
            "bobProcedure",
        ],
        [
            """\
            create procedure bobProcedureLowercase
            begin
                select name from bob
            end;
            """,
            True,
            "bobProcedureLowercase",
        ],
        [
            """\
            /* my sql is very fun */
            CREATE PROCEDURE bobProcedure
            BEGIN
                SELECT name FROM bob
            END;
            """,
            True,
            "bobProcedure",
        ],
        [
            """\
            CREATE /* this is fun! */ PROC bobProcedure
            BEGIN
                SELECT name FROM bob
            END;
            """,
            True,
            "bobProcedure",
        ],
        [
            """\
            -- this is a comment!
            CREATE
            -- additional comment here!
            PROCEDURE bobProcedure
            BEGIN
                SELECT name FROM bob
            END;
            """,
            True,
            "bobProcedure",
        ],
        [
            "CREATE TABLE bob_table",
            False,
            None,
        ],
        [
            "Exec procedure",
            False,
            None,
        ],
        [
            "CREATEprocedure",
            False,
            None,
        ],
        [
            "procedure create",
            False,
            None,
        ],
    ],
)
def test_is_statement_procedure(query, is_proc, expected_name):
    p, name = is_statement_proc(query)
    assert p == is_proc
    assert re.match(name, expected_name, re.IGNORECASE) if expected_name else expected_name == name


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
