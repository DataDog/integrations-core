# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
import time
from collections import Counter
from concurrent.futures.thread import ThreadPoolExecutor

import mock
import psycopg2
import pytest
from semver import VersionInfo
from six import string_types

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.serialization import json
from datadog_checks.postgres.statement_samples import DBExplainError, StatementTruncationState
from datadog_checks.postgres.statements import PG_STAT_STATEMENTS_METRICS_COLUMNS

from .common import DB_NAME, HOST, PORT, POSTGRES_VERSION

SAMPLE_QUERIES = [
    # (username, password, dbname, query, arg)
    ("bob", "bob", "datadog_test", "SELECT city FROM persons WHERE city = %s", "hello"),
    (
        "bob",
        "bob",
        "datadog_test",
        "SELECT hello_how_is_it_going_this_is_a_very_long_table_alias_name.personid, "
        "hello_how_is_it_going_this_is_a_very_long_table_alias_name.lastname "
        "FROM persons hello_how_is_it_going_this_is_a_very_long_table_alias_name JOIN persons B "
        "ON hello_how_is_it_going_this_is_a_very_long_table_alias_name.personid = B.personid WHERE B.city = %s",
        "hello",
    ),
    ("dd_admin", "dd_admin", "dogs", "SELECT * FROM breed WHERE name = %s", "Labrador"),
]

dbm_enabled_keys = ["dbm", "deep_database_monitoring"]


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.mark.parametrize("dbm_enabled_key", dbm_enabled_keys)
@pytest.mark.parametrize("dbm_enabled", [True, False])
def test_dbm_enabled_config(integration_check, dbm_instance, dbm_enabled_key, dbm_enabled):
    # test to make sure we continue to support the old key
    for k in dbm_enabled_keys:
        dbm_instance.pop(k, None)
    dbm_instance[dbm_enabled_key] = dbm_enabled
    check = integration_check(dbm_instance)
    assert check._config.dbm_enabled == dbm_enabled


statement_samples_keys = ["query_samples", "statement_samples"]


@pytest.mark.parametrize("statement_samples_key", statement_samples_keys)
@pytest.mark.parametrize("statement_samples_enabled", [True, False])
def test_statement_samples_enabled_config(
    integration_check, dbm_instance, statement_samples_key, statement_samples_enabled
):
    # test to make sure we continue to support the old key
    for k in statement_samples_keys:
        dbm_instance.pop(k, None)
    dbm_instance[statement_samples_key] = {'enabled': statement_samples_enabled}
    check = integration_check(dbm_instance)
    assert check.statement_samples._enabled == statement_samples_enabled


@pytest.mark.parametrize(
    "version,expected_payload_version",
    [
        (VersionInfo(*[9, 6, 0]), "v9.6.0"),
        (None, ""),
    ],
)
def test_statement_metrics_version(integration_check, dbm_instance, version, expected_payload_version):
    if version:
        check = integration_check(dbm_instance)
        check._version = version
        check._connect()
        assert check.statement_metrics._payload_pg_version() == expected_payload_version
    else:
        with mock.patch(
            'datadog_checks.postgres.postgres.PostgreSql.version', new_callable=mock.PropertyMock
        ) as patched_version:
            patched_version.return_value = None
            check = integration_check(dbm_instance)
            check._connect()
            assert check.statement_metrics._payload_pg_version() == expected_payload_version


@pytest.mark.parametrize("dbstrict", [True, False])
@pytest.mark.parametrize("pg_stat_statements_view", ["pg_stat_statements", "datadog.pg_stat_statements()"])
def test_statement_metrics(
    aggregator, integration_check, dbm_instance, dbstrict, pg_stat_statements_view, datadog_agent
):
    dbm_instance['dbstrict'] = dbstrict
    dbm_instance['pg_stat_statements_view'] = pg_stat_statements_view
    # don't need samples for this test
    dbm_instance['query_samples'] = {'enabled': False}
    # very low collection interval for test purposes
    dbm_instance['query_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    connections = {}

    def _run_queries():
        for user, password, dbname, query, arg in SAMPLE_QUERIES:
            if dbname not in connections:
                connections[dbname] = psycopg2.connect(host=HOST, dbname=dbname, user=user, password=password)
            connections[dbname].cursor().execute(query, (arg,))

    check = integration_check(dbm_instance)
    check._connect()

    _run_queries()
    check.check(dbm_instance)
    _run_queries()
    check.check(dbm_instance)

    def _should_catch_query(dbname):
        # we can always catch it if the query originals in the same DB
        # when dbstrict=True we expect to only capture those queries for the initial database to which the
        # agent is connecting
        if POSTGRES_VERSION.split('.')[0] == "9" and pg_stat_statements_view == "pg_stat_statements":
            # cannot catch any queries from other users
            # only can see own queries
            return False
        if dbstrict and dbname != dbm_instance['dbname']:
            return False
        return True

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 1
    event = events[0]

    assert event['host'] == 'stubbed.hostname'
    assert event['timestamp'] > 0
    assert event['postgres_version'] == check.statement_metrics._payload_pg_version()
    assert event['ddagentversion'] == datadog_agent.get_version()
    assert event['min_collection_interval'] == dbm_instance['query_metrics']['collection_interval']
    expected_dbm_metrics_tags = {'foo:bar', 'port:{}'.format(PORT)}
    assert set(event['tags']) == expected_dbm_metrics_tags
    obfuscated_param = '?' if POSTGRES_VERSION.split('.')[0] == "9" else '$1'

    assert len(aggregator.metrics("postgresql.pg_stat_statements.max")) != 0
    assert len(aggregator.metrics("postgresql.pg_stat_statements.count")) != 0
    dbm_samples = aggregator.get_event_platform_events("dbm-samples")

    for username, _, dbname, query, _ in SAMPLE_QUERIES:
        expected_query = query % obfuscated_param
        query_signature = compute_sql_signature(expected_query)
        matching_rows = [r for r in event['postgres_rows'] if r['query_signature'] == query_signature]
        if not _should_catch_query(dbname):
            assert len(matching_rows) == 0
            continue

        # metrics
        assert len(matching_rows) == 1
        row = matching_rows[0]
        assert row['calls'] == 1
        assert row['datname'] == dbname
        assert row['rolname'] == username
        assert row['query'] == expected_query[0:200], "query should be truncated when sending to metrics"
        available_columns = set(row.keys())
        metric_columns = available_columns & PG_STAT_STATEMENTS_METRICS_COLUMNS
        for col in metric_columns:
            assert type(row[col]) in (float, int)

        # full query text
        fqt_events = [e for e in dbm_samples if e.get('dbm_type') == 'fqt']
        assert len(fqt_events) > 0
        matching = [e for e in fqt_events if e['db']['query_signature'] == query_signature]
        assert len(matching) == 1
        fqt_event = matching[0]
        assert fqt_event['ddagentversion'] == datadog_agent.get_version()
        assert fqt_event['ddsource'] == "postgres"
        assert fqt_event['db']['statement'] == expected_query
        assert fqt_event['postgres']['datname'] == dbname
        assert fqt_event['postgres']['rolname'] == username
        assert fqt_event['timestamp'] > 0
        assert fqt_event['host'] == 'stubbed.hostname'
        assert set(fqt_event['ddtags'].split(',')) == expected_dbm_metrics_tags | {
            "db:" + fqt_event['postgres']['datname'],
            "rolname:" + fqt_event['postgres']['rolname'],
        }

    for conn in connections.values():
        conn.close()


def test_statement_metrics_with_duplicates(aggregator, integration_check, dbm_instance, datadog_agent):
    # don't need samples for this test
    dbm_instance['query_samples'] = {'enabled': False}
    # very low collection interval for test purposes
    dbm_instance['query_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}

    # The query signature matches the normalized query returned by the mock agent and would need to be
    # updated if the normalized query is updated
    query = 'select * from pg_stat_activity where application_name = ANY(%s);'
    query_signature = 'a478c1e7aaac3ff2'
    normalized_query = 'select * from pg_stat_activity where application_name = ANY(array [ ? ])'

    def obfuscate_sql(query, options=None):
        if query.startswith('select * from pg_stat_activity where application_name'):
            return normalized_query
        return query

    check = integration_check(dbm_instance)
    check._connect()
    cursor = check.db.cursor()

    # Execute the query once to begin tracking it. Execute again between checks to track the difference.
    # This should result in a single metric for that query_signature having a value of 2
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = obfuscate_sql
        cursor.execute(query, (['app1', 'app2'],))
        cursor.execute(query, (['app1', 'app2', 'app3'],))
        check.check(dbm_instance)
        cursor.execute(query, (['app1', 'app2'],))
        cursor.execute(query, (['app1', 'app2', 'app3'],))
        check.check(dbm_instance)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 1
    event = events[0]

    matching = [e for e in event['postgres_rows'] if e['query_signature'] == query_signature]
    assert len(matching) == 1
    row = matching[0]
    assert row['calls'] == 2


@pytest.fixture
def bob_conn():
    conn = psycopg2.connect(host=HOST, dbname=DB_NAME, user="bob", password="bob")
    yield conn
    conn.close()


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 1
    pg_instance['pg_stat_activity_view'] = "datadog.pg_stat_activity()"
    pg_instance['query_samples'] = {'enabled': True, 'run_sync': True, 'collection_interval': 1}
    pg_instance['query_activity'] = {'enabled': True, 'collection_interval': 1}
    pg_instance['query_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 10}
    return pg_instance


def _expected_dbm_instance_tags(dbm_instance):
    return dbm_instance['tags'] + [
        'port:{}'.format(PORT),
        'db:{}'.format(dbm_instance['dbname']),
    ]


@pytest.mark.parametrize(
    "dbname,expected_db_explain_error",
    [
        ("datadog_test", None),
        ("dogs", None),
        ("dogs_noschema", DBExplainError.invalid_schema),
        ("dogs_nofunc", DBExplainError.failed_function),
    ],
)
def test_get_db_explain_setup_state(integration_check, dbm_instance, dbname, expected_db_explain_error):
    check = integration_check(dbm_instance)
    check._connect()
    db_explain_error, err = check.statement_samples._get_db_explain_setup_state(dbname)
    assert db_explain_error == expected_db_explain_error


failed_explain_test_repeat_count = 5


@pytest.mark.parametrize(
    "query,expected_error_tag,explain_function_override,expected_fail_count",
    [
        ("select * from fake_table", "error:explain-<class 'psycopg2.errors.UndefinedTable'>", None, 1),
        ("select * from fake_schema.fake_table", "error:explain-<class 'psycopg2.errors.UndefinedTable'>", None, 1),
        (
            "select * from pg_settings where name = $1",
            "error:explain-<class 'psycopg2.errors.UndefinedParameter'>",
            None,
            1,
        ),
        (
            "select * from pg_settings where name = 'this query is truncated' limi",
            "error:explain-<class 'psycopg2.errors.SyntaxError'>",
            None,
            1,
        ),
        (
            "select * from persons",
            "error:explain-<class 'psycopg2.errors.InsufficientPrivilege'>",
            "datadog.explain_statement_noaccess",
            failed_explain_test_repeat_count,
        ),
    ],
)
def test_failed_explain_handling(
    integration_check,
    dbm_instance,
    aggregator,
    query,
    expected_error_tag,
    explain_function_override,
    expected_fail_count,
):
    dbname = "datadog_test"
    if explain_function_override:
        dbm_instance['query_samples']['explain_function'] = explain_function_override
    check = integration_check(dbm_instance)
    check._connect()

    # run check so all internal state is correctly initialized
    check.check(dbm_instance)

    # clear out contents of aggregator so we measure only the metrics generated during this specific part of the test
    aggregator.reset()

    db_explain_error, err = check.statement_samples._get_db_explain_setup_state(dbname)
    assert db_explain_error is None
    assert err is None

    for _ in range(failed_explain_test_repeat_count):
        check.statement_samples._run_explain_safe(dbname, query, query, query)

    expected_tags = dbm_instance['tags'] + [
        'db:{}'.format(DB_NAME),
        'port:{}'.format(PORT),
        'agent_hostname:stubbed.hostname',
        expected_error_tag,
    ]

    aggregator.assert_metric(
        # even though we tried to explain the query multiple times, only a single error was registered, showing
        # that the cached error response was used
        'dd.postgres.statement_samples.error',
        count=expected_fail_count,
        tags=expected_tags,
        hostname='stubbed.hostname',
    )


@pytest.mark.parametrize("pg_stat_activity_view", ["pg_stat_activity", "datadog.pg_stat_activity()"])
@pytest.mark.parametrize(
    "user,password,dbname,query,arg,expected_error_tag,expected_collection_errors,expected_statement_truncated",
    [
        (
            "bob",
            "bob",
            "datadog_test",
            "SELECT city FROM persons WHERE city = %s",
            "hello",
            None,
            None,
            StatementTruncationState.not_truncated.value,
        ),
        (
            "dd_admin",
            "dd_admin",
            "dogs",
            "SELECT * FROM breed WHERE name = %s",
            "Labrador",
            None,
            None,
            StatementTruncationState.not_truncated.value,
        ),
        (
            "dd_admin",
            "dd_admin",
            "dogs_noschema",
            "SELECT * FROM kennel WHERE id = %s",
            123,
            "error:explain-{}".format(DBExplainError.invalid_schema),
            [{'code': 'invalid_schema', 'message': "<class 'psycopg2.errors.InvalidSchemaName'>"}],
            StatementTruncationState.not_truncated.value,
        ),
        (
            "dd_admin",
            "dd_admin",
            "dogs_nofunc",
            "SELECT * FROM kennel WHERE id = %s",
            123,
            "error:explain-{}".format(DBExplainError.failed_function),
            [{'code': 'failed_function', 'message': "<class 'psycopg2.errors.UndefinedFunction'>"}],
            StatementTruncationState.not_truncated.value,
        ),
        (
            "bob",
            "bob",
            "datadog_test",
            u"SELECT city as city0, city as city1, city as city2, city as city3, "
            "city as city4, city as city5, city as city6, city as city7, city as city8, city as city9, "
            "city as city10, city as city11, city as city12, city as city13, city as city14, city as city15, "
            "city as city16, city as city17, city as city18, city as city19, city as city20, city as city21, "
            "city as city22, city as city23, city as city24, city as city25, city as city26, city as city27, "
            "city as city28, city as city29, city as city30, city as city31, city as city32, city as city33, "
            "city as city34, city as city35, city as city36, city as city37, city as city38, city as city39, "
            "city as city40, city as city41, city as city42, city as city43, city as city44, city as city45, "
            "city as city46, city as city47, city as city48, city as city49, city as city50, city as city51, "
            "city as city52, city as city53, city as city54, city as city55, city as city56, city as city57, "
            "city as city58, city as city59, city as city60, city as city61 "
            "FROM persons WHERE city = %s",
            # Use some multi-byte characters (the euro symbol) so we can validate that the code is correctly
            # looking at the length in bytes when testing for truncated statements
            u'\u20AC\u20AC\u20AC\u20AC\u20AC\u20AC\u20AC\u20AC\u20AC\u20AC',
            "error:explain-{}".format(DBExplainError.query_truncated),
            [{'code': 'query_truncated', 'message': 'track_activity_query_size=1024'}],
            StatementTruncationState.truncated.value,
        ),
    ],
)
def test_statement_samples_collect(
    aggregator,
    integration_check,
    dbm_instance,
    pg_stat_activity_view,
    user,
    password,
    dbname,
    query,
    arg,
    expected_error_tag,
    expected_collection_errors,
    expected_statement_truncated,
    datadog_agent,
):
    dbm_instance['pg_stat_activity_view'] = pg_stat_activity_view
    check = integration_check(dbm_instance)
    check._connect()

    tags = dbm_instance['tags'] + [
        'port:{}'.format(PORT),
        'db:{}'.format(dbname),
    ]

    conn = psycopg2.connect(host=HOST, dbname=dbname, user=user, password=password)
    # we are able to see the full query (including the raw parameters) in pg_stat_activity because psycopg2 uses
    # the simple query protocol, sending the whole query as a plain string to postgres.
    # if a client is using the extended query protocol with prepare then the query would appear as
    # leave connection open until after the check has run to ensure we're able to see the query in
    # pg_stat_activity
    try:
        conn.cursor().execute(query, (arg,))
        check.check(dbm_instance)
        dbm_samples = aggregator.get_event_platform_events("dbm-samples")

        expected_query = query % ('\'' + arg + '\'' if isinstance(arg, string_types) else arg)

        # Find matching events by checking if the expected query starts with the event statement. Using this
        # instead of a direct equality check covers cases of truncated statements
        matching = [
            e for e in dbm_samples if expected_query.encode("utf-8").startswith(e['db']['statement'].encode("utf-8"))
        ]

        if POSTGRES_VERSION.split('.')[0] == "9" and pg_stat_activity_view == "pg_stat_activity":
            # pg_monitor role exists only in version 10+
            assert len(matching) == 0, "did not expect to catch any events"
            return

        assert len(matching) == 1, "missing captured event"
        event = matching[0]
        assert event['db']['query_truncated'] == expected_statement_truncated

        if expected_error_tag:
            assert event['db']['plan']['definition'] is None, "did not expect to collect an execution plan"
            aggregator.assert_metric(
                "dd.postgres.statement_samples.error",
                tags=tags + [expected_error_tag, 'agent_hostname:stubbed.hostname'],
                hostname='stubbed.hostname',
            )
        else:
            assert set(event['ddtags'].split(',')) == set(tags)
            assert event['db']['plan']['definition'] is not None, "missing execution plan"
            assert 'Plan' in json.loads(event['db']['plan']['definition']), "invalid json execution plan"
            # we expect to get a duration because the connections are in "idle" state
            assert event['duration']

        # validate the events to ensure we've provided an explanation for not providing an exec plan
        for event in matching:
            assert event['ddagentversion'] == datadog_agent.get_version()
            if event['db']['plan']['definition'] is None:
                assert event['db']['plan']['collection_errors'] == expected_collection_errors
            else:
                assert event['db']['plan']['collection_errors'] is None

    finally:
        conn.close()


@pytest.mark.parametrize("pg_stat_activity_view", ["pg_stat_activity", "datadog.pg_stat_activity()"])
@pytest.mark.parametrize(
    "user,password,dbname,query,arg,expected_out,expected_keys,expected_conn_out",
    [
        (
            "bob",
            "bob",
            "datadog_test",
            "SELECT city FROM pg_sleep(3), persons WHERE city = %s",
            "hello",
            {
                'datname': 'datadog_test',
                'usename': 'bob',
                'state': 'idle in transaction',
                'query_signature': 'd9193c18a6f372d8',
                'statement': "SELECT city FROM pg_sleep(3), persons WHERE city = 'hello'",
            },
            ["xact_start", "query_start", "pid", "client_port", "client_addr"],
            {
                'usename': 'bob',
                'state': 'idle in transaction',
                'application_name': '',
                'connections': 1,
            },
        ),
    ],
)
def test_activity_snapshot_collection(
    aggregator,
    integration_check,
    dbm_instance,
    datadog_agent,
    pg_stat_activity_view,
    user,
    password,
    dbname,
    query,
    arg,
    expected_out,
    expected_keys,
    expected_conn_out,
):
    dbm_instance['pg_stat_activity_view'] = pg_stat_activity_view
    check = integration_check(dbm_instance)
    check._connect()

    conn = psycopg2.connect(host=HOST, dbname=dbname, user=user, password=password)

    # we are able to see the full query (including the raw parameters) in pg_stat_activity because psycopg2 uses
    # the simple query protocol, sending the whole query as a plain string to postgres.
    # if a client is using the extended query protocol with prepare then the query would appear as
    # leave connection open until after the check has run to ensure we're able to see the query in
    # pg_stat_activity
    try:
        # turn off auto commit so we can manage transactions manually
        # this should allow us to catch queries in the 'idle in transaction' state
        conn.autocommit = False
        conn.cursor().execute(query, (arg,))
        check.check(dbm_instance)
        dbm_activity_event = aggregator.get_event_platform_events("dbm-activity")

        if POSTGRES_VERSION.split('.')[0] == "9" and pg_stat_activity_view == "pg_stat_activity":
            # cannot catch any queries from other users
            # only can see own queries
            return

        event = dbm_activity_event[0]
        assert event['host'] == "stubbed.hostname"
        assert event['ddsource'] == "postgres"
        assert event['dbm_type'] == "activity"
        assert event['ddagentversion'] == datadog_agent.get_version()
        assert len(event['postgres_activity']) > 0
        # find bob's query.
        bobs_query = None
        for query_json in event['postgres_activity']:
            if 'usename' in query_json and query_json['usename'] == "bob":
                bobs_query = query_json
        assert bobs_query is not None

        for key in expected_out:
            assert expected_out[key] == bobs_query[key]
        for val in expected_keys:
            assert val in bobs_query

        assert 'query' not in bobs_query

        expected_tags = dbm_instance['tags'] + [
            'port:{}'.format(PORT),
        ]

        # check postgres_connections are set
        assert len(event['postgres_connections']) > 0
        # find bob's connections.
        bobs_conns = None
        for query_json in event['postgres_connections']:
            if 'usename' in query_json and query_json['usename'] == "bob":
                bobs_conns = query_json
        assert bobs_conns is not None

        for key in expected_conn_out:
            assert expected_conn_out[key] == bobs_conns[key]

        assert event['ddtags'] == expected_tags

    finally:
        conn.close()


@pytest.mark.parametrize(
    "query,expected_err_tag,expected_explain_err_code,expected_err",
    [
        (
            "select * from fake_table",
            "error:explain-<class 'psycopg2.errors.UndefinedTable'>",
            DBExplainError.database_error,
            "<class 'psycopg2.errors.UndefinedTable'>",
        ),
        (
            "select * from pg_settings where name = $1",
            "error:explain-<class 'psycopg2.errors.UndefinedParameter'>",
            DBExplainError.database_error,
            "<class 'psycopg2.errors.UndefinedParameter'>",
        ),
        (
            "SELECT city as city0, city as city1, city as city2, city as city3, "
            "city as city4, city as city5, city as city6, city as city7, city as city8, city as city9, "
            "city as city10, city as city11, city as city12, city as city13, city as city14, city as city15, "
            "city as city16, city as city17, city as city18, city as city19, city as city20, city as city21, "
            "city as city22, city as city23, city as city24, city as city25, city as city26, city as city27, "
            "city as city28, city as city29, city as city30, city as city31, city as city32, city as city33, "
            "city as city34, city as city35, city as city36, city as city37, city as city38, city as city39, "
            "city as city40, city as city41, city as city42, city as city43, city as city44, city as city45, "
            "city as city46, city as city47, city as city48, city as city49, city as city50, city as city51, "
            "city as city52, city as city53, city as city54, city as city55, city as city56, city as city57, "
            "city as city58, city as city59, city as city60, city as city61 "
            "FROM persons WHERE city = 123",
            "error:explain-{}".format(DBExplainError.query_truncated),
            DBExplainError.query_truncated,
            "track_activity_query_size=1024",
        ),
    ],
)
def test_statement_run_explain_errors(
    integration_check,
    dbm_instance,
    aggregator,
    query,
    expected_err_tag,
    expected_explain_err_code,
    expected_err,
):
    check = integration_check(dbm_instance)
    check._connect()

    check.check(dbm_instance)
    _, explain_err_code, err = check.statement_samples._run_explain_safe("datadog_test", query, query, query)

    assert explain_err_code == expected_explain_err_code
    assert err == expected_err

    expected_tags = dbm_instance['tags'] + [
        'db:{}'.format(DB_NAME),
        'port:{}'.format(PORT),
        'agent_hostname:stubbed.hostname',
        expected_err_tag,
    ]

    aggregator.assert_metric(
        'dd.postgres.statement_samples.error',
        count=1,
        tags=expected_tags,
        hostname='stubbed.hostname',
    )


@pytest.mark.parametrize("dbstrict", [True, False])
def test_statement_samples_dbstrict(aggregator, integration_check, dbm_instance, dbstrict):
    dbm_instance["dbstrict"] = dbstrict
    check = integration_check(dbm_instance)
    check._connect()

    connections = []
    for user, password, dbname, query, arg in SAMPLE_QUERIES:
        conn = psycopg2.connect(host=HOST, dbname=dbname, user=user, password=password)
        conn.cursor().execute(query, (arg,))
        connections.append(conn)

    check.check(dbm_instance)
    dbm_samples = aggregator.get_event_platform_events("dbm-samples")

    for _, _, dbname, query, arg in SAMPLE_QUERIES:
        expected_query = query % ('\'' + arg + '\'' if isinstance(arg, string_types) else arg)
        matching = [e for e in dbm_samples if e['db']['statement'] == expected_query]
        if not dbstrict or dbname == dbm_instance['dbname']:
            # when dbstrict=True we expect to only capture those queries for the initial database to which the
            # agent is connecting
            assert len(matching) == 1, "missing captured event"
            event = matching[0]
            assert event["db"]["instance"] == dbname
        else:
            assert len(matching) == 0, "did not expect to capture an event"

    for conn in connections:
        conn.close()


@pytest.mark.parametrize("statement_samples_enabled", [True, False])
@pytest.mark.parametrize("statement_metrics_enabled", [True, False])
def test_async_job_enabled(integration_check, dbm_instance, statement_samples_enabled, statement_metrics_enabled):
    dbm_instance['query_samples'] = {'enabled': statement_samples_enabled, 'run_sync': False}
    dbm_instance['query_metrics'] = {'enabled': statement_metrics_enabled, 'run_sync': False}
    check = integration_check(dbm_instance)
    check._connect()
    check.check(dbm_instance)
    check.cancel()
    if statement_samples_enabled:
        assert check.statement_samples._job_loop_future is not None
        check.statement_samples._job_loop_future.result()
    else:
        assert check.statement_samples._job_loop_future is None
    if statement_metrics_enabled:
        assert check.statement_metrics._job_loop_future is not None
        check.statement_metrics._job_loop_future.result()
    else:
        assert check.statement_metrics._job_loop_future is None


@pytest.mark.parametrize("db_user", ["datadog", "datadog_no_catalog"])
def test_load_pg_settings(aggregator, integration_check, dbm_instance, db_user):
    dbm_instance["username"] = db_user
    dbm_instance["dbname"] = "postgres"
    check = integration_check(dbm_instance)
    check._connect()
    check._load_pg_settings(check.db)
    if db_user == 'datadog_no_catalog':
        aggregator.assert_metric(
            "dd.postgres.error",
            tags=_expected_dbm_instance_tags(dbm_instance)
            + ['error:load-pg-settings', 'agent_hostname:stubbed.hostname'],
            hostname='stubbed.hostname',
        )
    else:
        assert len(aggregator.metrics("dd.postgres.error")) == 0


def test_pg_settings_caching(aggregator, integration_check, dbm_instance):
    dbm_instance["username"] = "datadog"
    dbm_instance["dbname"] = "postgres"
    check = integration_check(dbm_instance)
    assert not check.pg_settings, "pg_settings should not have been initialized yet"
    check._connect()
    check._get_db(dbm_instance["dbname"])
    assert "track_activity_query_size" in check.pg_settings
    check.pg_settings["test_key"] = True
    check._get_db(dbm_instance["dbname"])
    assert (
        "test_key" in check.pg_settings
    ), "key should not have been blown away. If it was then pg_settings was not cached correctly"


def test_statement_samples_main_collection_rate_limit(aggregator, integration_check, dbm_instance):
    # test the main collection loop rate limit
    collection_interval = 0.1
    dbm_instance['query_samples']['collection_interval'] = collection_interval
    dbm_instance['query_samples']['run_sync'] = False
    check = integration_check(dbm_instance)
    check._connect()
    check.check(dbm_instance)
    sleep_time = 1
    time.sleep(sleep_time)
    max_collections = int(1 / collection_interval * sleep_time) + 1
    check.cancel()
    metrics = aggregator.metrics("dd.postgres.collect_statement_samples.time")
    assert max_collections / 2.0 <= len(metrics) <= max_collections


@pytest.mark.skip(reason='debugging flaky test (2021-09-03)')
def test_statement_samples_unique_plans_rate_limits(aggregator, integration_check, dbm_instance, bob_conn):
    # tests rate limiting ingestion of samples per unique (query, plan)
    cache_max_size = 10
    dbm_instance['query_samples']['seen_samples_cache_maxsize'] = cache_max_size
    # samples_per_hour_per_query set very low so that within this test we will have at most one sample per
    # (query, plan)
    dbm_instance['query_samples']['samples_per_hour_per_query'] = 1
    # run it synchronously with a high rate limit specifically for the test
    dbm_instance['query_samples']['collection_interval'] = 1.0 / 100
    dbm_instance['query_samples']['run_sync'] = True
    dbm_instance['query_metrics']['enabled'] = False
    check = integration_check(dbm_instance)
    check._connect()

    query_template = "SELECT {} FROM persons WHERE city = 'hello'"
    # queries that have different numbers of columns are considered different queries
    # i.e. "SELECT city, city FROM persons where city= 'hello'"
    queries = [query_template.format(','.join(["city"] * i)) for i in range(1, 15)]

    # leave bob's connection open until after the check has run to ensure we're able to see the query in
    # pg_stat_activity
    cursor = bob_conn.cursor()
    for _ in range(3):
        # repeat the same set of queries multiple times to ensure we're testing the per-query TTL rate limit
        for q in queries:
            cursor.execute(q)
            check.check(dbm_instance)
    cursor.close()

    def _sample_key(e):
        return e['db']['query_signature'], e['db'].get('plan', {}).get('signature')

    dbm_samples = [e for e in aggregator.get_event_platform_events("dbm-samples") if e.get('dbm_type') != 'fqt']
    statement_counts = Counter(_sample_key(e) for e in dbm_samples)
    assert len(statement_counts) == cache_max_size, "expected to collect at most {} unique statements".format(
        cache_max_size
    )

    for _, count in statement_counts.items():
        assert count == 1, "expected to collect exactly one sample per statement during this time"

    # in addition to the test query, dbm_samples will also contain samples from other queries that the postgres
    # integration is running
    pattern = query_template.format("(city,?)+")
    matching = [e for e in dbm_samples if re.match(pattern, e['db']['statement'])]

    assert len(matching) > 0, "should have collected exactly at least one matching event"


def test_async_job_inactive_stop(aggregator, integration_check, dbm_instance):
    dbm_instance['query_samples']['run_sync'] = False
    dbm_instance['query_metrics']['run_sync'] = False
    check = integration_check(dbm_instance)
    check._connect()
    check.check(dbm_instance)
    # make sure there were no unhandled exceptions
    check.statement_samples._job_loop_future.result()
    check.statement_metrics._job_loop_future.result()
    for job in ['query-metrics', 'query-samples']:
        aggregator.assert_metric(
            "dd.postgres.async_job.inactive_stop",
            tags=_expected_dbm_instance_tags(dbm_instance) + ['job:' + job],
        )


def test_async_job_cancel_cancel(aggregator, integration_check, dbm_instance):
    dbm_instance['query_samples']['run_sync'] = False
    dbm_instance['query_metrics']['run_sync'] = False
    check = integration_check(dbm_instance)
    check._connect()
    check.check(dbm_instance)
    check.cancel()
    # wait for it to stop and make sure it doesn't throw any exceptions
    check.statement_samples._job_loop_future.result()
    check.statement_metrics._job_loop_future.result()
    assert not check.statement_samples._job_loop_future.running(), "samples thread should be stopped"
    assert not check.statement_metrics._job_loop_future.running(), "metrics thread should be stopped"
    # if the thread doesn't start until after the cancel signal is set then the db connection will never
    # be created in the first place
    assert check._db_pool.get(dbm_instance['dbname']) is None, "db connection should be gone"
    for job in ['query-metrics', 'query-samples']:
        aggregator.assert_metric(
            "dd.postgres.async_job.cancel",
            tags=_expected_dbm_instance_tags(dbm_instance) + ['job:' + job],
        )


def test_statement_samples_invalid_activity_view(aggregator, integration_check, dbm_instance):
    dbm_instance['pg_stat_activity_view'] = "wrong_view"

    # run synchronously, so we expect it to blow up right away
    dbm_instance['query_samples'] = {'enabled': True, 'run_sync': True}
    check = integration_check(dbm_instance)
    check._connect()
    with pytest.raises(psycopg2.errors.UndefinedTable):
        check.check(dbm_instance)

    # run asynchronously, loop will crash the first time it tries to run as the table doesn't exist
    dbm_instance['query_samples']['run_sync'] = False
    check = integration_check(dbm_instance)
    check._connect()
    check.check(dbm_instance)
    # make sure there were no unhandled exceptions
    check.statement_samples._job_loop_future.result()
    aggregator.assert_metric(
        "dd.postgres.async_job.error",
        tags=_expected_dbm_instance_tags(dbm_instance)
        + [
            'job:query-samples',
            "error:database-<class 'psycopg2.errors.UndefinedTable'>",
        ],
    )


@pytest.mark.parametrize(
    "number_key",
    [
        "explained_queries_cache_maxsize",
        "explained_queries_per_hour_per_query",
        "seen_samples_cache_maxsize",
        "collection_interval",
    ],
)
def test_statement_samples_config_invalid_number(integration_check, pg_instance, number_key):
    pg_instance['query_samples'] = {
        number_key: "not-a-number",
    }
    with pytest.raises(ValueError):
        integration_check(pg_instance)


class ObjectNotInPrerequisiteState(psycopg2.errors.ObjectNotInPrerequisiteState):
    """
    A fake ObjectNotInPrerequisiteState that allows setting pg_error on construction since ObjectNotInPrerequisiteState
    has it as read-only and not settable at construction-time
    """

    def __init__(self, pg_error):
        self.pg_error = pg_error

    def __getattribute__(self, attr):
        if attr == 'pgerror':
            return self.pg_error
        else:
            return super(ObjectNotInPrerequisiteState, self).__getattribute__(attr)


class UndefinedTable(psycopg2.errors.UndefinedTable):
    """
    A fake UndefinedTable that allows setting pg_error on construction since UndefinedTable
    has it as read-only and not settable at construction-time
    """

    def __init__(self, pg_error):
        self.pg_error = pg_error

    def __getattribute__(self, attr):
        if attr == 'pgerror':
            return self.pg_error
        else:
            return super(UndefinedTable, self).__getattribute__(attr)


@pytest.mark.parametrize(
    "error,metric_columns,expected_error_tag",
    [
        (
            ObjectNotInPrerequisiteState('pg_stat_statements must be loaded via shared_preload_libraries'),
            [],
            'error:database-ObjectNotInPrerequisiteState-pg_stat_statements_not_loaded',
        ),
        (
            UndefinedTable('ERROR:  relation "pg_stat_statements" does not exist'),
            [],
            'error:database-UndefinedTable-pg_stat_statements_not_created',
        ),
        (
            ObjectNotInPrerequisiteState('cannot insert into view'),
            [],
            'error:database-ObjectNotInPrerequisiteState',
        ),
        (
            psycopg2.errors.DatabaseError(),
            [],
            'error:database-DatabaseError',
        ),
        (
            None,
            [],
            'error:database-missing_pg_stat_statements_required_columns',
        ),
    ],
)
def test_statement_metrics_database_errors(
    aggregator, integration_check, dbm_instance, error, metric_columns, expected_error_tag
):
    # don't need samples for this test
    dbm_instance['query_samples'] = {'enabled': False}
    check = integration_check(dbm_instance)
    check._connect()

    with mock.patch(
        'datadog_checks.postgres.statements.PostgresStatementMetrics._get_pg_stat_statements_columns',
        return_value=metric_columns,
        side_effect=error,
    ):
        check.check(dbm_instance)

    expected_tags = dbm_instance['tags'] + [
        'db:{}'.format(DB_NAME),
        'port:{}'.format(PORT),
        'agent_hostname:stubbed.hostname',
        expected_error_tag,
    ]

    aggregator.assert_metric(
        'dd.postgres.statement_metrics.error', value=1.0, count=1, tags=expected_tags, hostname='stubbed.hostname'
    )
