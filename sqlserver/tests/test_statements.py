# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import logging
import math
import os
import re
import time
from collections import namedtuple
from concurrent.futures.thread import ThreadPoolExecutor
from copy import copy
from unittest.mock import ANY

import mock
import pytest
from lxml import etree as ET

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.serialization import json
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import (
    ENGINE_EDITION_ENTERPRISE,
    ENGINE_EDITION_EXPRESS,
    ENGINE_EDITION_PERSONAL,
    ENGINE_EDITION_STANDARD,
)
from datadog_checks.sqlserver.statements import SQL_SERVER_QUERY_METRICS_COLUMNS, obfuscate_xml_plan

from .common import CHECK_NAME, OPERATION_TIME_METRIC_NAME

try:
    import pyodbc
except ImportError:
    pyodbc = None

SELF_HOSTED_ENGINE_EDITIONS = {
    ENGINE_EDITION_PERSONAL,
    ENGINE_EDITION_STANDARD,
    ENGINE_EDITION_ENTERPRISE,
    ENGINE_EDITION_EXPRESS,
}


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['min_collection_interval'] = 1
    instance_docker['procedure_metrics'] = {'enabled': False}
    instance_docker['collect_settings'] = {'enabled': False}
    instance_docker['query_activity'] = {'enabled': False}
    # set a very small collection interval so the tests go fast
    instance_docker['query_metrics'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.1,
        # in tests sometimes things can slow down so we don't want this short deadline causing some events
        # to fail to be collected on time
        'enforce_collection_interval_deadline': False,
    }
    return copy(instance_docker)


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
def test_get_available_query_metrics_columns(dbm_instance, expected_columns, available_columns):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.initialize_connection()
    _conn_key_prefix = "dbm-"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            result_available_columns = check.statement_metrics._get_available_query_metrics_columns(
                cursor, expected_columns
            )
            assert result_available_columns == available_columns


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
    "database,query,expected_queries_patterns,param_groups,exe_count,is_encrypted,is_proc,disable_secondary_tags",
    [
        [
            "master",
            "EXEC multiQueryProc",
            [
                r"select @total = @total \+ count\(\*\) from sys\.databases where name like '%_'",
                r"select @total = @total \+ count\(\*\) from sys\.sysobjects where type = 'U'",
            ],
            ((),),
            1,
            False,
            True,
            True,
        ],
        [
            "master",
            "EXEC multiQueryProc",
            [
                r"select @total = @total \+ count\(\*\) from sys\.databases where name like '%_'",
                r"select @total = @total \+ count\(\*\) from sys\.sysobjects where type = 'U'",
            ],
            ((),),
            5,
            False,
            True,
            True,
        ],
        [
            "master",
            "EXEC encryptedProc",
            [""],
            ((),),
            5,
            True,
            True,
            True,
        ],
        [
            "datadog_test",
            "SELECT * FROM ϑings",
            [r"SELECT \* FROM ϑings"],
            ((),),
            1,
            False,
            False,
            False,
        ],
        [
            "datadog_test",
            "SELECT * FROM ϑings where id = ?",
            [r"SELECT \* FROM ϑings where id = @P1"],
            (
                (1,),
                (2,),
                (3,),
            ),
            1,
            False,
            False,
            False,
        ],
        [
            "datadog_test",
            "EXEC bobProc",
            [r"SELECT \* FROM ϑings"],
            ((),),
            1,
            False,
            True,
            True,
        ],
        [
            "datadog_test",
            "EXEC bobProc",
            [r"SELECT \* FROM ϑings"],
            ((),),
            10,
            False,
            True,
            True,
        ],
        [
            "master",
            "SELECT * FROM datadog_test.dbo.ϑings where id = ?",
            [r"SELECT \* FROM datadog_test.dbo.ϑings where id = @P1"],
            (
                (1,),
                (2,),
                (3,),
            ),
            1,
            False,
            False,
            False,
        ],
        [
            "datadog_test",
            "SELECT * FROM ϑings where id = ? and name = ?",
            [r"SELECT \* FROM ϑings where id = @P1 and name = @P2"],
            (
                (1, "hello"),
                (2, "there"),
                (3, "bill"),
            ),
            1,
            False,
            False,
            False,
        ],
        [
            "datadog_test",
            "SELECT * FROM ϑings where id = ?",
            [r"SELECT \* FROM ϑings where id = @P1"],
            (
                (1,),
                (2,),
                (3,),
            ),
            1,
            False,
            False,
            True,
        ],
        [
            "datadog_test",
            "EXEC bobProcParams @P1 = ?, @P2 = ?",
            [
                r"SELECT \* FROM ϑings WHERE id = @P1",
                r"SELECT id FROM ϑings WHERE name = @P2",
            ],
            (
                (1, "foo"),
                (2, "bar"),
            ),
            1,
            False,
            True,
            True,
        ],
        [
            "datadog_test",
            "EXEC bobProcParams @P1 = ?, @P2 = ?",
            [
                r"SELECT \* FROM ϑings WHERE id = @P1",
                r"SELECT id FROM ϑings WHERE name = @P2",
            ],
            (
                (1, "foo"),
                (2, "bar"),
            ),
            5,
            False,
            True,
            True,
        ],
    ],
)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(*test_statement_metrics_and_plans_parameterized)
def test_statement_metrics_and_plans(
    aggregator,
    dd_run_check,
    dbm_instance,
    bob_conn,
    database,
    query,
    param_groups,
    exe_count,
    is_encrypted,
    is_proc,
    disable_secondary_tags,
    expected_queries_patterns,
    caplog,
    datadog_agent,
):
    caplog.set_level(logging.INFO)
    if disable_secondary_tags:
        dbm_instance['query_metrics']['disable_secondary_tags'] = True
    dbm_instance['query_activity'] = {'enabled': True, 'collection_interval': 2}
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    # the check must be run three times:
    # 1) set _last_stats_query_time (this needs to happen before the 1st test queries to ensure the query time
    # interval is correct)
    # 2) load the test queries into the StatementMetrics state
    # 3) emit the query metrics based on the diff of current and last state
    dd_run_check(check)
    for _ in range(0, exe_count):
        for params in param_groups:
            bob_conn.execute_with_retries(query, params, database=database)
    dd_run_check(check)
    aggregator.reset()
    for _ in range(0, exe_count):
        for params in param_groups:
            bob_conn.execute_with_retries(query, params, database=database)
    dd_run_check(check)

    _conn_key_prefix = "dbm-"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            available_query_metrics_columns = check.statement_metrics._get_available_query_metrics_columns(
                cursor, SQL_SERVER_QUERY_METRICS_COLUMNS
            )

    instance_tags = dbm_instance.get('tags', [])
    expected_instance_tags = {t for t in instance_tags if not t.startswith('dd.internal')}
    expected_instance_tags_with_db = expected_instance_tags | {"db:{}".format(database)}

    # dbm-metrics
    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(dbm_metrics) == 1, "should have collected exactly one dbm-metrics payload"
    payload = next((n for n in dbm_metrics if n.get('kind') == 'query_metrics'), None)
    # host metadata
    assert payload['sqlserver_version'].startswith("Microsoft SQL Server"), "invalid version"
    assert payload['host'] == "stubbed.hostname", "wrong hostname"
    assert payload['ddagenthostname'] == datadog_agent.get_hostname()
    tags = set(payload['tags'])
    assert tags == expected_instance_tags, "wrong instance tags for dbm-metrics event"
    assert not any("dd.internal" in m for m in tags), "emitted dd.internal metrics from check"
    assert type(payload['min_collection_interval']) in (float, int), "invalid min_collection_interval"
    # metrics rows
    sqlserver_rows = payload.get('sqlserver_rows', [])
    assert sqlserver_rows, "should have collected some sqlserver query metrics rows"
    match_pattern = "(" + ")|(".join(expected_queries_patterns) + ")"
    if is_encrypted:
        matching_rows = [r for r in sqlserver_rows if not r['text']]
    else:
        matching_rows = [r for r in sqlserver_rows if re.match(match_pattern, r['text'], re.IGNORECASE)]
    assert len(matching_rows) == len(expected_queries_patterns), "missing expected matching rows"
    total_execution_count = sum([r['execution_count'] for r in matching_rows])
    assert (
        total_execution_count == len(param_groups) * len(expected_queries_patterns) * exe_count
    ), "wrong execution count"
    for row in matching_rows:
        if is_encrypted:
            # we get NULL text for encrypted statements so we have no calculated query signature
            assert not row['query_signature']
        else:
            assert row['query_signature'], "missing query signature"
        assert 'statement_text' not in row, "statement_text field should not be forwarded"
        assert row['is_encrypted'] == is_encrypted
        if not is_encrypted:
            assert row['is_proc'] == is_proc
        if is_proc and not is_encrypted:
            assert row['procedure_signature'], "missing proc signature"
            assert row['procedure_name'], "missing proc name"
        if disable_secondary_tags:
            assert 'database_name' not in row
        else:
            assert row['database_name'] == database, "incorrect database_name"
        for column in available_query_metrics_columns:
            assert column in row, "missing required metrics column {}".format(column)
            assert type(row[column]) in (float, int), "wrong type for metrics column {}".format(column)
    # all the plan handles / proc sigs should be the same for the same procedure execution
    if is_proc:
        assert all(row['plan_handle'] == matching_rows[0]['plan_handle'] for row in matching_rows)
    if is_proc and not is_encrypted:
        assert all(row['procedure_signature'] == matching_rows[0]['procedure_signature'] for row in matching_rows)
        assert all(row['procedure_name'] == matching_rows[0]['procedure_name'] for row in matching_rows)

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    assert dbm_samples, "should have collected at least one sample"

    if is_encrypted:
        matching_samples = [s for s in dbm_samples if not s['db']['statement']]
    else:
        matching_samples = [s for s in dbm_samples if re.search(match_pattern, s['db']['statement'], re.IGNORECASE)]

    assert matching_samples, "should have collected some matching samples"

    # validate common host fields
    for event in matching_samples:
        assert event['host'] == "stubbed.hostname", "wrong hostname"
        assert event['ddsource'] == "sqlserver", "wrong source"
        assert event['ddagentversion'], "missing ddagentversion"
        if disable_secondary_tags:
            assert set(event['ddtags'].split(',')) == expected_instance_tags, "wrong instance tags for plan event"
        else:
            assert (
                set(event['ddtags'].split(',')) == expected_instance_tags_with_db
            ), "wrong instance tags for plan event"

    plan_events = [s for s in matching_samples if s['dbm_type'] == "plan"]
    # plan sampling should limit the number of plans we collect per query/ proc
    # to one, despite changing parameters or mult queries in a single proc
    assert len(plan_events) == 1, "should have collected exactly one plan event"

    for event in plan_events:
        if is_encrypted:
            assert not event['db']['plan']['definition']
            assert event['sqlserver']['is_plan_encrypted']
            assert event['sqlserver']['is_statement_encrypted']
        elif is_proc:
            assert event['db']['procedure_signature'], "missing proc signature"
            assert event['db']['procedure_name'], "missing proc name"
            assert not event['db']['query_signature'], "procedure plans should not have query_signature field set"
        else:
            assert event['db']['plan']['definition'], "event plan definition missing"
            parsed_plan = ET.fromstring(event['db']['plan']['definition'])
            assert parsed_plan.tag.endswith("ShowPlanXML"), "plan does not match expected structure"
            assert not event['sqlserver']['is_plan_encrypted']
            assert not event['sqlserver']['is_statement_encrypted']

    fqt_events = [s for s in matching_samples if s['dbm_type'] == "fqt"]
    assert len(fqt_events) == len(
        expected_queries_patterns
    ), "should have collected an FQT event per unique query signature"

    # internal debug metrics
    aggregator.assert_metric(
        OPERATION_TIME_METRIC_NAME,
        tags=['agent_hostname:stubbed.hostname', 'operation:collect_statement_metrics_and_plans']
        + _expected_dbm_instance_tags(dbm_instance),
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "database,query,expected_queries_patterns,",
    [
        [
            "master",
            "EXEC multiQueryProc",
            [
                r"select @total = @total \+ count\(\*\) from sys\.databases where name like '%_'",
                r"select @total = @total \+ count\(\*\) from sys\.sysobjects where type = 'U'",
            ],
        ]
    ],
)
def test_statement_metrics_limit(
    aggregator, dd_run_check, dbm_instance, bob_conn, database, query, expected_queries_patterns
):
    dbm_instance['query_metrics']['max_queries'] = 5
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    # the check must be run three times:
    # 1) set _last_stats_query_time (this needs to happen before the 1st test queries to ensure the query time
    # interval is correct)
    # 2) load the test queries into the StatementMetrics state
    # 3) emit the query metrics based on the diff of current and last state
    dd_run_check(check)
    bob_conn.execute_with_retries(query, (), database=database)
    dd_run_check(check)
    aggregator.reset()
    bob_conn.execute_with_retries(query, (), database=database)
    dd_run_check(check)

    # dbm-metrics
    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(dbm_metrics) == 1, "should have collected exactly one dbm-metrics payload"
    payload = next((n for n in dbm_metrics if n.get('kind') == 'query_metrics'), None)
    # metrics rows
    sqlserver_rows = payload.get('sqlserver_rows', [])
    assert sqlserver_rows, "should have collected some sqlserver query metrics rows"
    assert len(sqlserver_rows) == dbm_instance['query_metrics']['max_queries']

    # check that it's sorted
    assert sqlserver_rows == sorted(sqlserver_rows, key=lambda i: i['total_elapsed_time'], reverse=True)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "metadata,expected_metadata_payload",
    [
        (
            {'tables_csv': 'sys.databases', 'commands': ['SELECT']},
            {'tables': ['sys.databases'], 'commands': ['SELECT']},
        ),
        (
            {'tables_csv': '', 'commands': None},
            {'tables': None, 'commands': None},
        ),
    ],
)
def test_statement_metadata(
    aggregator, dd_run_check, dbm_instance, bob_conn, datadog_agent, metadata, expected_metadata_payload
):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    query = "select * from sys.databases /* service='datadog-agent' */"
    query_signature = '6d1d070f9b6c5647'

    def _run_query():
        bob_conn.execute_with_retries(query)

    def _obfuscate_sql(sql_query, options=None):
        return json.dumps({'query': sql_query, 'metadata': metadata})

    # Execute the query with the mocked obfuscate_sql. The result should produce an event payload with the metadata.
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = _obfuscate_sql
        _run_query()
        dd_run_check(check)
        _run_query()
        dd_run_check(check)

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    assert dbm_samples, "should have collected at least one sample"

    matching = [s for s in dbm_samples if s['db']['query_signature'] == query_signature and s['dbm_type'] == 'plan']
    assert len(matching) == 1
    sample = matching[0]
    assert sample['db']['metadata']['tables'] == expected_metadata_payload['tables']
    assert sample['db']['metadata']['commands'] == expected_metadata_payload['commands']
    assert sample['db']['metadata']['comments'] == ["/* service='datadog-agent' */"]

    fqt_samples = [
        s for s in dbm_samples if s.get('dbm_type') == 'fqt' and s['db']['query_signature'] == query_signature
    ]
    assert len(fqt_samples) == 1
    fqt = fqt_samples[0]
    assert fqt['db']['metadata']['tables'] == expected_metadata_payload['tables']
    assert fqt['db']['metadata']['commands'] == expected_metadata_payload['commands']
    assert fqt['db']['metadata']['comments'] == ["/* service='datadog-agent' */"]

    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(dbm_metrics) == 1
    metric = dbm_metrics[0]
    matching_metrics = [m for m in metric['sqlserver_rows'] if m['query_signature'] == query_signature]
    assert len(matching_metrics) == 1
    metric = matching_metrics[0]
    assert metric['dd_tables'] == expected_metadata_payload['tables']
    assert metric['dd_commands'] == expected_metadata_payload['commands']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "input_cloud_metadata,output_cloud_metadata",
    [
        ({}, {}),
        (
            {
                'azure': {
                    'deployment_type': 'managed_instance',
                    'name': 'my-instance.abcea3661b20.database.windows.net',
                },
            },
            {
                'azure': {
                    'deployment_type': 'managed_instance',
                    'name': 'my-instance.abcea3661b20.database.windows.net',
                },
            },
        ),
        (
            {
                'azure': {
                    'deployment_type': 'managed_instance',
                    'fully_qualified_domain_name': 'my-instance.abcea3661b20.database.windows.net',
                },
            },
            {
                'azure': {
                    'deployment_type': 'managed_instance',
                    'name': 'my-instance.abcea3661b20.database.windows.net',
                },
            },
        ),
        (
            {
                'aws': {
                    'instance_endpoint': 'foo.aws.com',
                },
                'azure': {
                    'deployment_type': 'managed_instance',
                    'name': 'my-instance.abcea3661b20.database.windows.net',
                },
            },
            {
                'aws': {
                    'instance_endpoint': 'foo.aws.com',
                },
                'azure': {
                    'deployment_type': 'managed_instance',
                    'name': 'my-instance.abcea3661b20.database.windows.net',
                },
            },
        ),
        (
            {
                'gcp': {
                    'project_id': 'foo-project',
                    'instance_id': 'bar',
                    'extra_field': 'included',
                },
            },
            {
                'gcp': {
                    'project_id': 'foo-project',
                    'instance_id': 'bar',
                    'extra_field': 'included',
                },
            },
        ),
    ],
)
def test_statement_cloud_metadata(
    aggregator, dd_run_check, dbm_instance, bob_conn, datadog_agent, input_cloud_metadata, output_cloud_metadata
):
    if input_cloud_metadata:
        for k, v in input_cloud_metadata.items():
            dbm_instance[k] = v
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    query = 'SELECT * FROM ϑings'

    def _run_query():
        bob_conn.execute_with_retries(query, (), database="datadog_test")

    # the check must be run three times:
    # 1) set _last_stats_query_time (this needs to happen before the 1st test queries to ensure the query time
    # interval is correct)
    # 2) load the test queries into the StatementMetrics state
    # 3) emit the query metrics based on the diff of current and last state
    _run_query()
    dd_run_check(check)
    _run_query()
    dd_run_check(check)
    aggregator.reset()
    _run_query()
    dd_run_check(check)

    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(dbm_metrics) == 1, "should have collected exactly one metrics payload"
    payload = next((n for n in dbm_metrics if n.get('kind') == 'query_metrics'), None)
    # host metadata
    assert payload['sqlserver_version'].startswith("Microsoft SQL Server"), "invalid version"
    assert payload['host'] == "stubbed.hostname", "wrong hostname"
    assert payload['ddagenthostname'] == datadog_agent.get_hostname()
    # cloud metadata
    assert payload['cloud_metadata'] == output_cloud_metadata, "wrong cloud_metadata"
    # test that we're reading the edition out of the db instance. Note that this edition is what
    # is running in our test docker containers, so it's not expected to match the test cloud metadata
    assert payload['sqlserver_engine_edition'] in SELF_HOSTED_ENGINE_EDITIONS, "wrong edition"


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "reported_hostname,expected_hostname",
    [
        (None, 'stubbed.hostname'),
        ('override.hostname', 'override.hostname'),
    ],
)
def test_statement_reported_hostname(
    aggregator, dd_run_check, dbm_instance, bob_conn, datadog_agent, reported_hostname, expected_hostname
):
    dbm_instance['reported_hostname'] = reported_hostname
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    dd_run_check(check)
    dd_run_check(check)

    samples = aggregator.get_event_platform_events("dbm-samples")
    assert samples, "should have collected at least one sample"
    assert samples[0]['host'] == expected_hostname

    fqt_samples = [s for s in samples if s.get('dbm_type') == 'fqt']
    assert fqt_samples, "should have collected at least one fqt sample"
    assert fqt_samples[0]['host'] == expected_hostname

    metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert metrics, "should have collected metrics"
    assert metrics[0]['host'] == expected_hostname


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
        lookback_seconds = math.ceil(time.time() - now) + 60
        params = (lookback_seconds,)
        logging.debug("running statement_metrics_query [%s] %s", statement_metrics_query, params)
        cursor.execute(statement_metrics_query, params)

        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        matching = [r for r in rows if r['statement_text'] == test_query]
        assert matching, "the test query should be visible in the query stats, found all rows: {}".format(rows)
        row = matching[0]

        cursor.execute(
            "select count(*) from sys.dm_exec_query_stats where query_hash = ? and query_plan_hash = ?",
            row['query_hash'],
            row['query_plan_hash'],
        )

        assert cursor.fetchall()[0][0] >= 1, "failed to read back the same query stats using the query and plan hash"


XML_PLANS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xml_plans")


@pytest.mark.parametrize("slow_plans", [True, False])
@pytest.mark.skip(reason="skip to see if this test is why the tests get stuck")
def test_plan_collection_deadline(aggregator, dd_run_check, dbm_instance, slow_plans):
    dbm_instance['query_metrics']['enforce_collection_interval_deadline'] = True

    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    def _mock_slow_load_plan(*_):
        if not slow_plans:
            check.log.debug("_mock_slow_load_plan instant return")
            return
        interval = dbm_instance['query_metrics']['collection_interval']
        check.log.debug("_mock_slow_load_plan sleeping %s seconds", interval)
        time.sleep(interval)

    aggregator.reset()

    with mock.patch.object(check.statement_metrics, '_load_plan', passthrough=True) as mock_obj:
        mock_obj.side_effect = _mock_slow_load_plan
        dd_run_check(check)

    expected_debug_tags = ['agent_hostname:stubbed.hostname'] + _expected_dbm_instance_tags(dbm_instance)

    if slow_plans:
        aggregator.assert_metric("dd.sqlserver.statements.deadline_exceeded", tags=expected_debug_tags)
    else:
        aggregator.assert_metric("dd.sqlserver.statements.deadline_exceeded", count=0)


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


def _mock_sql_obfuscate(sql_string, options=None):
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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "database,query,",
    [
        [
            "master",
            "EXEC conditionalPlanTest @Switch = 1",
        ]
    ],
)
def test_statement_conditional_stored_procedure_with_temp_table(
    aggregator, dd_run_check, dbm_instance, bob_conn, database, query
):
    # This test covers a very special case where a stored procedure has a conditional branch
    # and uses temp tables. The plan will be NULL if there are any statements involving temp tables that
    # have not been executed. We simulate the case by running the stored procedure with a parameter that
    # only executes the first branch of the conditional. The second branch will not be executed and the
    # plan will be NULL. That being said, ALL executed statements in the stored procedure will have NULL plan.
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])

    dd_run_check(check)
    bob_conn.execute_with_retries(query, (), database=database)
    dd_run_check(check)
    aggregator.reset()
    bob_conn.execute_with_retries(query, (), database=database)
    dd_run_check(check)

    # dbm-metrics
    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(dbm_metrics) == 1, "should have collected exactly one dbm-metrics payload"
    payload = dbm_metrics[0]
    # metrics rows
    sqlserver_rows = payload.get('sqlserver_rows', [])
    assert sqlserver_rows, "should have collected some sqlserver query metrics rows"

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    assert dbm_samples, "should have collected at least one sample"

    matched_events = [s for s in dbm_samples if s['dbm_type'] == "plan" and "#Ids" in s['db']['statement']]
    assert matched_events, "should have collected plan event"

    for event in matched_events:
        assert event['db']['plan']['definition'] is None
        assert event['sqlserver']['plan_handle'] is not None
        assert event['sqlserver']['query_hash'] is not None
        assert event['sqlserver']['query_plan_hash'] is not None


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
def test_statement_stored_procedure_characters_limit(
    aggregator, datadog_agent, dd_run_check, dbm_instance, bob_conn, stored_procedure_characters_limit
):
    dbm_instance['stored_procedure_characters_limit'] = stored_procedure_characters_limit
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    query = "EXEC procedureWithLargeCommment;"

    def _obfuscate_sql(sql_query, options=None):
        if "PROCEDURE procedureWithLargeCommment" in sql_query and len(sql_query) >= stored_procedure_characters_limit:
            raise Exception('failed to obfuscate')
        return json.dumps({'query': sql_query, 'metadata': {}})

    # Execute the query with the mocked obfuscate_sql. The result should produce an event payload with the metadata.
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = _obfuscate_sql
        dd_run_check(check)
        bob_conn.execute_with_retries(query, (), database="datadog_test")
        dd_run_check(check)
        aggregator.reset()
        bob_conn.execute_with_retries(query, (), database="datadog_test")
        dd_run_check(check)

    # dbm-metrics
    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(dbm_metrics) == 1, "should have collected exactly one dbm-metrics payload"
    payload = dbm_metrics[0]
    # metrics rows
    sqlserver_rows = payload.get('sqlserver_rows', [])
    assert sqlserver_rows, "should have collected some sqlserver query metrics rows"

    matched_rows = [s for s in sqlserver_rows if s.get("procedure_name") == "procedurewithlargecommment"]
    if stored_procedure_characters_limit > 500:
        assert matched_rows, "should have collected the metric row with expected procedure name"
        assert "procedure_signature" in matched_rows[0]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_statement_with_embedded_characters(aggregator, datadog_agent, dd_run_check, dbm_instance, bob_conn):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    query = "EXEC nullCharTest;"

    def _obfuscate_sql(sql_query, options=None):
        return json.dumps({'query': sql_query, 'metadata': {}})

    # Execute the query with the mocked obfuscate_sql. The result should produce an event payload with the metadata.
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = _obfuscate_sql
        dd_run_check(check)
        bob_conn.execute_with_retries(query, (), database="datadog_test")
        dd_run_check(check)
        aggregator.reset()
        bob_conn.execute_with_retries(query, (), database="datadog_test")
        dd_run_check(check)

    # dbm-metrics
    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(dbm_metrics) == 1, "should have collected exactly one dbm-metrics payload"
    payload = dbm_metrics[0]
    # metrics rows
    sqlserver_rows = payload.get('sqlserver_rows', [])
    assert sqlserver_rows, "should have collected some sqlserver query metrics rows"

    matched_rows = [s for s in sqlserver_rows if s.get("procedure_name") == "nullchartest"]
    assert matched_rows, "should have collected the metric row with expected procedure name"
    assert "text" in matched_rows[0]
    assert "\x00" not in matched_rows[0]["text"]


def _mock_database_list():
    Row = namedtuple('Row', 'name')
    fetchall_results = [
        Row('master'),
        Row('tempdb'),
        Row('msdb'),
        Row('AdventureWorks2017'),
        Row('CaseSensitive2018'),
        Row('Fancy2020db'),
    ]
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchall.return_value = iter(fetchall_results)
    # check excluded overrides included
    mock_cursor.fetchall.return_value = iter(fetchall_results)
    return fetchall_results, mock_cursor


@pytest.mark.unit
def test_metrics_lookback_multiplier(instance_docker):
    instance_docker['query_metrics'] = {'collection_interval': 3}
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    _, mock_cursor = _mock_database_list()

    check.statement_metrics._load_raw_query_metrics_rows(mock_cursor)
    mock_cursor.execute.assert_called_with(ANY, (6,))
