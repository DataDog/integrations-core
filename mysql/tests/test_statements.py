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
from datadog_checks.base.utils.db.utils import DBMAsyncJob, RateLimitingTTLCache
from datadog_checks.base.utils.serialization import json
from datadog_checks.mysql import MySql, statements
from datadog_checks.mysql.statement_samples import MySQLStatementSamples, StatementTruncationState

from . import common
from .common import MYSQL_FLAVOR, MYSQL_REPLICATION, MYSQL_VERSION_PARSED

logger = logging.getLogger(__name__)

statement_samples_keys = ["query_samples", "statement_samples"]

# default test query to use that is guaranteed to succeed as it's using a fully qualified table name so it doesn't
# depend on a default schema being set on the connection
DEFAULT_FQ_SUCCESS_QUERY = "SELECT * FROM information_schema.TABLES"

CLOSE_TO_ZERO_INTERVAL = 0.0000001


@pytest.fixture
def dbm_instance(instance_complex):
    instance_complex['dbm'] = True
    instance_complex['disable_generic_tags'] = False
    # set the default for tests to run sychronously to ensure we don't have orphaned threads running around
    instance_complex['query_samples'] = {'enabled': True, 'run_sync': True, 'collection_interval': 1}
    # Set collection_interval close to 0. This is needed if the test runs the check multiple times.
    # This prevents DBMAsync from skipping job executions, as it is designed
    # to not execute jobs more frequently than their collection period.
    instance_complex['query_metrics'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': CLOSE_TO_ZERO_INTERVAL,
    }
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
@pytest.mark.parametrize("only_query_recent_statements", [False, True])
@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
def test_statement_metrics(
    aggregator,
    dd_run_check,
    dbm_instance,
    query,
    default_schema,
    datadog_agent,
    aurora_replication_role,
    only_query_recent_statements,
):
    dbm_instance['query_metrics']['only_query_recent_statements'] = only_query_recent_statements
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    def run_query(q):
        with mysql_check._connect() as db:
            with closing(db.cursor()) as cursor:
                if default_schema:
                    cursor.execute("USE " + default_schema)
                cursor.execute(q)

    with (
        mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as m_obfuscate_sql,
        mock.patch.object(mysql_check, '_get_is_aurora', passthrough=True) as m_get_is_aurora,
        mock.patch.object(
            mysql_check, '_get_aurora_replication_role', passthrough=True
        ) as m_get_aurora_replication_role,
    ):
        m_obfuscate_sql.side_effect = _obfuscate_sql
        m_get_is_aurora.return_value = False
        m_get_aurora_replication_role.return_value = None
        if aurora_replication_role:
            m_get_is_aurora.return_value = True
            m_get_aurora_replication_role.return_value = aurora_replication_role

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
    expected_tags = set(_expected_dbm_instance_tags(dbm_instance, mysql_check))
    if aurora_replication_role:
        expected_tags.add("replication_role:" + aurora_replication_role)
    elif MYSQL_FLAVOR.lower() in ('mysql', 'percona') and MYSQL_REPLICATION == 'classic':
        expected_tags.add("replication_role:primary")
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
            'SELECT {} FROM users where name=\'Johannes Chrysostomus Wolfgangus Theophilus Mozart\''.format(
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
    # This prevents DBMAsync from skipping job executions, as a job should not be executed
    # more frequently than its collection period.
    dbm_instance['query_samples']['collection_interval'] = CLOSE_TO_ZERO_INTERVAL

    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    if explain_strategy:
        mysql_check._statement_samples._preferred_explain_strategies = [explain_strategy]

    expected_tags = set(_expected_dbm_instance_tags(dbm_instance, mysql_check))
    if aurora_replication_role:
        expected_tags.add("replication_role:" + aurora_replication_role)

    with (
        mock.patch.object(mysql_check, '_get_is_aurora', passthrough=True) as m_get_is_aurora,
        mock.patch.object(
            mysql_check, '_get_aurora_replication_role', passthrough=True
        ) as m_get_aurora_replication_role,
    ):
        m_get_is_aurora.return_value = False
        m_get_aurora_replication_role.return_value = None
        if aurora_replication_role:
            m_get_is_aurora.return_value = True
            m_get_aurora_replication_role.return_value = aurora_replication_role

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
        else statement[:4093] + '...'
        if len(statement) > 4096
        else statement
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
        'end_event_id': None,
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
    mysql_check._performance_schema_enabled = False

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
    # This prevents DBMAsync from skipping job executions, as a job should not be executed
    # more frequently than its collection period.
    dbm_instance['query_samples']['collection_interval'] = CLOSE_TO_ZERO_INTERVAL
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
        expected_tags = _expected_dbm_job_err_tags(dbm_instance, mysql_check) + ('job:' + job,)
        if MYSQL_FLAVOR.lower() in ('mysql', 'percona') and MYSQL_REPLICATION == 'classic':
            expected_tags += ('replication_role:primary', 'cluster_uuid:{}'.format(mysql_check.cluster_uuid))
        aggregator.assert_metric(
            "dd.mysql.async_job.inactive_stop",
            tags=expected_tags,
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
        expected_tags = _expected_dbm_job_err_tags(dbm_instance, mysql_check) + ('job:' + job,)
        if MYSQL_FLAVOR.lower() in ('mysql', 'percona') and MYSQL_REPLICATION == 'classic':
            expected_tags += ('replication_role:primary', 'cluster_uuid:{}'.format(mysql_check.cluster_uuid))
        aggregator.assert_metric("dd.mysql.async_job.cancel", tags=expected_tags)


def _expected_dbm_instance_tags(dbm_instance, check):
    _tags = dbm_instance.get('tags', ()) + (
        'database_hostname:{}'.format('stubbed.hostname'),
        'database_instance:{}'.format('stubbed.hostname'),
        'server:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
        'dbms_flavor:{}'.format(MYSQL_FLAVOR.lower()),
    )
    if MYSQL_FLAVOR.lower() in ('mysql', 'percona'):
        _tags += ("server_uuid:{}".format(check.server_uuid),)
        if MYSQL_REPLICATION == 'classic':
            _tags += ('cluster_uuid:{}'.format(check.cluster_uuid),)
    return _tags


# the inactive job metrics are emitted from the main integrations
# directly to metrics-intake, so they should also be properly tagged with a resource
def _expected_dbm_job_err_tags(dbm_instance, check):
    _tags = dbm_instance['tags'] + (
        'database_hostname:{}'.format('stubbed.hostname'),
        'database_instance:{}'.format('stubbed.hostname'),
        'port:{}'.format(common.PORT),
        'server:{}'.format(common.HOST),
        'dd.internal.resource:database_instance:stubbed.hostname',
        'dbms_flavor:{}'.format(common.MYSQL_FLAVOR.lower()),
    )
    if MYSQL_FLAVOR.lower() in ('mysql', 'percona'):
        _tags += ("server_uuid:{}".format(check.server_uuid),)
    return _tags


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
            "UPDATE performance_schema.setup_consumers SET enabled='NO'  WHERE name = '{}';".format(consumer_to_disable)
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
            'query_signature': '761498b7d5f04d11',
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


@pytest.mark.unit
@pytest.mark.parametrize(
    "end_event_id,timer_end,uptime,event_timestamp_offset,window_seconds,expected_result",
    [
        # Test case 1: Event timestamp is within the window (should return False)
        pytest.param(123, 3019558487284095384, 21466230, 5000, 60, False, id="within_window"),
        # Test case 2: Event timestamp is outside the window (should return True)
        pytest.param(123, 3019558487284095384, 21466230, 65000, 60, True, id="outside_window"),
        # Test case 3: No end_event_id (should return False)
        pytest.param(None, 3019558487284095384, 21466230, 65000, 60, False, id="no_end_event_id"),
        # Test case 4: Event timestamp is before query end time (should return False)
        pytest.param(123, 3019558487284095384, 21466230, -5000, 60, False, id="before_query_end"),
        # Test case 5: Edge case - exactly at window boundary (should return True)
        pytest.param(123, 3019558487284095384, 21466230, 60000, 60, False, id="at_window_boundary"),
    ],
)
def test_has_sampled_since_completion(
    dbm_instance, end_event_id, timer_end, uptime, event_timestamp_offset, window_seconds, expected_result
):
    """Test the _has_sampled_since_completion method with various scenarios."""
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    now = 1708025457

    # Create a mock row with the provided parameters
    row = {
        'end_event_id': end_event_id,
        'timer_end': timer_end,
        'now': now,
        'uptime': uptime,
    }

    # Calculate the query end time
    query_end_time = mysql_check._statement_samples._calculate_timer_end(row)

    # Set the window size
    mysql_check._statement_samples._seen_samples_ratelimiter = RateLimitingTTLCache(
        maxsize=10000,
        ttl=window_seconds,
    )

    # Calculate event timestamp based on offset from query end time
    event_timestamp = query_end_time + event_timestamp_offset

    assert mysql_check._statement_samples._has_sampled_since_completion(row, event_timestamp) == expected_result


# TiDB-specific tests
@pytest.mark.unit
def test_tidb_statement_summary_query():
    """Test TiDB statement summary query generation"""
    from datadog_checks.mysql.statements import _get_tidb_statement_summary_query

    # Test without recent statements filter
    query, args = _get_tidb_statement_summary_query(only_query_recent_statements=False)
    assert "information_schema.cluster_statements_summary" in query
    assert "ORDER BY `EXEC_COUNT` DESC" in query
    assert args is None

    # Test with recent statements filter
    last_seen = '2024-01-01 00:00:00'
    query, args = _get_tidb_statement_summary_query(only_query_recent_statements=True, last_seen=last_seen)
    assert "WHERE `LAST_SEEN` >= %s" in query
    assert args == [last_seen]


@pytest.mark.unit
def test_normalize_tidb_statement_row():
    """Test normalization of TiDB statement row to MySQL format"""
    from datadog_checks.mysql.statements import _normalize_tidb_statement_row

    tidb_row = {
        'INSTANCE': '10.0.0.1:4000',
        'SCHEMA_NAME': 'test_db',
        'DIGEST': 'abc123',
        'DIGEST_TEXT': 'SELECT * FROM users',
        'EXEC_COUNT': 100,
        'SUM_LATENCY': 50000000,  # 50ms in nanoseconds
        'SUM_ERRORS': 2,
        'AVG_AFFECTED_ROWS': 0.5,
        'LAST_SEEN': '2024-01-01 00:00:00',
        # TiDB specific columns
        'AVG_LATENCY': 500000,
        'MAX_LATENCY': 1000000,
        'AVG_MEM': 1024,
        'MAX_MEM': 2048,
        'AVG_RESULT_ROWS': 10,
        'MAX_RESULT_ROWS': 20,
    }

    normalized = _normalize_tidb_statement_row(tidb_row)

    # Check standard MySQL columns
    assert normalized['schema_name'] == 'test_db'
    assert normalized['digest'] == 'abc123'
    assert normalized['digest_text'] == 'SELECT * FROM users'
    assert normalized['count_star'] == 100
    assert normalized['sum_timer_wait'] == 50000000
    assert normalized['sum_errors'] == 2
    assert normalized['sum_rows_affected'] == 50  # 0.5 * 100
    assert normalized['sum_rows_sent'] == 1000  # 10 * 100
    assert normalized['last_seen'] == '2024-01-01 00:00:00'

    # Check columns that TiDB doesn't have (should be 0)
    assert normalized['sum_lock_time'] == 0
    assert normalized['sum_rows_examined'] == 0
    assert normalized['sum_select_scan'] == 0
    assert normalized['sum_select_full_join'] == 0
    assert normalized['sum_no_index_used'] == 0
    assert normalized['sum_no_good_index_used'] == 0

    # Check TiDB-specific metrics are preserved
    assert normalized['_tidb_instance'] == '10.0.0.1:4000'
    assert normalized['_tidb_avg_latency'] == 500000
    assert normalized['_tidb_max_latency'] == 1000000
    assert normalized['_tidb_avg_mem'] == 1024
    assert normalized['_tidb_max_mem'] == 2048


@pytest.mark.unit
def test_is_tidb_statements_summary_available():
    """Test checking if TiDB cluster_statements_summary is available"""
    from datadog_checks.mysql.statements import _is_tidb_statements_summary_available

    class MockCursor:
        def __init__(self, has_table):
            self.has_table = has_table

        def execute(self, query):
            pass

        def fetchone(self):
            if self.has_table:
                return (1,)
            return None

    # Test when table exists
    cursor = MockCursor(has_table=True)
    assert _is_tidb_statements_summary_available(cursor) is True

    # Test when table doesn't exist
    cursor = MockCursor(has_table=False)
    assert _is_tidb_statements_summary_available(cursor) is False


@pytest.mark.unit
def test_collect_tidb_statement_metrics_rows():
    """Test collection of statement metrics from TiDB"""
    from datadog_checks.mysql.statements import _collect_tidb_statement_metrics_rows

    class MockCursor:
        def __init__(self, rows):
            self.rows = rows
            self.executed_query = None
            self.executed_args = None

        def execute(self, query, args=None):
            self.executed_query = query
            self.executed_args = args

        def fetchall(self):
            return self.rows

    # Sample TiDB rows
    tidb_rows = [
        {
            'INSTANCE': '10.0.0.1:4000',
            'SCHEMA_NAME': 'db1',
            'DIGEST': 'digest1',
            'DIGEST_TEXT': 'SELECT * FROM t1',
            'EXEC_COUNT': 10,
            'SUM_LATENCY': 1000000,
            'SUM_ERRORS': 0,
            'AVG_AFFECTED_ROWS': 0,
            'LAST_SEEN': '2024-01-01 00:00:00',
            'AVG_LATENCY': 100000,
            'MAX_LATENCY': 200000,
            'AVG_MEM': 100,
            'MAX_MEM': 200,
            'AVG_RESULT_ROWS': 1,
            'MAX_RESULT_ROWS': 2,
        }
    ]

    cursor = MockCursor(tidb_rows)

    # Test collection without filters
    rows = _collect_tidb_statement_metrics_rows(cursor)

    assert len(rows) == 1
    assert rows[0]['schema_name'] == 'db1'
    assert rows[0]['digest'] == 'digest1'
    assert rows[0]['count_star'] == 10
    assert rows[0]['sum_timer_wait'] == 1000000

    # Test collection with recent statements filter
    last_seen = '2024-01-01 00:00:00'
    rows = _collect_tidb_statement_metrics_rows(cursor, only_query_recent_statements=True, last_seen=last_seen)

    assert cursor.executed_args == [last_seen]
    assert "WHERE `LAST_SEEN` >= %s" in cursor.executed_query


@pytest.mark.unit
def test_tidb_statement_metrics_integration():
    """Test TiDB statement metrics collection integration with main check"""
    from datadog_checks.mysql import MySql

    from . import common

    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[{'server': 'localhost', 'user': 'datadog', 'dbm': True, 'query_metrics': {'enabled': True}}],
    )

    # Mock the TiDB detection
    with mock.patch.object(mysql_check, '_get_is_tidb', return_value=True):
        # This test verifies the integration point exists
        # Actual collection would require a real TiDB connection
        assert hasattr(mysql_check, '_get_is_tidb')


@pytest.mark.unit
def test_is_tidb_statements_summary_available_mock():
    """Test checking if TiDB cluster_statements_summary is available"""
    from datadog_checks.mysql.statements import _is_tidb_statements_summary_available

    # Test when table exists
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchone.return_value = (1,)
    assert _is_tidb_statements_summary_available(mock_cursor) is True
    mock_cursor.execute.assert_called_once()

    # Test when table doesn't exist
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchone.return_value = None
    assert _is_tidb_statements_summary_available(mock_cursor) is False

    # Test when exception occurs
    mock_cursor = mock.MagicMock()
    mock_cursor.execute.side_effect = Exception("Table not found")
    assert _is_tidb_statements_summary_available(mock_cursor) is False


# TiDB-specific explain tests
@pytest.mark.unit
def test_tidb_explain_plan_from_cluster_statements():
    """Test that EXPLAIN plans work for TiDB queries"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Mock database connection first
    mock_db = mock.MagicMock()

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})
    statement_samples._db = mock_db
    # Initialize TiDB-specific strategies
    statement_samples._get_sample_collection_strategy()

    # Mock database connection and cursor
    mock_cursor = mock.MagicMock()
    mock_db.cursor.return_value.__enter__.return_value = mock_cursor

    # Mock TiDB EXPLAIN output
    tidb_explain_output = json.dumps(
        {
            "id": "TableReader_5",
            "estRows": "10000.00",
            "task": "root",
            "access object": "",
            "operator info": "data:TableFullScan_4",
            "operatorInfo": "data:TableFullScan_4",
            "childTasks": [
                {
                    "id": "TableFullScan_4",
                    "estRows": "10000.00",
                    "task": "cop[tikv]",
                    "access object": "table:users",
                    "operator info": "keep order:false, stats:pseudo",
                }
            ],
        }
    )

    mock_cursor.fetchone.return_value = [tidb_explain_output]

    # Test explain
    statement = "SELECT * FROM users WHERE id = 1"
    obfuscated_statement = "SELECT * FROM users WHERE id = ?"

    plan = statement_samples._run_explain_tidb('test_db', mock_cursor, statement, obfuscated_statement)

    # Verify EXPLAIN was called with tidb_json format for TiDB
    mock_cursor.execute.assert_called_with('EXPLAIN FORMAT=tidb_json SELECT * FROM users WHERE id = 1')

    # Verify plan was returned
    assert plan == tidb_explain_output


def test_tidb_rate_limiting():
    """Test that rate limiting works for TiDB statement samples"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                    'samples_per_hour_per_query': 1,  # Very restrictive for testing
                },
            }
        ],
    )

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Test rate limiter
    query_cache_key = ('test_db', 'query_signature_123')

    # First acquire should succeed
    assert statement_samples._explained_statements_ratelimiter.acquire(query_cache_key) is True

    # Second acquire should fail due to rate limiting
    assert statement_samples._explained_statements_ratelimiter.acquire(query_cache_key) is False


@pytest.mark.unit
def test_tidb_node_instance_metadata():
    """Test that TiDB node instance is included in statement samples"""
    # Mock the connection before creating the check
    with mock.patch('datadog_checks.mysql.util.connect_with_session_variables'):
        mysql_check = MySql(
            common.CHECK_NAME,
            {},
            instances=[
                {
                    'server': 'localhost',
                    'user': 'datadog',
                    'dbm': True,
                    'statement_samples': {
                        'enabled': True,
                    },
                }
            ],
        )

        # Mock TiDB detection
        mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

        # Create statement samples collector
        statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})
        # Initialize _tags and _tags_str which are normally set by the parent class
        statement_samples._tags = []
        statement_samples._tags_str = ""

    # Mock database connection
    mock_db = mock.MagicMock()
    statement_samples._db = mock_db
    statement_samples._explained_statements_ratelimiter = mock.MagicMock()
    statement_samples._explained_statements_ratelimiter.acquire.return_value = True
    statement_samples._seen_samples_ratelimiter = mock.MagicMock()
    statement_samples._seen_samples_ratelimiter.acquire.return_value = True

    # Test row with TiDB node instance
    row = {
        'sql_text': 'SELECT * FROM orders',
        'digest_text': 'SELECT * FROM orders',
        'current_schema': 'ecommerce',
        'processlist_host': 'tidb-node-2.cluster.local:4000',
        'timer_end': 123456789,
        'timer_wait_ns': 1000000,
        'rows_affected': 0,
        'rows_sent': 100,
        'rows_examined': 100,
        'processlist_user': 'app_user',
        'processlist_db': 'ecommerce',
        'digest': 'test_digest',
        'lock_time_ns': 0,
        'select_full_join': 0,
        'select_full_range_join': 0,
        'select_range': 0,
        'select_range_check': 0,
        'select_scan': 1,
        'sort_merge_passes': 0,
        'sort_range': 0,
        'sort_rows': 0,
        'sort_scan': 0,
        'no_index_used': 0,
        'no_good_index_used': 0,
    }

    # Mock required methods
    with mock.patch('datadog_checks.mysql.statement_samples.obfuscate_sql_with_metadata') as mock_obfuscate:
        mock_obfuscate.return_value = {'query': 'SELECT * FROM orders', 'metadata': {'tables': ['orders']}}

        with mock.patch('datadog_checks.mysql.statement_samples.compute_sql_signature') as mock_signature:
            mock_signature.return_value = 'test_signature'

            with mock.patch('datadog_checks.mysql.statement_samples.datadog_agent') as mock_agent:
                mock_agent.obfuscate_sql_exec_plan.return_value = '{}'
                mock_agent.get_version.return_value = '7.0.0'

                with mock.patch('datadog_checks.mysql.statement_samples.compute_exec_plan_signature') as mock_plan_sig:
                    mock_plan_sig.return_value = 'plan_signature'

                    with mock.patch('datadog_checks.mysql.statement_samples.get_truncation_state') as mock_trunc:
                        mock_trunc.return_value = mock.MagicMock(value='not_truncated')

                        # Mock explain statement to return empty plan
                        statement_samples._explain_statement = mock.MagicMock(return_value=('{}', []))

                        # Call _collect_plan_for_statement
                        event = statement_samples._collect_plan_for_statement(row)

    # Verify event was created
    assert event is not None

    # Verify TiDB node instance is included
    assert 'tidb' in event
    assert 'node_instance' in event['tidb']
    assert event['tidb']['node_instance'] == 'tidb-node-2.cluster.local:4000'

    # Verify network.client.ip still contains the processlist_host for compatibility
    assert event['network']['client']['ip'] == 'tidb-node-2.cluster.local:4000'


def test_tidb_has_sampled_since_completion():
    """Test that _has_sampled_since_completion handles TiDB correctly"""
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog', 'dbm': True}])

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Mock database
    mock_db = mock.MagicMock()
    statement_samples._db = mock_db

    # For TiDB, should always return False
    row = {'end_event_id': 12345}  # Even with end_event_id set
    result = statement_samples._has_sampled_since_completion(row, 1234567890)

    assert result is False


def test_tidb_use_prefetched_plan():
    """Test that TiDB uses pre-fetched plan from cluster_statements_summary"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})
    # Initialize _tags and _tags_str which are normally set by the parent class
    statement_samples._tags = []
    statement_samples._tags_str = ""

    # Mock database connection
    mock_db = mock.MagicMock()
    statement_samples._db = mock_db
    statement_samples._explained_statements_ratelimiter = mock.MagicMock()
    statement_samples._explained_statements_ratelimiter.acquire.return_value = True
    statement_samples._seen_samples_ratelimiter = mock.MagicMock()
    statement_samples._seen_samples_ratelimiter.acquire.return_value = True

    # Test row with execution plan from TiDB
    row = {
        'sql_text': 'SELECT * FROM users WHERE id = ?',
        'digest_text': 'SELECT * FROM users WHERE id = ?',
        'current_schema': 'test_db',
        'execution_plan': 'id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk\n'
        'Point_Get_1\troot\t1\ttable:users, handle:id\t1\ttime:500µs\tN/A\tN/A',
        'timer_end': 123456789,
        'timer_wait_ns': 1000000,
        'rows_affected': 0,
        'rows_sent': 1,
        'rows_examined': 1,
        'processlist_user': 'test_user',
        'processlist_host': 'localhost',
        'processlist_db': 'test_db',
        # Add other required fields
        'digest': 'test_digest',
        'lock_time_ns': 0,
        'select_full_join': 0,
        'select_full_range_join': 0,
        'select_range': 0,
        'select_range_check': 0,
        'select_scan': 0,
        'sort_merge_passes': 0,
        'sort_range': 0,
        'sort_rows': 0,
        'sort_scan': 0,
        'no_index_used': 0,
        'no_good_index_used': 0,
    }

    # Mock required methods
    with mock.patch('datadog_checks.mysql.statement_samples.obfuscate_sql_with_metadata') as mock_obfuscate:
        mock_obfuscate.return_value = {'query': 'SELECT * FROM users WHERE id = ?', 'metadata': {'tables': ['users']}}

        with mock.patch('datadog_checks.mysql.statement_samples.compute_sql_signature') as mock_signature:
            mock_signature.return_value = 'test_signature'

            with mock.patch('datadog_checks.mysql.statement_samples.datadog_agent') as mock_agent:
                mock_agent.obfuscate_sql_exec_plan.side_effect = lambda x, normalize=False: x
                mock_agent.get_version.return_value = '7.0.0'

                with mock.patch('datadog_checks.mysql.statement_samples.compute_exec_plan_signature') as mock_plan_sig:
                    mock_plan_sig.return_value = 'plan_signature'

                    with mock.patch('datadog_checks.mysql.statement_samples.get_truncation_state') as mock_trunc:
                        mock_trunc.return_value = mock.MagicMock(value='not_truncated')

                        # Call _collect_plan_for_statement
                        event = statement_samples._collect_plan_for_statement(row)

    # Should have successfully created an event with the pre-fetched plan
    assert event is not None
    # For TiDB text plans, obfuscate should NOT be called
    mock_agent.obfuscate_sql_exec_plan.assert_not_called()
    # The plan should be MySQL-compatible format in db.plan.definition
    plan_def = event['db']['plan']['definition']
    # Should be valid JSON
    parsed = json.loads(plan_def)
    # Should be MySQL-compatible format
    assert 'query_block' in parsed
    assert parsed['query_block']['table']['table_name'] == 'users'
    assert parsed['query_block']['table']['access_type'] == 'const'

    # The native TiDB format should be in mysql.execution_plan
    assert 'mysql' in event
    assert 'execution_plan' in event['mysql']
    native_plan = json.loads(event['mysql']['execution_plan'])
    assert isinstance(native_plan, list)
    assert len(native_plan) == 1
    assert native_plan[0]['id'] == 'Point_Get_1'

    # Verify TiDB node instance is included
    assert 'tidb' in event
    assert 'node_instance' in event['tidb']
    assert event['tidb']['node_instance'] == 'localhost'


def test_tidb_prefetched_plan_bytes():
    """Test that TiDB handles execution plan in bytes format"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})
    # Initialize _tags and _tags_str which are normally set by the parent class
    statement_samples._tags = []
    statement_samples._tags_str = ""

    # Mock database connection
    mock_db = mock.MagicMock()
    statement_samples._db = mock_db
    statement_samples._explained_statements_ratelimiter = mock.MagicMock()
    statement_samples._explained_statements_ratelimiter.acquire.return_value = True
    statement_samples._seen_samples_ratelimiter = mock.MagicMock()
    statement_samples._seen_samples_ratelimiter.acquire.return_value = True

    # Test row with execution plan as string (what TiDB returns after decoding)
    row = {
        'sql_text': 'SELECT * FROM users WHERE id = ?',
        'digest_text': 'SELECT * FROM users WHERE id = ?',
        'current_schema': 'test_db',
        'execution_plan': (
            'id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk\n'
            'Point_Get_1\troot\t1\ttable:users, handle:id\t1\ttime:500µs\tN/A\tN/A'
        ),  # string format with header
        'timer_end': 123456789,
        'timer_wait_ns': 1000000,
        'rows_affected': 0,
        'rows_sent': 1,
        'rows_examined': 1,
        'processlist_user': 'test_user',
        'processlist_host': 'localhost',
        'processlist_db': 'test_db',
        'digest': 'test_digest',
        'lock_time_ns': 0,
        'select_full_join': 0,
        'select_full_range_join': 0,
        'select_range': 0,
        'select_range_check': 0,
        'select_scan': 0,
        'sort_merge_passes': 0,
        'sort_range': 0,
        'sort_rows': 0,
        'sort_scan': 0,
        'no_index_used': 0,
        'no_good_index_used': 0,
    }

    # Mock required methods
    with mock.patch('datadog_checks.mysql.statement_samples.obfuscate_sql_with_metadata') as mock_obfuscate:
        mock_obfuscate.return_value = {'query': 'SELECT * FROM users WHERE id = ?', 'metadata': {'tables': ['users']}}

        with mock.patch('datadog_checks.mysql.statement_samples.compute_sql_signature') as mock_signature:
            mock_signature.return_value = 'test_signature'

            with mock.patch('datadog_checks.mysql.statement_samples.datadog_agent') as mock_agent:
                mock_agent.obfuscate_sql_exec_plan.side_effect = lambda x, normalize=False: x
                mock_agent.get_version.return_value = '7.0.0'

                with mock.patch('datadog_checks.mysql.statement_samples.compute_exec_plan_signature') as mock_plan_sig:
                    mock_plan_sig.return_value = 'plan_signature'

                    with mock.patch('datadog_checks.mysql.statement_samples.get_truncation_state') as mock_trunc:
                        mock_trunc.return_value = mock.MagicMock(value='not_truncated')

                        # Call _collect_plan_for_statement
                        event = statement_samples._collect_plan_for_statement(row)

    # Should have successfully created an event with the pre-fetched plan
    assert event is not None
    # For TiDB text plans, obfuscate should NOT be called
    mock_agent.obfuscate_sql_exec_plan.assert_not_called()

    # The plan definition should be a MySQL-compatible JSON string
    plan_def = event['db']['plan']['definition']
    # If it's bytes, decode it
    if isinstance(plan_def, bytes):
        plan_def = plan_def.decode('utf-8')
    assert isinstance(plan_def, str)
    # Parse it to verify MySQL-compatible structure
    parsed_plan = json.loads(plan_def)
    assert 'query_block' in parsed_plan
    assert 'table' in parsed_plan['query_block']
    assert parsed_plan['query_block']['table']['table_name'] == 'users'
    assert parsed_plan['query_block']['table']['access_type'] == 'const'  # Point_Get maps to 'const'

    # The mysql.execution_plan should contain the native TiDB JSON array
    assert 'mysql' in event
    assert 'execution_plan' in event['mysql']
    exec_plan = event['mysql']['execution_plan']
    assert isinstance(exec_plan, str)
    # Parse to verify it's the native TiDB format
    parsed_exec = json.loads(exec_plan)
    assert isinstance(parsed_exec, list)
    assert len(parsed_exec) == 1
    assert parsed_exec[0]['id'] == 'Point_Get_1'
    assert parsed_exec[0]['taskType'] == 'root'


def test_tidb_plan_mysql_conversion():
    """Test conversion of TiDB plan to MySQL-compatible format"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})
    # Initialize _tags and _tags_str which are normally set by the parent class
    statement_samples._tags = []
    statement_samples._tags_str = ""

    # Test various TiDB operator types
    tidb_plans = [
        {
            "id": "Point_Get_1",
            "taskType": "root",
            "estRows": "1",
            "actRows": "1",
            "operatorInfo": "table:users, handle:1",
        },
        {
            "id": "IndexRangeScan_10",
            "taskType": "cop[tikv]",
            "estRows": "100",
            "actRows": "95",
            "operatorInfo": "table:orders, index:idx_date(created_at)",
        },
        {
            "id": "TableFullScan_5",
            "taskType": "cop[tikv]",
            "estRows": "10000",
            "actRows": "10000",
            "operatorInfo": "table:products",
        },
    ]

    # Test Point_Get conversion
    mysql_plan = statement_samples._convert_tidb_plan_to_mysql_format(json.dumps([tidb_plans[0]]))
    parsed = json.loads(mysql_plan)
    assert parsed['query_block']['table']['table_name'] == 'users'
    assert parsed['query_block']['table']['access_type'] == 'const'
    assert parsed['query_block']['table']['key'] == 'PRIMARY'

    # Test IndexRangeScan conversion
    mysql_plan = statement_samples._convert_tidb_plan_to_mysql_format(json.dumps([tidb_plans[1]]))
    parsed = json.loads(mysql_plan)
    assert parsed['query_block']['table']['table_name'] == 'orders'
    assert parsed['query_block']['table']['access_type'] == 'range'
    assert parsed['query_block']['table']['key'] == 'idx_date(created_at)'

    # Test TableFullScan conversion
    mysql_plan = statement_samples._convert_tidb_plan_to_mysql_format(json.dumps([tidb_plans[2]]))
    parsed = json.loads(mysql_plan)
    assert parsed['query_block']['table']['table_name'] == 'products'
    assert parsed['query_block']['table']['access_type'] == 'ALL'


def test_tidb_plan_json_string_format():
    """Test that TiDB plan definition is a JSON string in the event, matching MySQL format"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Test plan text with multiple nodes
    plan_text = (
        "id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk\n"
        "Projection_7\troot\t1\tmercari.items_order_datetime.order_datetime\t0\t"
        "time:519.2µs, loops:1\t1016 Bytes\tN/A\n"
        "└─TopN_8\troot\t1\tmercari.items_order_datetime.order_datetime:desc, offset:?, count:?\t0\t"
        "time:516.7µs, loops:1\t0 Bytes\tN/A\n"
        "  └─Point_Get_13\troot\t1.00\ttable:items_order_datetime, clustered index:PRIMARY(item_id)\t0\t"
        "time:508.7µs, loops:2\tN/A\tN/A"
    )

    # Parse the plan
    parsed_json_str = statement_samples._parse_tidb_text_plan(plan_text)

    # The method returns a JSON string, parse it to verify it's valid
    parsed_obj = json.loads(parsed_json_str)

    # Verify it's a list of objects
    assert isinstance(parsed_obj, list)
    assert len(parsed_obj) == 3

    # Check first node
    assert parsed_obj[0]['id'] == 'Projection_7'
    assert parsed_obj[0]['taskType'] == 'root'
    assert parsed_obj[0]['estRows'] == '1'
    assert parsed_obj[0]['operatorInfo'] == 'mercari.items_order_datetime.order_datetime'

    # Check second node (with tree prefix removed)
    assert parsed_obj[1]['id'] == 'TopN_8'
    assert parsed_obj[1]['taskType'] == 'root'

    # Check third node
    assert parsed_obj[2]['id'] == 'Point_Get_13'
    assert parsed_obj[2]['taskType'] == 'root'


def test_tidb_plan_json_parsing():
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Test realistic TiDB plan text
    plan_text = """\tid\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk
\tProjection_6\troot\t1\tmercari.users.id, mercari.users.photo_id\t1\ttime:779.9µs, loops:2\t2.61 KB\tN/A
\t└─HashJoin_8\troot\t1\tCARTESIAN left outer join\t1\ttime:765.2µs, loops:2\t50.2 KB\t0 Bytes
\t  ├─Point_Get_9(Build)\troot\t1\ttable:users, handle:?\t1\ttime:545.5µs, loops:2\tN/A\tN/A
\t  └─Point_Get_10(Probe)\troot\t1\ttable:user_personal_attributes, handle:?\t0\ttime:582.5µs, loops:1\tN/A\tN/A"""

    parsed = statement_samples._parse_tidb_text_plan(plan_text)

    # Should be valid JSON
    plan_json = json.loads(parsed)

    # Should be a list of nodes
    assert isinstance(plan_json, list)
    assert len(plan_json) == 4  # 4 nodes in the plan

    # Check root node (first in list)
    assert plan_json[0]['id'] == 'Projection_6'
    assert plan_json[0]['taskType'] == 'root'
    assert plan_json[0]['estRows'] == '1'
    assert plan_json[0]['actRows'] == '1'

    # Check HashJoin node
    hash_join = plan_json[1]
    assert hash_join['id'] == 'HashJoin_8'
    assert hash_join['taskType'] == 'root'
    assert 'left outer join' in hash_join['operatorInfo']

    # Check Point_Get nodes
    assert plan_json[2]['id'] == 'Point_Get_9(Build)'
    assert plan_json[3]['id'] == 'Point_Get_10(Probe)'


def test_tidb_plan_json_parsing_escaped():
    """Test TiDB plan text to JSON parsing with escaped characters"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Test TiDB plan text with escaped newlines and tabs (as seen in real data)
    plan_text = (
        "\\tid\\ttask\\testRows\\toperator info\\tactRows\\texecution info\\tmemory\\tdisk\\n"
        "\\tUpdate_3\\troot\\t0\\tN/A\\t0\\ttime:2.38ms, loops:2\\t23.7 KB\\tN/A\\n"
        "\\t└─Point_Get_1\\troot\\t1\\ttable:users, handle:?, lock\\t1\\t"
        "time:766.2µs, loops:2\\tN/A\\tN/A"
    )

    parsed = statement_samples._parse_tidb_text_plan(plan_text)

    # Should be valid JSON
    plan_json = json.loads(parsed)

    # Should be a list of nodes
    assert isinstance(plan_json, list)
    assert len(plan_json) == 2  # 2 nodes in the plan

    # Check root node
    assert plan_json[0]['id'] == 'Update_3'
    assert plan_json[0]['taskType'] == 'root'
    assert plan_json[0]['operatorInfo'] == 'N/A'

    # Check Point_Get child
    point_get = plan_json[1]
    assert point_get['id'] == 'Point_Get_1'
    assert 'table:users' in point_get['operatorInfo']


def test_tidb_explain_skip_parameterized_queries():
    """Test that TiDB skips EXPLAIN for parameterized queries"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Mock database connection and cursor
    mock_cursor = mock.MagicMock()
    mock_db = mock.MagicMock()
    mock_db.cursor.return_value.__enter__.return_value = mock_cursor
    statement_samples._db = mock_db

    # Test with parameterized query (contains ?)
    statement = "select ? from information_schema.tables where table_schema = ? and table_name = ? limit ?"
    obfuscated_statement = statement  # Same in this case

    plan = statement_samples._run_explain_tidb('information_schema', mock_cursor, statement, obfuscated_statement)

    # Should return None for parameterized queries
    assert plan is None

    # Verify no execute was called
    mock_cursor.execute.assert_not_called()


def test_tidb_explain_format_tidb_json():
    """Test that TiDB uses FORMAT=tidb_json instead of FORMAT=json"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Mock database connection and cursor
    mock_cursor = mock.MagicMock()
    mock_db = mock.MagicMock()
    mock_db.cursor.return_value.__enter__.return_value = mock_cursor
    statement_samples._db = mock_db

    # Mock TiDB EXPLAIN output with tidb_json format
    tidb_json_output = json.dumps(
        {
            "SQL": (
                "insert into auth ( uuid, access_token ) values ( ? ) "
                "on duplicate key update access_token = access_token"
            ),
            "Plan": {"TP": "Insert", "Schema": "test"},
        }
    )

    mock_cursor.fetchone.return_value = [tidb_json_output]

    # Test explain with INSERT ON DUPLICATE KEY UPDATE
    statement = (
        "insert into auth ( uuid, access_token ) values ( 'test' ) on duplicate key update access_token = access_token"
    )
    obfuscated_statement = (
        "insert into auth ( uuid, access_token ) values ( ? ) on duplicate key update access_token = access_token"
    )

    plan = statement_samples._run_explain_tidb('test_db', mock_cursor, statement, obfuscated_statement)

    # Verify EXPLAIN FORMAT=tidb_json was called
    expected_query = (
        "EXPLAIN FORMAT=tidb_json insert into auth ( uuid, access_token ) values ( 'test' ) "
        "on duplicate key update access_token = access_token"
    )
    mock_cursor.execute.assert_called_with(expected_query)

    # Verify plan was returned
    assert plan == tidb_json_output


def test_tidb_plan_parsing_real_output():
    """Test parsing of actual TiDB execution plan output with multiple lines"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})
    # Initialize _tags and _tags_str which are normally set by the parent class
    statement_samples._tags = []
    statement_samples._tags_str = ""

    # Real TiDB plan output - convert to tab-separated format
    plan_text = (
        "id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk\n"
        "Projection_7\troot\t1\tmercari.items_order_datetime.order_datetime\t0\t"
        "time:519.2µs, loops:1, Concurrency:OFF\t1016 Bytes\tN/A\n"
        "└─TopN_8\troot\t1\tmercari.items_order_datetime.order_datetime:desc, offset:?, count:?\t0\t"
        "time:516.7µs, loops:1\t0 Bytes\tN/A\n"
        "  └─Point_Get_13\troot\t1.00\ttable:items_order_datetime, clustered index:PRIMARY(item_id)\t0\t"
        "time:508.7µs, loops:2, Get:{num_rpc:1, total_time:470.9µs}, time_detail: "
        "{total_process_time: 41µs, total_wait_time: 49.4µs, total_kv_read_wall_time: 96.9µs, "
        "tikv_wall_time: 122.9µs}, scan_detail: {total_keys: 1, get_snapshot_time: 13.5µs, "
        "rocksdb: {block: {cache_hit_count: 9}}}\tN/A\tN/A"
    )

    parsed = statement_samples._parse_tidb_text_plan(plan_text)

    # Should be valid JSON
    plan_json = json.loads(parsed)

    # Expected JSON structure - flat array like TiDB's FORMAT=tidb_json
    expected_json = [
        {
            "id": "Projection_7",
            "estRows": "1",
            "taskType": "root",
            "operatorInfo": "mercari.items_order_datetime.order_datetime",
            "actRows": "0",
            "executionInfo": "time:519.2µs, loops:1, Concurrency:OFF",
            "memory": "1016 Bytes",
        },
        {
            "id": "TopN_8",
            "estRows": "1",
            "taskType": "root",
            "operatorInfo": "mercari.items_order_datetime.order_datetime:desc, offset:?, count:?",
            "actRows": "0",
            "executionInfo": "time:516.7µs, loops:1",
            "memory": "0 Bytes",
        },
        {
            "id": "Point_Get_13",
            "estRows": "1.00",
            "taskType": "root",
            "operatorInfo": "table:items_order_datetime, clustered index:PRIMARY(item_id)",
            "actRows": "0",
            "executionInfo": (
                "time:508.7µs, loops:2, Get:{num_rpc:1, total_time:470.9µs}, time_detail: "
                "{total_process_time: 41µs, total_wait_time: 49.4µs, total_kv_read_wall_time: 96.9µs, "
                "tikv_wall_time: 122.9µs}, scan_detail: {total_keys: 1, get_snapshot_time: 13.5µs, "
                "rocksdb: {block: {cache_hit_count: 9}}}"
            ),
        },
    ]

    # Verify the parsed JSON matches expected structure
    assert plan_json == expected_json


def test_tidb_plan_parsing_edge_cases():
    """Test edge cases in TiDB plan parsing"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Test 1: Empty plan
    empty_plan = ""
    parsed = statement_samples._parse_tidb_text_plan(empty_plan)
    result = json.loads(parsed)
    assert 'raw_plan' in result
    assert result['raw_plan'] == ""

    # Test 2: Only header, no data
    header_only = "id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk"
    parsed = statement_samples._parse_tidb_text_plan(header_only)
    result = json.loads(parsed)
    assert 'raw_plan' in result

    # Test 3: Malformed line (fewer columns than expected)
    malformed_plan = """id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk
TableScan_1\troot\t100"""  # Only 3 columns instead of 8

    parsed = statement_samples._parse_tidb_text_plan(malformed_plan)
    result = json.loads(parsed)
    # Should return empty array when no valid nodes
    assert result == []  # No valid nodes due to column count mismatch

    # Test 4: Plan with N/A values
    plan_with_na = """id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk
TableScan_1\troot\tN/A\ttable:test\tN/A\ttime:1ms\tN/A\tN/A"""

    parsed = statement_samples._parse_tidb_text_plan(plan_with_na)
    result = json.loads(parsed)

    # Should return flat array
    assert len(result) == 1
    node = result[0]
    assert node['id'] == 'TableScan_1'
    assert node['estRows'] == "0"  # N/A converted to "0" for numeric fields
    assert node['actRows'] == "0"  # N/A converted to "0" for numeric fields
    assert 'memory' not in node  # N/A fields are omitted
    assert 'disk' not in node


def test_tidb_plan_parsing_simple_flat_structure():
    """Test parsing of simple TiDB plan without tree structure"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Simple plan with single node (no tree indicators)
    simple_plan = """id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk
Show_5\troot\t1\t\t13\ttime:10.8ms, loops:2\t1.23 KB\tN/A"""

    parsed = statement_samples._parse_tidb_text_plan(simple_plan)
    result = json.loads(parsed)

    # Expected JSON - flat array like TiDB FORMAT=tidb_json
    expected_json = [
        {
            "id": "Show_5",
            "estRows": "1",
            "taskType": "root",
            "actRows": "13",
            "executionInfo": "time:10.8ms, loops:2",
            "memory": "1.23 KB",
        }
    ]

    # Verify the parsed JSON matches expected structure
    assert result == expected_json


def test_tidb_plan_parsing_show_statement():
    """Test parsing of TiDB SHOW statement execution plan"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Plan that was producing incorrect JSON in the original issue
    plan_text = """id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk
└─Show_5\troot\t1\t\t13\ttime:10.8ms, loops:2\t1.23 KB\tN/A"""

    parsed = statement_samples._parse_tidb_text_plan(plan_text)
    result = json.loads(parsed)

    # Expected correct JSON structure - flat array
    expected_json = [
        {
            "id": "Show_5",
            "estRows": "1",
            "taskType": "root",
            "actRows": "13",
            "executionInfo": "time:10.8ms, loops:2",
            "memory": "1.23 KB",
        }
    ]

    # Verify the parsed JSON is correct (not the broken format from the issue)
    assert result == expected_json

    # This should NOT produce the broken format shown in the issue:
    # {
    #   "id":"",
    #   "task":"└─Show_5",
    #   "estRows":"root",
    #   "operator":"1",
    #   "actRows":"",
    #   "execution":"13",
    #   "memory":"time:10.8ms, loops:2",
    #   "disk":null
    # }


def test_tidb_plan_parsing_reference_format():
    """Test parsing matches TiDB's actual FORMAT=tidb_json output"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Simulate TiDB text plan for: SELECT * FROM auth WHERE uuid = 'test'
    plan_text = """id\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk
Point_Get_1\troot\t1.00\ttable:auth, clustered index:PRIMARY(uuid)\t1\ttime:500µs\tN/A\tN/A"""

    parsed = statement_samples._parse_tidb_text_plan(plan_text)
    result = json.loads(parsed)

    # Expected format matching TiDB's EXPLAIN FORMAT=tidb_json output
    expected_json = [
        {
            "id": "Point_Get_1",
            "estRows": "1.00",
            "taskType": "root",
            "operatorInfo": "table:auth, clustered index:PRIMARY(uuid)",
            "actRows": "1",
            "executionInfo": "time:500µs",
        }
    ]

    # Verify matches TiDB's actual format
    assert result == expected_json


def test_tidb_plan_parsing_with_empty_first_column():
    """Test parsing TiDB plan with empty first column (actual format from user)"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Real TiDB plan with empty first column before id
    plan_text = (
        "\tid\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk\n"
        "\tPoint_Get_1\troot\t1\ttable:item_description, clustered index:PRIMARY(item_id)\t1\t"
        "time:954.1µs, loops:2, Get:{num_rpc:1, total_time:922.7µs}, time_detail: "
        "{total_process_time: 118.7µs, total_wait_time: 475.9µs, total_kv_read_wall_time: 599.8µs, "
        "tikv_wall_time: 627.3µs}, scan_detail: {total_process_keys: 1, total_process_keys_size: 102, "
        "total_keys: 1, get_snapshot_time: 442.9µs, rocksdb: {block: {cache_hit_count: 10}}}\tN/A\tN/A"
    )

    parsed = statement_samples._parse_tidb_text_plan(plan_text)
    result = json.loads(parsed)

    # Expected JSON
    expected_json = [
        {
            "id": "Point_Get_1",
            "estRows": "1",
            "taskType": "root",
            "operatorInfo": "table:item_description, clustered index:PRIMARY(item_id)",
            "actRows": "1",
            "executionInfo": (
                "time:954.1µs, loops:2, Get:{num_rpc:1, total_time:922.7µs}, time_detail: "
                "{total_process_time: 118.7µs, total_wait_time: 475.9µs, total_kv_read_wall_time: 599.8µs, "
                "tikv_wall_time: 627.3µs}, scan_detail: {total_process_keys: 1, total_process_keys_size: 102, "
                "total_keys: 1, get_snapshot_time: 442.9µs, rocksdb: {block: {cache_hit_count: 10}}}"
            ),
        }
    ]

    # Verify correct parsing with empty first column
    assert result == expected_json


def test_tidb_plan_parsing_multi_level_with_empty_column():
    """Test parsing multi-level TiDB plan with empty first column and tree structure"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Multi-level plan from user's example
    plan_text = (
        "\tid\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk\n"
        "\tProjection_7\troot\t1\tmercari.items_order_datetime.order_datetime\t0\t"
        "time:475.4µs, loops:1, Concurrency:OFF\t1016 Bytes\tN/A\n"
        "\t└─TopN_8\troot\t1\tmercari.items_order_datetime.order_datetime:desc, offset:?, count:?\t0\t"
        "time:471.9µs, loops:1\t0 Bytes\tN/A\n"
        "\t  └─Point_Get_13\troot\t1.00\ttable:items_order_datetime, clustered index:PRIMARY(item_id)\t0\t"
        "time:460.4µs, loops:2, Get:{num_rpc:1, total_time:426.5µs}, time_detail: "
        "{total_process_time: 45.8µs, total_wait_time: 38.7µs, total_kv_read_wall_time: 87.5µs, "
        "tikv_wall_time: 113.6µs}, scan_detail: {total_keys: 1, get_snapshot_time: 10µs, "
        "rocksdb: {block: {cache_hit_count: 9}}}\tN/A\tN/A"
    )

    parsed = statement_samples._parse_tidb_text_plan(plan_text)
    result = json.loads(parsed)

    # Expected flat array (no hierarchy)
    expected_json = [
        {
            "id": "Projection_7",
            "estRows": "1",
            "taskType": "root",
            "operatorInfo": "mercari.items_order_datetime.order_datetime",
            "actRows": "0",
            "executionInfo": "time:475.4µs, loops:1, Concurrency:OFF",
            "memory": "1016 Bytes",
        },
        {
            "id": "TopN_8",
            "estRows": "1",
            "taskType": "root",
            "operatorInfo": "mercari.items_order_datetime.order_datetime:desc, offset:?, count:?",
            "actRows": "0",
            "executionInfo": "time:471.9µs, loops:1",
            "memory": "0 Bytes",
        },
        {
            "id": "Point_Get_13",
            "estRows": "1.00",
            "taskType": "root",
            "operatorInfo": "table:items_order_datetime, clustered index:PRIMARY(item_id)",
            "actRows": "0",
            "executionInfo": (
                "time:460.4µs, loops:2, Get:{num_rpc:1, total_time:426.5µs}, time_detail: "
                "{total_process_time: 45.8µs, total_wait_time: 38.7µs, total_kv_read_wall_time: 87.5µs, "
                "tikv_wall_time: 113.6µs}, scan_detail: {total_keys: 1, get_snapshot_time: 10µs, "
                "rocksdb: {block: {cache_hit_count: 9}}}"
            ),
        },
    ]

    # Verify correct parsing with tree structure
    assert result == expected_json


def test_tidb_plan_parsing_stream_agg_with_empty_column():
    """Test parsing StreamAgg plan with cop[tikv] tasks"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # StreamAgg plan from user's example
    plan_text = (
        "\tid\ttask\testRows\toperator info\tactRows\texecution info\tmemory\tdisk\n"
        "\tStreamAgg_17\troot\t1\tfuncs:count(Column#9)->Column#7\t1\ttime:591.2µs, loops:2\t388 Bytes\tN/A\n"
        "\t└─IndexReader_18\troot\t1\tindex:StreamAgg_9\t0\ttime:586.2µs, loops:1, cop_task: "
        "{num: 1, max: 542.8µs, proc_keys: 0, tot_proc: 77.1µs, tot_wait: 32µs, copr_cache: disabled, "
        "build_task_duration: 9.09µs, max_distsql_concurrency: 1}, rpc_info:{Cop:{num_rpc:1, "
        "total_time:526.8µs}}\t280 Bytes\tN/A\n"
        "\t  └─StreamAgg_9\tcop[tikv]\t1\tfuncs:count(?)->Column#9\t0\ttikv_task:{time:0s, loops:1}, "
        "scan_detail: {total_keys: 1, get_snapshot_time: 8.69µs, rocksdb: {block: {cache_hit_count: 10}}}, "
        "time_detail: {total_process_time: 77.1µs, total_wait_time: 32µs, tikv_wall_time: 215µs}\tN/A\tN/A\n"
        "\t    └─IndexRangeScan_16\tcop[tikv]\t1.28\ttable:comments, index:idx_item_id_status(item_id, status), "
        "range:[? ?,? ?], keep order:false\t0\ttikv_task:{time:0s, loops:1}\tN/A\tN/A"
    )

    parsed = statement_samples._parse_tidb_text_plan(plan_text)
    result = json.loads(parsed)

    # Expected flat array with cop[tikv] tasks
    expected_json = [
        {
            "id": "StreamAgg_17",
            "estRows": "1",
            "taskType": "root",
            "operatorInfo": "funcs:count(Column#9)->Column#7",
            "actRows": "1",
            "executionInfo": "time:591.2µs, loops:2",
            "memory": "388 Bytes",
        },
        {
            "id": "IndexReader_18",
            "estRows": "1",
            "taskType": "root",
            "operatorInfo": "index:StreamAgg_9",
            "actRows": "0",
            "executionInfo": (
                "time:586.2µs, loops:1, cop_task: {num: 1, max: 542.8µs, proc_keys: 0, "
                "tot_proc: 77.1µs, tot_wait: 32µs, copr_cache: disabled, build_task_duration: 9.09µs, "
                "max_distsql_concurrency: 1}, rpc_info:{Cop:{num_rpc:1, total_time:526.8µs}}"
            ),
            "memory": "280 Bytes",
        },
        {
            "id": "StreamAgg_9",
            "estRows": "1",
            "taskType": "cop[tikv]",
            "operatorInfo": "funcs:count(?)->Column#9",
            "actRows": "0",
            "executionInfo": (
                "tikv_task:{time:0s, loops:1}, scan_detail: {total_keys: 1, get_snapshot_time: 8.69µs, "
                "rocksdb: {block: {cache_hit_count: 10}}}, time_detail: {total_process_time: 77.1µs, "
                "total_wait_time: 32µs, tikv_wall_time: 215µs}"
            ),
        },
        {
            "id": "IndexRangeScan_16",
            "estRows": "1.28",
            "taskType": "cop[tikv]",
            "operatorInfo": (
                "table:comments, index:idx_item_id_status(item_id, status), range:[? ?,? ?], keep order:false"
            ),
            "actRows": "0",
            "executionInfo": "tikv_task:{time:0s, loops:1}",
        },
    ]

    # Verify correct parsing
    assert result == expected_json


def test_tidb_plan_parsing_empty_plan():
    """Test parsing empty plan (row 16 from user's example)"""
    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[
            {
                'server': 'localhost',
                'user': 'datadog',
                'dbm': True,
                'statement_samples': {
                    'enabled': True,
                },
            }
        ],
    )

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Empty plan
    plan_text = ""

    parsed = statement_samples._parse_tidb_text_plan(plan_text)
    result = json.loads(parsed)

    # Expected: raw_plan wrapper for empty plan
    assert 'raw_plan' in result
    assert result['raw_plan'] == ""


@pytest.mark.unit
def test_tidb_sample_collection_strategy():
    """Test that TiDB uses the correct statement collection strategy"""
    from datadog_checks.mysql.statement_samples import MySQLStatementSamples

    mysql_check = MySql(
        common.CHECK_NAME,
        {},
        instances=[{'server': 'localhost', 'user': 'datadog', 'dbm': True, 'statement_samples': {'enabled': True}}],
    )

    # Mock TiDB detection
    mysql_check._get_is_tidb = mock.MagicMock(return_value=True)

    # Create statement samples collector
    statement_samples = MySQLStatementSamples(mysql_check, mysql_check._config, {})

    # Mock database connection
    mock_db = mock.MagicMock()
    statement_samples._db = mock_db

    # Get the collection strategy
    table, interval = statement_samples._get_sample_collection_strategy()

    # Should use TiDB cluster_statements_summary table
    assert table == "information_schema.cluster_statements_summary"
    assert interval > 0

    # Should set TiDB explain strategies
    assert statement_samples._preferred_explain_strategies == ['TIDB_STATEMENT']
