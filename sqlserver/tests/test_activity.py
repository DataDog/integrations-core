# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import concurrent
import datetime
import json
import os
import re
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy

import mock
import pytest
from dateutil import parser

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.dev.ci import running_on_windows_ci
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.activity import DM_EXEC_REQUESTS_COLS, _hash_to_hex

from .common import CHECK_NAME, OPERATION_TIME_METRIC_NAME, SQLSERVER_MAJOR_VERSION
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
    instance_docker['procedure_metrics'] = {'enabled': False}
    instance_docker['collect_settings'] = {'enabled': False}
    return copy(instance_docker)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize("use_autocommit", [True, False])
@pytest.mark.parametrize(
    "database,query,match_pattern,is_proc,expected_comments",
    [
        [
            "datadog_test",
            "/*test=foo*/ SELECT * FROM ϑings",
            r"SELECT \* FROM ϑings",
            False,
            ["/*test=foo*/"],
        ],
        [
            "datadog_test",
            "EXEC bobProc",
            r"SELECT \* FROM ϑings",
            True,
            [],
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
    expected_comments,
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

    instance_tags = set(dbm_instance.get('tags', []))
    expected_instance_tags = {t for t in instance_tags if not t.startswith('dd.internal')}

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
    assert len(event['sqlserver_activity']) == 2, "should have collected exactly two activity rows"
    event['sqlserver_activity'].sort(key=lambda r: r.get('blocking_session_id', 0))
    # the second query should be fred's, which is currently blocked on
    # bob who is holding a table lock
    blocked_row = event['sqlserver_activity'][1]
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
    assert blocked_row['dd_comments'] == expected_comments, "missing expected comments"
    # assert that the current timestamp is being collected as an ISO timestamp with TZ info
    assert parser.isoparse(blocked_row['now']).tzinfo, "current timestamp not formatted correctly"
    assert blocked_row["query_start"], "missing query_start"
    assert blocked_row["is_user_process"], "missing is_user_process"
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
    assert f_conn['status'] == "running" or f_conn['status'] == "sleeping"

    # internal debug metrics
    aggregator.assert_metric(
        OPERATION_TIME_METRIC_NAME,
        tags=['agent_hostname:stubbed.hostname', 'operation:collect_activity']
        + _expected_dbm_instance_tags(dbm_instance),
    )


@pytest.mark.skipif(running_on_windows_ci() and SQLSERVER_MAJOR_VERSION == 2019, reason='Test flakes on this set up')
def test_activity_nested_blocking_transactions(
    aggregator,
    instance_docker,
    dd_run_check,
    dbm_instance,
):
    """
    Test to ensure the check captures a scenario where a blocking idle transaction
    is collected through activity. An open transaction which completes its current
    request but has not committed can still hold a row-level lock preventing subsequent
    sessions from updating. It is important that the Agent captures these cases to show
    the complete picture and the last executed query responsible for the lock.
    """

    TABLE_NAME = "##LockTest{}".format(str(int(time.time() * 1000)))

    QUERIES_SETUP = (
        """
        CREATE TABLE {}
        (
            id int,
            name varchar(10),
            city varchar(20)
        )""".format(
            TABLE_NAME
        ),
        "INSERT INTO {} VALUES (1001, 'tire', 'sfo')".format(TABLE_NAME),
        "INSERT INTO {} VALUES (1002, 'wisth', 'nyc')".format(TABLE_NAME),
        "INSERT INTO {} VALUES (1003, 'tire', 'aus')".format(TABLE_NAME),
        "COMMIT",
    )

    QUERY1 = """UPDATE {} SET [name] = 'west' WHERE [id] = 1001""".format(TABLE_NAME)
    QUERY2 = """UPDATE {} SET [name] = 'fast' WHERE [id] = 1001""".format(TABLE_NAME)
    QUERY3 = """UPDATE {} SET [city] = 'blow' WHERE [id] = 1001""".format(TABLE_NAME)

    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    conn1 = _get_conn_for_user(instance_docker, "fred", _autocommit=False)
    conn2 = _get_conn_for_user(instance_docker, "bob", _autocommit=False)
    conn3 = _get_conn_for_user(instance_docker, "fred", _autocommit=False)

    close_conns = threading.Event()

    def run_queries(conn, queries):
        cur = conn.cursor()
        cur.execute("USE {}".format("datadog_test"))
        cur.execute("BEGIN TRANSACTION")
        for q in queries:
            try:
                cur.execute(q)
            except pyodbc.OperationalError:
                # This is expected since the query (might be) blocked
                pass
        # Do not allow the conn to be garbage collected and closed until the global lock is released
        while not close_conns.is_set():
            time.sleep(0.1)
        cur.execute("COMMIT")

    # Setup
    cur = conn1.cursor()
    for q in QUERIES_SETUP:
        cur.execute(q)

    # Transaction 1
    t1 = threading.Thread(target=run_queries, args=(conn1, [QUERY1]))
    # Transaction 2
    t2 = threading.Thread(target=run_queries, args=(conn2, [QUERY2]))
    # Transaction 3
    t3 = threading.Thread(target=run_queries, args=(conn3, [QUERY3]))

    t1.start()
    time.sleep(0.3)
    t2.start()
    time.sleep(0.3)
    t3.start()

    try:
        dd_run_check(check)
        dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    finally:
        close_conns.set()  # Release the threads

    # All 3 connections are expected
    assert dbm_activity and 'sqlserver_activity' in dbm_activity[0]
    assert len(dbm_activity[0]['sqlserver_activity']) == 3

    activity = dbm_activity[0]['sqlserver_activity']
    activity = sorted(activity, key=lambda a: a.get('blocking_session_id', 0))

    root_blocker = activity[0]
    tx2 = activity[1]
    tx3 = activity[2]

    # Expect to capture the root blocker, which would have a sleeping transaction but no
    # associated sys.dm_exec_requests.
    assert root_blocker["user_name"] == "fred"
    assert root_blocker["session_status"] == "sleeping"
    assert root_blocker["database_name"] == "datadog_test"
    assert root_blocker["last_request_start_time"]
    assert root_blocker["client_port"]
    assert root_blocker["client_address"]
    assert root_blocker["host_name"]
    # Expect to capture the query signature for the root blocker
    # query text is not captured from the req dmv
    # but available in the connection dmv with most_recent_sql_handle
    assert root_blocker["query_signature"]
    # we do not capture requests for sleeping sessions
    assert "blocking_session_id" not in root_blocker
    assert "request_status" not in root_blocker
    assert "query_start" not in root_blocker

    # TX2 should be blocked by the root blocker TX1, TX3 should be blocked by TX2
    assert tx2["blocking_session_id"] == root_blocker["id"]
    assert tx3["blocking_session_id"] == tx2["id"]
    # TX2 and TX3 should be running
    assert tx2["session_status"] == "running"
    assert tx3["session_status"] == "running"
    # verify other essential fields are present
    assert tx2["user_name"] == "bob"
    assert tx2["database_name"] == "datadog_test"
    assert tx2["last_request_start_time"]
    assert tx2["client_port"]
    assert tx2["client_address"]
    assert tx2["host_name"]
    assert tx2["query_signature"]
    assert tx2["request_status"]
    assert tx2["query_start"]
    assert tx2["query_hash"]
    assert tx2["query_plan_hash"]

    assert tx3["user_name"] == "fred"
    assert tx3["database_name"] == "datadog_test"
    assert tx3["last_request_start_time"]
    assert tx3["client_port"]
    assert tx3["client_address"]
    assert tx3["host_name"]
    assert tx3["query_signature"]
    assert tx3["request_status"]
    assert tx3["query_start"]
    assert tx3["query_hash"]
    assert tx3["query_plan_hash"]

    assert isinstance(tx2["query_hash"], str)
    assert isinstance(tx2["query_plan_hash"], str)
    assert isinstance(tx3["query_hash"], str)
    assert isinstance(tx3["query_plan_hash"], str)

    for t in [t1, t2, t3]:
        t.join()


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
            {'tables_csv': '', 'commands': None, 'comments': ['-- Test comment']},
            {'tables': None, 'commands': None, 'comments': ['-- Test comment']},
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
    return datetime.datetime(2021, 9, 23, 23, 21, 21, 669330).isoformat()


def old_time():
    return datetime.datetime(2021, 9, 22, 22, 21, 21, 669330).isoformat()


def very_old_time():
    return datetime.datetime(2021, 9, 20, 23, 21, 21, 669330).isoformat()


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


@pytest.mark.unit
def test_activity_stored_procedure_failed_to_obfuscate(dbm_instance, datadog_agent):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        large_comment = "/* " + "a" * 5000 + " */"
        statement_text = "SELECT * FROM ϑings"
        procedure_text = f"CREATE PROCEDURE dbo.sp_test {large_comment} AS BEGIN {statement_text} END;"
        metadata = {'tables_csv': 'ϑings', 'commands': ['SELECT'], 'comments': [large_comment]}
        rows = [
            {
                "user_name": "newbob",
                "id": 1,
                "statement_text": statement_text,
                "text": procedure_text,
                "query_start": new_time(),
            },
        ]
        # the first call to obfuscate query text will succeed
        # the second call to obfuscate procedure text will fail
        mock_agent.side_effect = [
            json.dumps({'query': statement_text, 'metadata': metadata}),
            Exception("failed to obfuscate"),
        ]
        result_rows = check.activity._normalize_queries_and_filter_rows(rows, 10000)
        # procedure text obfuscation will fail but the activity row will still be collected
        assert len(result_rows) == 1
        assert result_rows[0]['text'] == statement_text
        assert result_rows[0]['is_proc'] is True
        assert result_rows[0]['procedure_signature'] == '__procedure_obfuscation_error__'


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "stored_procedure_characters_limit",
    [
        500,
        1000,
        2000,
    ],
)
def test_activity_stored_procedure_characters_limit(
    aggregator,
    instance_docker,
    dd_run_check,
    dbm_instance,
    datadog_agent,
    stored_procedure_characters_limit,
):
    dbm_instance['stored_procedure_characters_limit'] = stored_procedure_characters_limit
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    def _obfuscate_sql(sql_query, options=None):
        if "PROCEDURE procedureWithLargeCommment" in sql_query and len(sql_query) >= stored_procedure_characters_limit:
            raise Exception("failed to obfuscate")
        return json.dumps({'query': sql_query, 'metadata': {}})

    blocking_query = "INSERT INTO ϑings WITH (TABLOCK, HOLDLOCK) (name) VALUES ('puppy')"
    fred_conn = _get_conn_for_user(instance_docker, "fred", _autocommit=True)
    bob_conn = _get_conn_for_user(instance_docker, "bob")

    def run_test_query(c, q):
        cur = c.cursor()
        cur.execute("USE datadog_test")
        cur.execute(q)

    run_test_query(fred_conn, "EXEC procedureWithLargeCommment")

    # bob's query blocks until the tx is completed
    run_test_query(bob_conn, blocking_query)

    # fred's query will get blocked by bob, so it needs
    # to be run asynchronously
    executor = concurrent.futures.ThreadPoolExecutor(1)
    f_q = executor.submit(run_test_query, fred_conn, "EXEC procedureWithLargeCommment")
    while not f_q.running():
        if f_q.done():
            break
        print("waiting on fred's query to execute")
        time.sleep(1)

    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = _obfuscate_sql
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

    executor = concurrent.futures.ThreadPoolExecutor(1)
    b_q = executor.submit(run_test_query, bob_conn)
    while not b_q.running():
        if b_q.done():
            break
        time.sleep(1)

    dbm_activity = aggregator.get_event_platform_events("dbm-activity")
    assert dbm_activity, "should have collected at least one activity"

    matching_activity = []
    for event in dbm_activity:
        for activity in event['sqlserver_activity']:
            if activity['query_signature'] == "2fa838aee8217d23":
                matching_activity.append(activity)
    assert len(matching_activity) == 1
    assert matching_activity[0]['is_proc'] is True
    assert matching_activity[0]['procedure_name'].lower() == "procedurewithlargecommment"
    assert matching_activity[0]['text'] == "SELECT * FROM ϑings"
    # this is a hacky way of asserting that the procedure signature is present
    # when stored_procedure_characters_limit is set to a large value
    if stored_procedure_characters_limit > 500:
        assert "procedure_signature" in matching_activity[0]


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


def _load_test_activity_json(filename):
    with open(os.path.join(ACTIVITY_JSON_PLANS_DIR, filename), 'r') as f:
        return json.load(f)


def _get_conn_for_user(instance_docker, user, _autocommit=False):
    # Make DB connection
    conn_str = 'DRIVER={};Server={};Database=master;UID={};PWD={};TrustServerCertificate=yes;'.format(
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


@pytest.mark.parametrize(
    "input,expected",
    [
        (b'0xBA61D813C4878164', '307842413631443831334334383738313634'),
        (b'0x0000000000000000', '307830303030303030303030303030303030'),
    ],
)
def test_hash_to_hex(input, expected):
    output = _hash_to_hex(input)
    assert output == expected
    assert type(output) == str


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


@pytest.mark.parametrize(
    "row",
    [
        pytest.param(
            {
                'now': '2023-10-06T12:11:16.167-07:00',
                'query_start': '2023-10-06T12:11:16.167-07:00',
                'user_name': 'shopper',
                'last_request_start_time': datetime.datetime(2023, 10, 6, 12, 11, 16, 167000),
                'id': 70,
                'database_name': 'dbmorders_1',
                'session_status': 'running',
                'request_status': 'runnable',
                'statement_text': None,
                'text': None,
                'client_port': 54708,
                'client_address': '127.0.0.1',
                'host_name': 'sqlserver-25542ca5-764d9496f4-mk7fv',
                'program_name': 'go-mssqldb',
                'command': 'SELECT',
                'blocking_session_id': 0,
                'wait_type': None,
                'wait_time': 0,
                'last_wait_type': 'SOS_SCHEDULER_YIELD',
                'wait_resource': '',
                'open_transaction_count': 0,
                'transaction_id': 15567746,
                'percent_complete': 0.0,
                'estimated_completion_time': 0,
                'cpu_time': 3,
                'total_elapsed_time': 10,
                'reads': 0,
                'writes': 0,
                'logical_reads': 80,
                'transaction_isolation_level': 2,
                'lock_timeout': -1,
                'deadlock_priority': 0,
                'row_count': 1,
                'query_hash': b'f\x8b\xa3Xc\xb3T\xfb',
                'query_plan_hash': b'\xb0qh9\x0c\xa9\xa3\xb8',
            },
            id="no_statement_text",
        ),
        pytest.param(
            {
                'now': '2023-10-06T19:36:10.550+00:00',
                'query_start': '2023-10-06T19:36:10.483+00:00',
                'user_name': 'datadog',
                'last_request_start_time': datetime.datetime(2023, 10, 6, 19, 36, 10, 483000),
                'id': 161,
                'database_name': 'master',
                'session_status': 'running',
                'request_status': 'runnable',
                'statement_text': "SELECT * from orders",
                'client_port': 48416,
                'client_address': '10.135.98.65',
                'host_name': 'sqlserver-9e8c6bf5-78fdd7765f-wr4g5',
                'program_name': '',
                'command': 'SELECT',
                'blocking_session_id': 0,
                'wait_type': None,
                'wait_time': 0,
                'last_wait_type': 'SOS_SCHEDULER_YIELD',
                'wait_resource': '',
                'open_transaction_count': 0,
                'transaction_id': 966590372257,
                'percent_complete': 0.0,
                'estimated_completion_time': 0,
                'cpu_time': 23,
                'total_elapsed_time': 72,
                'reads': 0,
                'writes': 0,
                'logical_reads': 98,
                'transaction_isolation_level': 1,
                'lock_timeout': -1,
                'deadlock_priority': 0,
                'row_count': 0,
                'query_hash': b'\xa4\xffV\x1c\xd4\x14\xbeC',
                'query_plan_hash': b'\xfe\xba\xbf\xc6_\x9bo\x83',
            },
            id="with_statement_text",
        ),
    ],
)
def test_sanitize_activity_row(dbm_instance, row):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    row = check.activity._obfuscate_and_sanitize_row(row)
    assert isinstance(row['query_hash'], str)
    assert isinstance(row['query_plan_hash'], str)
