# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import math
import os
import re
import time
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy

import mock
import pytest
from lxml import etree as ET

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.statements import SQL_SERVER_QUERY_METRICS_COLUMNS, obfuscate_xml_plan

from .common import CHECK_NAME
from .utils import not_windows_ci, windows_ci

try:
    import pyodbc
except ImportError:
    pyodbc = None


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['min_collection_interval'] = 1
    # set a very small collection interval so the tests go fast
    instance_docker['query_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    return copy(instance_docker)


@pytest.fixture
def instance_sql_msoledb_dbm(instance_sql_msoledb):
    instance_sql_msoledb['dbm'] = True
    instance_sql_msoledb['min_collection_interval'] = 1
    instance_sql_msoledb['query_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 2}
    instance_sql_msoledb['tags'] = ['optional:tag1']
    return instance_sql_msoledb


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "expected_columns,available_columns",
    [
        [
            ["execution_count", "total_worker_time"],
            ["execution_count", "total_worker_time"],
        ],
        [
            ["execution_count", "total_worker_time", "some_missing_column"],
            ["execution_count", "total_worker_time"],
        ],
    ],
)
def test_get_available_query_metrics_columns(aggregator, dbm_instance, expected_columns, available_columns):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.initialize_connection()
    _conn_key_prefix = "dbm-"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            result_available_columns = check.statement_metrics._get_available_query_metrics_columns(
                cursor, expected_columns
            )
            assert result_available_columns == available_columns


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_get_statement_metrics_query_cached(aggregator, dbm_instance, caplog):
    caplog.set_level(logging.DEBUG)
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.initialize_connection()
    _conn_key_prefix = "dbm-"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            for _ in range(3):
                query = check.statement_metrics._get_statement_metrics_query_cached(cursor)
                assert query, "query should be non-empty"
    times_columns_loaded = 0
    for r in caplog.records:
        if r.message.startswith("found available sys.dm_exec_query_stats columns"):
            times_columns_loaded += 1
    assert times_columns_loaded == 1, "columns should have been loaded only once"


test_statement_metrics_and_plans_parameterized = (
    "database,plan_user,query,match_pattern,param_groups",
    [
        [
            "datadog_test",
            "dbo",
            "SELECT * FROM ϑings",
            r"SELECT \* FROM ϑings",
            ((),),
        ],
        [
            "datadog_test",
            "dbo",
            "SELECT * FROM ϑings where id = ?",
            r"\(@P1 \w+\)SELECT \* FROM ϑings where id = @P1",
            (
                (1,),
                (2,),
                (3,),
            ),
        ],
        [
            "master",
            None,
            "SELECT * FROM datadog_test.dbo.ϑings where id = ?",
            r"\(@P1 \w+\)SELECT \* FROM datadog_test.dbo.ϑings where id = @P1",
            (
                (1,),
                (2,),
                (3,),
            ),
        ],
        [
            "datadog_test",
            "dbo",
            "SELECT * FROM ϑings where id = ? and name = ?",
            r"\(@P1 \w+,@P2 (N)?VARCHAR\(\d+\)\)SELECT \* FROM ϑings where id = @P1 and name = @P2",
            (
                (1, "hello"),
                (2, "there"),
                (3, "bill"),
            ),
        ],
    ],
)


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(*test_statement_metrics_and_plans_parameterized)
def test_statement_metrics_and_plans(
    aggregator, dd_run_check, dbm_instance, bob_conn, database, plan_user, query, param_groups, match_pattern, caplog
):
    _run_test_statement_metrics_and_plans(
        aggregator,
        dd_run_check,
        dbm_instance,
        bob_conn,
        database,
        plan_user,
        query,
        param_groups,
        match_pattern,
        caplog,
    )


@windows_ci
@pytest.mark.integration
@pytest.mark.parametrize(*test_statement_metrics_and_plans_parameterized)
def test_statement_metrics_and_plans_windows(
    aggregator,
    dd_run_check,
    instance_sql_msoledb_dbm,
    bob_conn,
    database,
    plan_user,
    query,
    param_groups,
    match_pattern,
    caplog,
):
    _run_test_statement_metrics_and_plans(
        aggregator,
        dd_run_check,
        instance_sql_msoledb_dbm,
        bob_conn,
        database,
        plan_user,
        query,
        param_groups,
        match_pattern,
        caplog,
    )


def _run_test_statement_metrics_and_plans(
    aggregator, dd_run_check, dbm_instance, bob_conn, database, plan_user, query, param_groups, match_pattern, caplog
):
    caplog.set_level(logging.INFO)
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    # the check must be run three times:
    # 1) set _last_stats_query_time (this needs to happen before the 1st test queries to ensure the query time
    # interval is correct)
    # 2) load the test queries into the StatementMetrics state
    # 3) emit the query metrics based on the diff of current and last state
    dd_run_check(check)
    for params in param_groups:
        bob_conn.execute_with_retries(query, params, database=database)
    dd_run_check(check)
    aggregator.reset()
    for params in param_groups:
        bob_conn.execute_with_retries(query, params, database=database)
    dd_run_check(check)

    _conn_key_prefix = "dbm-"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            available_query_metrics_columns = check.statement_metrics._get_available_query_metrics_columns(
                cursor, SQL_SERVER_QUERY_METRICS_COLUMNS
            )

    expected_instance_tags = set(dbm_instance.get('tags', []))
    expected_instance_tags_with_db = set(dbm_instance.get('tags', [])) | {"db:{}".format(database)}

    # dbm-metrics
    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(dbm_metrics) == 1, "should have collected exactly one dbm-metrics payload"
    payload = dbm_metrics[0]
    # host metadata
    assert payload['sqlserver_version'].startswith("Microsoft SQL Server"), "invalid version"
    assert payload['host'] == "stubbed.hostname", "wrong hostname"
    assert set(payload['tags']) == expected_instance_tags, "wrong instance tags for dbm-metrics event"
    assert type(payload['min_collection_interval']) in (float, int), "invalid min_collection_interval"
    # metrics rows
    sqlserver_rows = payload.get('sqlserver_rows', [])
    assert sqlserver_rows, "should have collected some sqlserver query metrics rows"
    matching_rows = [r for r in sqlserver_rows if re.match(match_pattern, r['text'], re.IGNORECASE)]
    assert len(matching_rows) >= 1, "expected at least one matching metrics row"
    total_execution_count = sum([r['execution_count'] for r in matching_rows])
    assert total_execution_count == len(param_groups), "wrong execution count"
    for row in matching_rows:
        assert row['query_signature'], "missing query signature"
        assert row['database_name'] == database, "incorrect database_name"
        assert row['user_name'] == plan_user, "incorrect user_name"
        for column in available_query_metrics_columns:
            assert column in row, "missing required metrics column {}".format(column)
            assert type(row[column]) in (float, int), "wrong type for metrics column {}".format(column)

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    assert dbm_samples, "should have collected at least one sample"

    matching_samples = [s for s in dbm_samples if re.match(match_pattern, s['db']['statement'], re.IGNORECASE)]
    assert matching_samples, "should have collected some matching samples"

    # validate common host fields
    for event in matching_samples:
        assert event['host'] == "stubbed.hostname", "wrong hostname"
        assert event['ddsource'] == "sqlserver", "wrong source"
        assert event['ddagentversion'], "missing ddagentversion"
        assert set(event['ddtags'].split(',')) == expected_instance_tags_with_db, "wrong instance tags for plan event"

    plan_events = [s for s in dbm_samples if s['dbm_type'] == "plan"]
    assert plan_events, "should have collected some plans"

    for event in plan_events:
        assert event['db']['plan']['definition'], "event plan definition missing"
        parsed_plan = ET.fromstring(event['db']['plan']['definition'])
        assert parsed_plan.tag.endswith("ShowPlanXML"), "plan does not match expected structure"

    fqt_events = [s for s in dbm_samples if s['dbm_type'] == "fqt"]
    assert fqt_events, "should have collected some FQT events"

    # internal debug metrics
    aggregator.assert_metric(
        "dd.sqlserver.operation.time",
        tags=['agent_hostname:stubbed.hostname', 'operation:collect_statement_metrics_and_plans']
        + _expected_dbm_instance_tags(dbm_instance),
    )


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_statement_basic_metrics_query(datadog_conn_docker, dbm_instance):
    now = time.time()
    test_query = "select * from sys.databases"

    # run this test query to guarantee there's at least one application query in the query plan cache
    with datadog_conn_docker.cursor() as cursor:
        cursor.execute(test_query)
        cursor.fetchall()

    # load statement_metrics_query
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.initialize_connection()
    _conn_key_prefix = "dbm-"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            statement_metrics_query = check.statement_metrics._get_statement_metrics_query_cached(cursor)

    # this test ensures that we're able to run the basic STATEMENT_METRICS_QUERY without error
    # the dm_exec_plan_attributes table-valued function used in this query contains a "sql_variant" data type
    # which is not supported by pyodbc, so we need to explicitly cast the field into the type we expect to see
    # without the cast this is expected to fail with
    # pyodbc.ProgrammingError: ('ODBC SQL type -150 is not yet supported.  column-index=77  type=-150', 'HY106')
    with datadog_conn_docker.cursor() as cursor:
        params = (math.ceil(time.time() - now),)
        logging.debug("running statement_metrics_query [%s] %s", statement_metrics_query, params)
        cursor.execute(statement_metrics_query, params)

        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        matching = [r for r in rows if r['text'] == test_query]
        assert matching, "the test query should be visible in the query stats"
        row = matching[0]

        cursor.execute(
            "select count(*) from sys.dm_exec_query_stats where query_hash = ? and query_plan_hash = ?",
            row['query_hash'],
            row['query_plan_hash'],
        )

        assert cursor.fetchall()[0][0] >= 1, "failed to read back the same query stats using the query and plan hash"


XML_PLANS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xml_plans")


def _strip_whitespace(raw_plan):
    tree = ET.fromstring(raw_plan)
    for e in tree.iter():
        if e.text:
            e.text = e.text.strip()
        if e.tail:
            e.tail = e.tail.strip()
    return to_native_string(ET.tostring(tree))


def _load_test_xml_plan(filename):
    with open(os.path.join(XML_PLANS_DIR, filename), 'r') as f:
        return f.read()


def _mock_sql_obfuscate(sql_string):
    sql_string = re.sub(r"'[^']+'", r"?", sql_string)
    sql_string = re.sub(r"([^@])[0-9]+", r"\1?", sql_string)
    return sql_string


@pytest.mark.parametrize(
    "test_file,obfuscated_file",
    [
        ("test1_raw.xml", "test1_obfuscated.xml"),
        ("test2_raw.xml", "test2_obfuscated.xml"),
    ],
)
def test_obfuscate_xml_plan(test_file, obfuscated_file, datadog_agent):
    test_plan = _strip_whitespace(_load_test_xml_plan(test_file))
    expected_result = _strip_whitespace(_load_test_xml_plan(obfuscated_file))

    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = _mock_sql_obfuscate
        result = obfuscate_xml_plan(test_plan)
        assert result == expected_result, "incorrect obfuscation"


PORT = 1432


def _expected_dbm_instance_tags(dbm_instance):
    return dbm_instance['tags']


@pytest.mark.parametrize("statement_metrics_enabled", [True, False])
def test_async_job_enabled(dd_run_check, dbm_instance, statement_metrics_enabled):
    dbm_instance['query_metrics'] = {'enabled': statement_metrics_enabled, 'run_sync': False}
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.cancel()
    if statement_metrics_enabled:
        assert check.statement_metrics._job_loop_future is not None
        check.statement_metrics._job_loop_future.result()
    else:
        assert check.statement_metrics._job_loop_future is None


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_async_job_inactive_stop(aggregator, dd_run_check, dbm_instance):
    dbm_instance['query_metrics']['run_sync'] = False
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.statement_metrics._job_loop_future.result()
    aggregator.assert_metric(
        "dd.sqlserver.async_job.inactive_stop",
        tags=['job:query-metrics'] + _expected_dbm_instance_tags(dbm_instance),
        hostname='',
    )


@not_windows_ci
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_async_job_cancel_cancel(aggregator, dd_run_check, dbm_instance):
    dbm_instance['query_metrics']['run_sync'] = False
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.cancel()
    # wait for it to stop and make sure it doesn't throw any exceptions
    check.statement_metrics._job_loop_future.result()
    assert not check.statement_metrics._job_loop_future.running(), "metrics thread should be stopped"
    # if the thread doesn't start until after the cancel signal is set then the db connection will never
    # be created in the first place
    aggregator.assert_metric(
        "dd.sqlserver.async_job.cancel",
        tags=_expected_dbm_instance_tags(dbm_instance) + ['job:query-metrics'],
    )
