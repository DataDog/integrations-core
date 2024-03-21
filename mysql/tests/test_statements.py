# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import re
import time
from collections import Counter
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import closing
from os import environ

import mock
import pytest
from packaging.version import parse as parse_version

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.serialization import json
from datadog_checks.mysql import MySql, statements
from datadog_checks.mysql.statement_samples import StatementTruncationState

from . import common
from .common import MYSQL_VERSION_PARSED

logger = logging.getLogger(__name__)

statement_samples_keys = ["query_samples", "statement_samples"]

# default test query to use that is guaranteed to succeed as it's using a fully qualified table name so it doesn't
# depend on a default schema being set on the connection
DEFAULT_FQ_SUCCESS_QUERY = "SELECT * FROM information_schema.TABLES"


@pytest.fixture
def dbm_instance(instance_complex):
    instance_complex['dbm'] = True
    instance_complex['disable_generic_tags'] = False
    # set the default for tests to run sychronously to ensure we don't have orphaned threads running around
    instance_complex['query_samples'] = {'enabled': True, 'run_sync': True, 'collection_interval': 1}
    # set a very small collection interval so the tests go fast
    instance_complex['query_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    # don't need query activity for these tests
    instance_complex['query_activity'] = {'enabled': False}
    instance_complex['collect_settings'] = {'enabled': False}
    return instance_complex


dbm_enabled_keys = ["dbm", "deep_database_monitoring"]


@pytest.mark.parametrize("dbm_enabled_key", dbm_enabled_keys)
@pytest.mark.parametrize("dbm_enabled", [True, False])
def test_dbm_enabled_config(dbm_instance, dbm_enabled_key, dbm_enabled):
    # test to make sure we continue to support the old key
    for k in dbm_enabled_keys:
        dbm_instance.pop(k, None)
    dbm_instance[dbm_enabled_key] = dbm_enabled
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    assert mysql_check._config.dbm_enabled == dbm_enabled


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.mark.unit
@pytest.mark.parametrize("statement_samples_key", statement_samples_keys)
@pytest.mark.parametrize("statement_samples_enabled", [True, False])
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_statement_samples_enabled_config(dbm_instance, statement_samples_key, statement_samples_enabled):
    # test to make sure we continue to support the old key
    for k in statement_samples_keys:
        dbm_instance.pop(k, None)
    dbm_instance[statement_samples_key] = {'enabled': statement_samples_enabled}
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    assert mysql_check._statement_samples._enabled == statement_samples_enabled


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
# these queries are formatted the same way they appear in events_statements_summary_by_digest to make the test simpler
@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM `testdb` . `users`",
        # include one long query that exceeds truncation limit so we can confirm the truncation is happening
        "SELECT `hello_how_is_it_going_this_is_a_very_long_table_alias_name` . `name` , "
        "`hello_how_is_it_going_this_is_a_very_long_table_alias_name` . `age` FROM `testdb` . `users` "
        "`hello_how_is_it_going_this_is_a_very_long_table_alias_name` JOIN `testdb` . `users` `B` ON "
        "`hello_how_is_it_going_this_is_a_very_long_table_alias_name` . `name` = `B` . `name`",
    ],
)
@pytest.mark.parametrize("default_schema", [None, "testdb"])
@pytest.mark.parametrize("aurora_replication_role", [None, "writer", "reader"])
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_statement_metrics(
    aggregator, dd_run_check, dbm_instance, query, default_schema, datadog_agent, aurora_replication_role
):
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    def run_query(q):
        with mysql_check._connect() as db:
            with closing(db.cursor()) as cursor:
                if default_schema:
                    cursor.execute("USE " + default_schema)
                cursor.execute(q)

    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as m_obfuscate_sql, mock.patch.object(
        mysql_check, '_get_is_aurora', passthrough=True
    ) as m_get_is_aurora, mock.patch.object(
        mysql_check, '_get_runtime_aurora_tags', passthrough=True
    ) as m_get_runtime_aurora_tags:
        m_obfuscate_sql.side_effect = _obfuscate_sql
        m_get_is_aurora.return_value = False
        m_get_runtime_aurora_tags.return_value = []
        if aurora_replication_role:
            m_get_is_aurora.return_value = True
            m_get_runtime_aurora_tags.return_value = ["replication_role:" + aurora_replication_role]

        # Run a query
        run_query(query)
        dd_run_check(mysql_check)

        # Run the query and check a second time so statement metrics are computed from the previous run
        run_query(query)
        dd_run_check(mysql_check)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 1
    event = events[0]

    assert event['host'] == 'stubbed.hostname'
    assert event['ddagentversion'] == datadog_agent.get_version()
    assert event['ddagenthostname'] == datadog_agent.get_hostname()
    assert event['mysql_version'] == mysql_check.version.version + '+' + mysql_check.version.build
    assert event['mysql_flavor'] == mysql_check.version.flavor
    assert event['timestamp'] > 0
    assert event['min_collection_interval'] == dbm_instance['query_metrics']['collection_interval']
    expected_tags = set(_expected_dbm_instance_tags(dbm_instance))
    if aurora_replication_role:
        expected_tags.add("replication_role:" + aurora_replication_role)
    assert set(event['tags']) == expected_tags
    query_signature = compute_sql_signature(query)
    matching_rows = [r for r in event['mysql_rows'] if r['query_signature'] == query_signature]
    assert len(matching_rows) == 1
    row = matching_rows[0]

    assert row['digest']
    assert row['schema_name'] == default_schema
    assert row['digest_text'].strip() == query.strip()

    for col in statements.METRICS_COLUMNS:
        assert type(row[col]) in (float, int)

    events = aggregator.get_event_platform_events("dbm-samples")
    assert len(events) > 0
    fqt_events = [e for e in events if e.get('dbm_type') == 'fqt']
    assert len(fqt_events) > 0
    matching = [e for e in fqt_events if e['db']['query_signature'] == query_signature]
    assert len(matching) == 1
    event = matching[0]
    assert event['db']['query_signature'] == query_signature
    assert event['db']['statement'] == query
    assert event['mysql']['schema'] == default_schema
    assert event['timestamp'] > 0
    assert event['host'] == 'stubbed.hostname'
    assert event['ddagentversion'] == datadog_agent.get_version()


def _obfuscate_sql(query, options=None):
    return re.sub(r'\s+', ' ', query or '').strip()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_statement_metrics_with_duplicates(aggregator, dd_run_check, dbm_instance, datadog_agent):
    query_one = 'select * from information_schema.processlist where state in (\'starting\')'
    query_two = 'select * from information_schema.processlist where state in (\'starting\', \'Waiting on empty queue\')'
    normalized_query = 'SELECT * FROM `information_schema` . `processlist` where state in ( ? )'
    # The query signature should match the query and consistency of this tag has product impact. Do not change
    # the query signature for this test unless you know what you're doing. The query digest is determined by
    # mysql and varies across versions.
    query_signature = '94caeb4c54f97849'

    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    def obfuscate_sql(query, options=None):
        if 'WHERE `state`' in query:
            return normalized_query
        return query

    def run_query(q):
        with mysql_check._connect() as db:
            with closing(db.cursor()) as cursor:
                cursor.execute(q)

    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = obfuscate_sql
        # Run two queries that map to the same normalized one
        run_query(query_one)
        run_query(query_two)
        dd_run_check(mysql_check)

        # Run the queries again and check a second time so statement metrics are computed from the previous run using
        # the merged stats of the two queries
        run_query(query_one)
        run_query(query_two)
        dd_run_check(mysql_check)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 1
    event = events[0]

    matching_rows = [r for r in event['mysql_rows'] if r['query_signature'] == query_signature]
    assert len(matching_rows) == 1
    row = matching_rows[0]

    assert row['query_signature'] == query_signature
    assert row['count_star'] == 2


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "input_cloud_metadata,output_cloud_metadata",
    [
        ({}, {}),
        (
            {
                'azure': {
                    'deployment_type': 'flexible_server',
                    'name': 'test-server.database.windows.net',
                },
            },
            {
                'azure': {
                    'deployment_type': 'flexible_server',
                    'name': 'test-server.database.windows.net',
                },
            },
        ),
        (
            {
                'azure': {
                    'deployment_type': 'flexible_server',
                    'fully_qualified_domain_name': 'test-server.database.windows.net',
                },
            },
            {
                'azure': {
                    'deployment_type': 'flexible_server',
                    'name': 'test-server.database.windows.net',
                },
            },
        ),
        (
            {
                'aws': {
                    'instance_endpoint': 'foo.aws.com',
                },
                'azure': {
                    'deployment_type': 'flexible_server',
                    'name': 'test-server.database.windows.net',
                },
            },
            {
                'aws': {
                    'instance_endpoint': 'foo.aws.com',
                },
                'azure': {
                    'deployment_type': 'flexible_server',
                    'name': 'test-server.database.windows.net',
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
def test_statement_metrics_cloud_metadata(
    aggregator, dd_run_check, dbm_instance, input_cloud_metadata, output_cloud_metadata, datadog_agent
):
    if input_cloud_metadata:
        for k, v in input_cloud_metadata.items():
            dbm_instance[k] = v
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    def run_query(q):
        with mysql_check._connect() as db:
            with closing(db.cursor()) as cursor:
                cursor.execute(q)

    query = "SELECT * FROM `testdb` . `users`"

    # Run a query
    run_query(query)
    dd_run_check(mysql_check)

    # Run the query and check a second time so statement metrics are computed from the previous run
    run_query(query)
    dd_run_check(mysql_check)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 1, "should produce exactly one metrics payload"
    event = events[0]

    assert event['host'] == 'stubbed.hostname'
    assert event['ddagentversion'] == datadog_agent.get_version()
    assert event['ddagenthostname'] == datadog_agent.get_hostname()
    assert event['mysql_version'] == mysql_check.version.version + '+' + mysql_check.version.build
    assert event['mysql_flavor'] == mysql_check.version.flavor
    assert event['cloud_metadata'] == output_cloud_metadata, "wrong cloud_metadata"


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize("explain_strategy", ['PROCEDURE', 'FQ_PROCEDURE', 'STATEMENT', None])
@pytest.mark.parametrize(
    "schema,statement,expected_collection_errors,expected_statement_truncated",
    [
        (
            None,
            'select name as nam from testdb.users',
            None,
            StatementTruncationState.not_truncated.value,
        ),
        (
            'information_schema',
            'select * from testdb.users',
            [{'strategy': 'PROCEDURE', 'code': 'database_error', 'message': "<class 'pymysql.err.OperationalError'>"}],
            StatementTruncationState.not_truncated.value,
        ),
        (
            'testdb',
            'select name as nam from users',
            [
                {
                    'strategy': 'FQ_PROCEDURE',
                    'code': 'database_error',
                    'message': "<class 'pymysql.err.ProgrammingError'>",
                }
            ],
            StatementTruncationState.not_truncated.value,
        ),
        (
            'testdb',
            'SELECT {} FROM users where '
            'name=\'Johannes Chrysostomus Wolfgangus Theophilus Mozart\''.format(
                ", ".join("name as name{}".format(i) for i in range(244))
            ),
            [
                {
                    'strategy': None,
                    'code': 'query_truncated',
                    'message': 'truncated length: {}'.format(
                        4096
                        if MYSQL_VERSION_PARSED > parse_version('5.6') and environ.get('MYSQL_FLAVOR') != 'mariadb'
                        else 1024
                    ),
                }
            ],
            StatementTruncationState.truncated.value,
        ),
    ],
)
@pytest.mark.parametrize("aurora_replication_role", ["reader"])
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_statement_samples_collect(
    aggregator,
    dd_run_check,
    dbm_instance,
    bob_conn,
    explain_strategy,
    schema,
    statement,
    expected_collection_errors,
    expected_statement_truncated,
    aurora_replication_role,
    caplog,
    datadog_agent,
):
    caplog.set_level(logging.INFO, logger="datadog_checks.mysql.collection_utils")
    caplog.set_level(logging.DEBUG, logger="datadog_checks")
    caplog.set_level(logging.DEBUG, logger="tests.test_mysql")

    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    if explain_strategy:
        mysql_check._statement_samples._preferred_explain_strategies = [explain_strategy]

    expected_tags = set(_expected_dbm_instance_tags(dbm_instance))
    if aurora_replication_role:
        expected_tags.add("replication_role:" + aurora_replication_role)

    with mock.patch.object(mysql_check, '_get_is_aurora', passthrough=True) as m_get_is_aurora, mock.patch.object(
        mysql_check, '_get_runtime_aurora_tags', passthrough=True
    ) as m_get_runtime_aurora_tags:
        m_get_is_aurora.return_value = False
        m_get_runtime_aurora_tags.return_value = []
        if aurora_replication_role:
            m_get_is_aurora.return_value = True
            m_get_runtime_aurora_tags.return_value = ["replication_role:" + aurora_replication_role]

        logger.debug("running first check")
        dd_run_check(mysql_check)
        aggregator.reset()
        mysql_check._statement_samples._init_caches()

        # we deliberately want to keep the connection open for the duration of the test to ensure
        # the query remains in the events_statements_current and events_statements_history tables
        # it would be cleared out upon connection close otherwise
        with closing(bob_conn.cursor()) as cursor:
            # run the check once, then clear out all saved events
            # on the next check run it should only capture events since the last checkpoint
            if schema:
                cursor.execute("use {}".format(schema))
            cursor.execute(statement)
        logger.debug("running second check")
        mysql_check.check(dbm_instance)
        logger.debug("done second check")

    events = aggregator.get_event_platform_events("dbm-samples")

    for event in events:
        assert event['ddagentversion'] == datadog_agent.get_version()

    # Match against the statement itself if it's below the statement length limit or its truncated form which is
    # the first 1024/4096 bytes (depending on the mysql version) with the last 3 replaced by '...'
    expected_statement_prefix = (
        statement[:1021] + '...'
        if len(statement) > 1024
        and (MYSQL_VERSION_PARSED == parse_version('5.6') or environ.get('MYSQL_FLAVOR') == 'mariadb')
        else statement[:4093] + '...' if len(statement) > 4096 else statement
    )

    matching = [e for e in events if expected_statement_prefix.startswith(e['db']['statement'])]
    assert len(matching) > 0, "should have collected an event"

    with_plans = [e for e in matching if e['db']['plan']['definition'] is not None]
    if schema == 'testdb' and explain_strategy == 'FQ_PROCEDURE':
        # explain via the FQ_PROCEDURE will fail if a query contains non-fully-qualified tables because it will
        # default to the schema of the FQ_PROCEDURE, so in case of "select * from testdb" it'll try to do
        # "select start from datadog.testdb" which would be the wrong schema.
        assert not with_plans, "should not have collected any plans"
    elif schema == 'information_schema' and explain_strategy == 'PROCEDURE':
        # we can't create an explain_statement procedure in performance_schema so this is not expected to work
        assert not with_plans, "should not have collected any plans"
    elif not schema and explain_strategy == 'PROCEDURE':
        # if there is no default schema then we cannot use the non-fully-qualified procedure strategy
        assert not with_plans, "should not have collected any plans"
    elif not expected_statement_truncated:
        event = with_plans[0]
        assert 'query_block' in json.loads(event['db']['plan']['definition']), "invalid json execution plan"
        assert set(event['ddtags'].split(',')) == expected_tags

    # Validate the events to ensure we've provided an explanation for not providing an exec plan
    for event in matching:
        assert event['db']['query_truncated'] == expected_statement_truncated
        if event['db']['plan']['definition'] is None:
            assert event['db']['plan']['collection_errors'] == expected_collection_errors
        else:
            assert event['db']['plan']['collection_errors'] is None
        assert event['timestamp'] is not None
        assert time.time() - event['timestamp'] < 60  # ensure the timestamp is recent

    # we avoid closing these in a try/finally block in order to maintain the connections in case we want to
    # debug the test with --pdb
    mysql_check._statement_samples._close_db_conn()


@pytest.mark.parametrize(
    "statement,schema,expected_warnings",
    [
        (
            'SELECT 1',
            # Since information_schema doesn't have the explain_plan procedure, we should detect the config
            # error and emit a warning
            'information_schema',
            [
                "Unable to collect explain plans because the procedure 'explain_statement' is "
                "either undefined or not granted access to in schema 'information_schema'. "
                "See https://docs.datadoghq.com/database_monitoring/setup_mysql/troubleshooting#"
                "explain-plan-procedure-missing for more details: "
                "(1044) Access denied for user 'dog'@'%' to database 'information_schema'\n"
                "code=explain-plan-procedure-missing host=stubbed.hostname schema=information_schema",
            ],
        ),
        (
            # The missing table should make the explain plan fail without reporting a warning about the procedure
            # missing
            'SELECT * from missing_table',
            'testdb',
            [],
        ),
    ],
)
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_missing_explain_procedure(dbm_instance, dd_run_check, aggregator, statement, schema, expected_warnings):
    # This feature is being deprecated, it's disabled here because otherwise this warning gets surfaced before the
    # explain procedure warning.
    dbm_instance['options']['extra_performance_metrics'] = False
    # Disable query samples to avoid interference from query samples getting picked up from db and triggering
    # explain plans
    dbm_instance['query_samples']['enabled'] = False
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    mysql_check._statement_samples._preferred_explain_strategies = ['PROCEDURE']
    mysql_check._statement_samples._tags = []
    mysql_check._statement_samples._tags_str = ''

    row = {
        'current_schema': schema,
        'sql_text': statement,
        'query': statement,
        'digest_text': statement,
        'now': time.time(),
        'uptime': '21466230',
        'timer_end': 3019558487284095384,
        'timer_wait_ns': 12.9,
    }

    mysql_check._statement_samples._collect_plan_for_statement(row)
    dd_run_check(mysql_check)

    assert mysql_check.warnings == expected_warnings


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_performance_schema_disabled(dbm_instance, dd_run_check):
    # Disable query samples to avoid interference from queries from the db running explain plans
    # and isolate the fake row from it
    dbm_instance['options']['extra_performance_metrics'] = False
    dbm_instance['query_samples']['enabled'] = False
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    # Fake the performance schema being disabled to validate the reporting of a warning when this condition occurs
    mysql_check.performance_schema_enabled = False

    # Run this twice to confirm that duplicate warnings aren't added more than once
    mysql_check._statement_metrics.collect_per_statement_metrics()
    mysql_check._statement_metrics.collect_per_statement_metrics()

    # Run the check only so that recorded warnings are actually added
    dd_run_check(mysql_check)

    assert mysql_check.warnings == [
        'Unable to collect statement metrics because the performance schema is disabled. See '
        'https://docs.datadoghq.com/database_monitoring/setup_mysql/troubleshooting#performance-schema-not-enabled '
        'for more details\n'
        'code=performance-schema-not-enabled host=stubbed.hostname'
    ]

    # as we faked the performance schema being disabled, running the check should restore the flag to True
    # this is to "simulate" enabling performance schema without restarting the agent
    # as the next check run will update the flag
    assert mysql_check.performance_schema_enabled is True

    # clear the warnings and rerun collect_per_statement_metrics
    mysql_check.warnings.clear()
    mysql_check._statement_metrics.collect_per_statement_metrics()
    mysql_check._statement_metrics.collect_per_statement_metrics()
    dd_run_check(mysql_check)
    assert mysql_check.warnings == []


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "metadata,expected_metadata_payload",
    [
        (
            {'tables_csv': 'information_schema', 'commands': ['SELECT'], 'comments': ['-- Test comment']},
            {'tables': ['information_schema'], 'commands': ['SELECT'], 'comments': ['-- Test comment']},
        ),
        (
            {'tables_csv': '', 'commands': None, 'comments': None},
            {'tables': None, 'commands': None, 'comments': None},
        ),
    ],
)
def test_statement_metadata(
    aggregator, dd_run_check, dbm_instance, datadog_agent, metadata, expected_metadata_payload, root_conn
):
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    test_query = '''
    -- Test comment
    select * from information_schema.processlist where state in (\'starting\')
    '''
    query_signature = '94caeb4c54f97849'
    normalized_query = 'SELECT * FROM `information_schema` . `processlist` where state in ( ? )'

    def obfuscate_sql(query, options=None):
        if 'WHERE `state`' in query:
            return json.dumps({'query': normalized_query, 'metadata': metadata})
        return json.dumps({'query': query, 'metadata': metadata})

    def run_query(q):
        with closing(root_conn.cursor()) as cursor:
            cursor.execute(q)

    # Execute the query with the mocked obfuscate_sql. The result should produce an event payload with the metadata.
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = obfuscate_sql
        run_query(test_query)
        dd_run_check(mysql_check)
        run_query(test_query)
        dd_run_check(mysql_check)

    samples = aggregator.get_event_platform_events("dbm-samples")
    matching = [s for s in samples if s['db']['query_signature'] == query_signature and s.get('dbm_type') != 'fqt']
    assert len(matching) == 1
    sample = matching[0]
    assert sample['db']['metadata']['tables'] == expected_metadata_payload['tables']
    assert sample['db']['metadata']['commands'] == expected_metadata_payload['commands']
    assert sample['db']['metadata']['comments'] == expected_metadata_payload['comments']

    fqt_samples = [s for s in samples if s['db']['query_signature'] == query_signature and s.get('dbm_type') == 'fqt']
    assert len(fqt_samples) == 1
    fqt = fqt_samples[0]
    assert fqt['db']['metadata']['tables'] == expected_metadata_payload['tables']
    assert fqt['db']['metadata']['commands'] == expected_metadata_payload['commands']

    metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert len(metrics) == 1
    metric = metrics[0]
    matching_metrics = [m for m in metric['mysql_rows'] if m['query_signature'] == query_signature]
    assert len(matching_metrics) == 1
    metric = matching_metrics[0]
    assert metric['dd_tables'] == expected_metadata_payload['tables']
    assert metric['dd_commands'] == expected_metadata_payload['commands']


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
    aggregator, dd_run_check, dbm_instance, datadog_agent, reported_hostname, expected_hostname
):
    dbm_instance['reported_hostname'] = reported_hostname
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    dd_run_check(mysql_check)
    dd_run_check(mysql_check)

    samples = aggregator.get_event_platform_events("dbm-samples")
    assert samples, "should have at least one sample"
    assert samples[0]['host'] == expected_hostname

    fqt_samples = [s for s in samples if s.get('dbm_type') == 'fqt']
    assert fqt_samples, "should have at least one fqt sample"
    assert fqt_samples[0]['host'] == expected_hostname

    metrics = aggregator.get_event_platform_events("dbm-metrics")
    assert metrics, "should have at least one metric"
    assert metrics[0]['host'] == expected_hostname


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "current_schema,sql_text,optimal_strategy_cached,attempt_count,total_error_count,db_error_count",
    [
        # if there is no default schema then we have only two possible strategies as the PROCEDURE strategy requires
        # a default schema, so (3*2=6)
        (None, 'select * from fake_table', True, 3, 6, 2),
        (None, 'select * from fake_table', False, 3, 6, 6),
        # if there is a default schema then we'll try all three possible strategies (3*3 = 9)
        ('testdb', 'select * from fake_table', True, 3, 9, 3),
        ('testdb', 'select * from fake_table', False, 3, 9, 9),
        # if there is an issue accessing the schema then we won't event attempt to explain the query and schema error
        # will be cached so we won't try to re-access the schema, therefore there will be only one database error.
        ('invalid_schema', 'select * from fake_table', False, 3, 3, 1),
    ],
)
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_statement_samples_failed_explain_handling(
    aggregator,
    dd_run_check,
    dbm_instance,
    current_schema,
    sql_text,
    optimal_strategy_cached,
    attempt_count,
    total_error_count,
    db_error_count,
):
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    dd_run_check(mysql_check)

    total_error_states = []
    with closing(mysql_check._statement_samples._get_db_connection().cursor()) as cursor:
        if optimal_strategy_cached:
            # run a query in that schema which we know will succeed to ensure the optimal strategy is cached
            _, error_states = mysql_check._statement_samples._explain_statement(
                cursor, DEFAULT_FQ_SUCCESS_QUERY, current_schema, DEFAULT_FQ_SUCCESS_QUERY, DEFAULT_FQ_SUCCESS_QUERY
            )
            assert not error_states
        else:
            # reset all internal caches to make sure there is no previously cached strategy
            mysql_check._statement_samples._init_caches()

        aggregator.reset()

        for _ in range(attempt_count):
            _, error_states = mysql_check._statement_samples._explain_statement(
                cursor, sql_text, current_schema, sql_text, sql_text
            )
            total_error_states.extend(error_states)

    assert len(total_error_states) == total_error_count
    aggregator.assert_metric("dd.mysql.db.error", value=db_error_count)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_statement_samples_main_collection_rate_limit(aggregator, dd_run_check, dbm_instance):
    # test rate limiting of the main collection loop
    collection_interval = 0.2
    dbm_instance['query_samples']['collection_interval'] = collection_interval
    dbm_instance['query_samples']['run_sync'] = False
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    dd_run_check(mysql_check)
    sleep_time = 1
    time.sleep(sleep_time)
    max_collections = int(1 / collection_interval * sleep_time) + 1
    mysql_check.cancel()
    metrics = aggregator.metrics("dd.mysql.collect_statement_samples.time")
    assert max_collections / 2.0 <= len(metrics) <= max_collections


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_statement_samples_unique_plans_rate_limits(aggregator, dd_run_check, bob_conn, dbm_instance):
    # test unique sample ingestion rate limiting
    cache_max_size = 20
    dbm_instance['query_samples']['run_sync'] = True
    dbm_instance['query_samples']['seen_samples_cache_maxsize'] = cache_max_size
    # samples_per_hour_per_query set very low so that within this test we will have at most one sample per
    # (query, plan)
    dbm_instance['query_samples']['samples_per_hour_per_query'] = 1
    dbm_instance['query_samples']['collection_interval'] = 1.0 / 100
    query_template = "select {} from testdb.users where name = 'hello'"
    # queries that have different numbers of columns are considered different queries
    # i.e. "SELECT city, city FROM persons where city= 'hello'"
    queries = [query_template.format(','.join(["name"] * i)) for i in range(1, 20)]
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    with closing(bob_conn.cursor()) as cursor:
        for _ in range(3):
            # repeat the same set of queries multiple times to ensure we're testing the per-query TTL rate limit
            for q in queries:
                cursor.execute(q)
                dd_run_check(mysql_check)

    def _sample_key(e):
        return e['db']['query_signature'], e['db'].get('plan', {}).get('signature')

    dbm_samples = [e for e in aggregator.get_event_platform_events("dbm-samples") if e.get('dbm_type') != 'fqt']
    statement_counts = Counter(_sample_key(e) for e in dbm_samples)
    assert len(statement_counts) == cache_max_size, "expected to collect at {} unique statements".format(cache_max_size)

    for _, count in statement_counts.items():
        assert count == 1, "expected to collect exactly one sample per (query, plan)"

    # in addition to the test query, dbm_samples will also contain samples from other queries that the postgres
    # integration is running
    pattern = query_template.format("(name,?)+")
    matching = [e for e in dbm_samples if re.match(pattern, e['db']['statement'])]
    assert len(matching) > 0, "should have collected at least one matching event"


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_async_job_inactive_stop(aggregator, dd_run_check, dbm_instance):
    # confirm that async jobs stop on their own after the check has not been run for a while
    dbm_instance['query_samples']['run_sync'] = False
    dbm_instance['query_metrics']['run_sync'] = False
    # low collection interval for a faster test
    dbm_instance['min_collection_interval'] = 1
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    dd_run_check(mysql_check)
    # make sure there were no unhandled exceptions
    mysql_check._statement_samples._job_loop_future.result()
    mysql_check._statement_metrics._job_loop_future.result()
    for job in ['statement-metrics', 'statement-samples']:
        aggregator.assert_metric(
            "dd.mysql.async_job.inactive_stop", tags=_expected_dbm_job_err_tags(dbm_instance) + ['job:' + job]
        )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_async_job_cancel(aggregator, dd_run_check, dbm_instance):
    dbm_instance['query_samples']['run_sync'] = False
    dbm_instance['query_metrics']['run_sync'] = False
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    dd_run_check(mysql_check)
    mysql_check.cancel()
    # wait for it to stop and make sure it doesn't throw any exceptions
    mysql_check._statement_samples._job_loop_future.result()
    mysql_check._statement_metrics._job_loop_future.result()
    assert not mysql_check._statement_samples._job_loop_future.running(), "samples thread should be stopped"
    assert not mysql_check._statement_metrics._job_loop_future.running(), "metrics thread should be stopped"
    assert mysql_check._statement_samples._db is None, "samples db connection should be gone"
    assert mysql_check._statement_metrics._db is None, "metrics db connection should be gone"
    for job in ['statement-metrics', 'statement-samples']:
        aggregator.assert_metric(
            "dd.mysql.async_job.cancel", tags=_expected_dbm_job_err_tags(dbm_instance) + ['job:' + job]
        )


def _expected_dbm_instance_tags(dbm_instance):
    return dbm_instance.get('tags', []) + ['server:{}'.format(common.HOST), 'port:{}'.format(common.PORT)]


# the inactive job metrics are emitted from the main integrations
# directly to metrics-intake, so they should also be properly tagged with a resource
def _expected_dbm_job_err_tags(dbm_instance):
    return dbm_instance['tags'] + [
        'port:{}'.format(common.PORT),
        'server:{}'.format(common.HOST),
        'dd.internal.resource:database_instance:stubbed.hostname',
    ]


@pytest.mark.parametrize("statement_samples_enabled", [True, False])
@pytest.mark.parametrize("statement_metrics_enabled", [True, False])
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_async_job_enabled(dd_run_check, dbm_instance, statement_samples_enabled, statement_metrics_enabled):
    dbm_instance['query_samples'] = {'enabled': statement_samples_enabled, 'run_sync': False}
    dbm_instance['query_metrics'] = {'enabled': statement_metrics_enabled, 'run_sync': False}
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    dd_run_check(mysql_check)
    mysql_check.cancel()
    if statement_samples_enabled:
        assert mysql_check._statement_samples._job_loop_future is not None
        mysql_check._statement_samples._job_loop_future.result()
    else:
        assert mysql_check._statement_samples._job_loop_future is None
    if statement_metrics_enabled:
        assert mysql_check._statement_metrics._job_loop_future is not None
        mysql_check._statement_metrics._job_loop_future.result()
    else:
        assert mysql_check._statement_metrics._job_loop_future is None


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_statement_samples_invalid_explain_procedure(aggregator, dd_run_check, dbm_instance, bob_conn):
    dbm_instance['query_samples']['explain_procedure'] = 'hello'
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    dd_run_check(mysql_check)
    aggregator.assert_metric_has_tag_prefix("dd.mysql.query_samples.error", "error:explain-")


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "events_statements_enable_procedure", ["datadog.enable_events_statements_consumers", "invalid_proc"]
)
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_statement_samples_enable_consumers(dd_run_check, dbm_instance, root_conn, events_statements_enable_procedure):
    dbm_instance['query_samples']['events_statements_enable_procedure'] = events_statements_enable_procedure
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    all_consumers = {'events_statements_current', 'events_statements_history', 'events_statements_history_long'}

    # deliberately disable one of the consumers
    consumer_to_disable = 'events_statements_history_long'
    with closing(root_conn.cursor()) as cursor:
        cursor.execute(
            "UPDATE performance_schema.setup_consumers SET enabled='NO'  WHERE name = "
            "'{}';".format(consumer_to_disable)
        )

    original_enabled_consumers = mysql_check._statement_samples._get_enabled_performance_schema_consumers()
    assert consumer_to_disable not in original_enabled_consumers

    dd_run_check(mysql_check)

    enabled_consumers = mysql_check._statement_samples._get_enabled_performance_schema_consumers()
    if events_statements_enable_procedure == "datadog.enable_events_statements_consumers":
        # ensure that the consumer was re-enabled by the check run
        assert enabled_consumers == all_consumers
    else:
        # the consumer should not have been re-enabled
        assert enabled_consumers == original_enabled_consumers


@pytest.mark.unit
def test_normalize_queries(dbm_instance):
    check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    # Test the general case with a valid schema, digest and digest_text
    assert check._statement_metrics._normalize_queries(
        [
            {
                'schema': 'network',
                'digest': '44e35cee979ba420eb49a8471f852bbe15b403c89742704817dfbaace0d99dbb',
                'digest_text': 'SELECT * from table where name = ?',
                'count': 41,
                'time': 66721400,
                'lock_time': 18298000,
            }
        ]
    ) == [
        {
            'digest': '44e35cee979ba420eb49a8471f852bbe15b403c89742704817dfbaace0d99dbb',
            'schema': 'network',
            'digest_text': 'SELECT * from table where name = ?',
            'query_signature': u'761498b7d5f04d11',
            'dd_commands': None,
            'dd_comments': None,
            'dd_tables': None,
            'count': 41,
            'time': 66721400,
            'lock_time': 18298000,
        }
    ]

    # Test the case of null values for digest, schema and digest_text (which is what the row created when the table
    # is full returns)
    assert check._statement_metrics._normalize_queries(
        [
            {
                'digest': None,
                'schema': None,
                'digest_text': None,
                'count': 41,
                'time': 66721400,
                'lock_time': 18298000,
            }
        ]
    ) == [
        {
            'digest': None,
            'schema': None,
            'digest_text': None,
            'query_signature': None,
            'dd_commands': None,
            'dd_comments': None,
            'dd_tables': None,
            'count': 41,
            'time': 66721400,
            'lock_time': 18298000,
        }
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    "timer_end,now,uptime,expected_timestamp",
    [
        pytest.param(3019558487284095384, 1708025457, 100, 1711044915487, id="picoseconds not overflow"),
        pytest.param(3019558487284095384, 1708025457, 21466230, 1708025529560, id="picoseconds overflow"),
    ],
)
def test_statement_samples_calculate_timer_end(dbm_instance, timer_end, now, uptime, expected_timestamp):
    check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    row = {
        'timer_end': timer_end,
        'now': now,
        'uptime': uptime,
    }
    assert check._statement_samples._calculate_timer_end(row) == expected_timestamp
