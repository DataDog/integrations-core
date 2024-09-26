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
@pytest.mark.parametrize("use_autocommit", [True])
@pytest.mark.parametrize(
    "database,query,match_pattern,is_proc,expected_comments",
    [
        [
            "datadog_test-1",
            "/*test=foo*/ SELECT * FROM ϑings",
            r"SELECT \* FROM ϑings",
            False,
            ["/*test=foo*/"],
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
        cur.execute("USE [{}]".format(database))
        # 0xFF can't be decoded to Unicode, which makes it good test data,
        # since Unicode is a default format
        cur.execute("SET CONTEXT_INFO 0xff")
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
    assert blocked_row['database_name'] == "datadog_test-1", "incorrect database_name"
    assert blocked_row['context_info'] == "ff", "incorrect context_info"
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


def new_time():
    return datetime.datetime(2021, 9, 23, 23, 21, 21, 669330).isoformat()


def old_time():
    return datetime.datetime(2021, 9, 22, 22, 21, 21, 669330).isoformat()


def very_old_time():
    return datetime.datetime(2021, 9, 20, 23, 21, 21, 669330).isoformat()


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
