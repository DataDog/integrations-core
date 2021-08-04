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
from pkg_resources import parse_version

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.serialization import json
from datadog_checks.mysql import MySql, statements
from datadog_checks.mysql.statement_samples import StatementTruncationState

from . import common, tags
from .common import MYSQL_VERSION_PARSED

logger = logging.getLogger(__name__)

statement_samples_keys = ["query_samples", "statement_samples"]


@pytest.fixture
def dbm_instance(instance_complex):
    instance_complex['dbm'] = True
    # set the default for tests to run sychronously to ensure we don't have orphaned threads running around
    instance_complex['query_samples'] = {'enabled': True, 'run_sync': True, 'collection_interval': 1}
    # set a very small collection interval so the tests go fast
    instance_complex['query_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
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
    assert event['timestamp'] > 0
    assert event['min_collection_interval'] == dbm_instance['query_metrics']['collection_interval']
    expected_tags = set(tags.METRIC_TAGS + ['server:{}'.format(common.HOST), 'port:{}'.format(common.PORT)])
    if aurora_replication_role:
        expected_tags.add("replication_role:" + aurora_replication_role)
    assert set(event['tags']) == expected_tags
    query_signature = compute_sql_signature(query)
    matching_rows = [r for r in event['mysql_rows'] if r['query_signature'] == query_signature]
    assert len(matching_rows) == 1
    row = matching_rows[0]

    assert row['digest']
    assert row['schema_name'] == default_schema
    assert row['digest_text'].strip() == query.strip()[0:200]

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


def _obfuscate_sql(query, options=None):
    return re.sub(r'\s+', ' ', query or '').strip()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
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
    "events_statements_table",
    ["events_statements_history_long"],
)
@pytest.mark.parametrize("explain_strategy", ['PROCEDURE', 'FQ_PROCEDURE', 'STATEMENT', None])
@pytest.mark.parametrize(
    "schema,statement,expected_collection_errors,expected_statement_truncated",
    [
        (
            None,
            'select name as nam from testdb.users',
            [{'strategy': 'PROCEDURE', 'code': 'procedure_strategy_requires_default_schema', 'message': None}],
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
def test_statement_samples_collect(
    aggregator,
    dd_run_check,
    dbm_instance,
    bob_conn,
    events_statements_table,
    explain_strategy,
    schema,
    statement,
    expected_collection_errors,
    expected_statement_truncated,
    aurora_replication_role,
    caplog,
):
    caplog.set_level(logging.INFO, logger="datadog_checks.mysql.collection_utils")
    caplog.set_level(logging.DEBUG, logger="datadog_checks")
    caplog.set_level(logging.DEBUG, logger="tests.test_mysql")

    # try to collect a sample from all supported events_statements tables using all possible strategies
    dbm_instance['query_samples']['events_statements_table'] = events_statements_table
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    if explain_strategy:
        mysql_check._statement_samples._preferred_explain_strategies = [explain_strategy]

    expected_tags = set(tags.METRIC_TAGS + ['server:{}'.format(common.HOST), 'port:{}'.format(common.PORT)])
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

    # we avoid closing these in a try/finally block in order to maintain the connections in case we want to
    # debug the test with --pdb
    mysql_check._statement_samples._close_db_conn()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
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
def test_statement_samples_unique_plans_rate_limits(aggregator, dd_run_check, bob_conn, dbm_instance):
    # test unique sample ingestion rate limiting
    cache_max_size = 20
    dbm_instance['query_samples']['run_sync'] = True
    # fix the table to 'events_statements_current' to ensure we don't pull in historical queries from other tests
    dbm_instance['query_samples']['events_statements_table'] = 'events_statements_current'
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
            "dd.mysql.async_job.inactive_stop", tags=_expected_dbm_instance_tags(dbm_instance) + ['job:' + job]
        )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
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
            "dd.mysql.async_job.cancel", tags=_expected_dbm_instance_tags(dbm_instance) + ['job:' + job]
        )


def _expected_dbm_instance_tags(dbm_instance):
    return dbm_instance['tags'] + ['server:{}'.format(common.HOST), 'port:{}'.format(common.PORT)]


@pytest.mark.parametrize("statement_samples_enabled", [True, False])
@pytest.mark.parametrize("statement_metrics_enabled", [True, False])
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
def test_statement_samples_max_per_digest(dd_run_check, dbm_instance):
    # clear out any events from previous test runs
    dbm_instance['query_samples']['events_statements_table'] = 'events_statements_history_long'
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    for _ in range(3):
        dd_run_check(mysql_check)
    rows = mysql_check._statement_samples._get_new_events_statements('events_statements_history_long', 1000)
    count_by_digest = Counter(r['digest'] for r in rows)
    for _, count in count_by_digest.items():
        assert count == 1, "we should be reading exactly one row per digest out of the database"


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_statement_samples_invalid_explain_procedure(aggregator, dd_run_check, dbm_instance):
    dbm_instance['query_samples']['explain_procedure'] = 'hello'
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    dd_run_check(mysql_check)
    aggregator.assert_metric_has_tag_prefix("dd.mysql.query_samples.error", "error:explain-")


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "events_statements_enable_procedure", ["datadog.enable_events_statements_consumers", "invalid_proc"]
)
def test_statement_samples_enable_consumers(dd_run_check, dbm_instance, root_conn, events_statements_enable_procedure):
    dbm_instance['query_samples']['events_statements_enable_procedure'] = events_statements_enable_procedure
    mysql_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    # deliberately disable one of the consumers
    with closing(root_conn.cursor()) as cursor:
        cursor.execute(
            "UPDATE performance_schema.setup_consumers SET enabled='NO'  WHERE name = "
            "'events_statements_history_long';"
        )

    original_enabled_consumers = mysql_check._statement_samples._get_enabled_performance_schema_consumers()
    assert original_enabled_consumers == {'events_statements_current', 'events_statements_history'}

    dd_run_check(mysql_check)

    enabled_consumers = mysql_check._statement_samples._get_enabled_performance_schema_consumers()
    if events_statements_enable_procedure == "datadog.enable_events_statements_consumers":
        assert enabled_consumers == original_enabled_consumers.union({'events_statements_history_long'})
    else:
        assert enabled_consumers == original_enabled_consumers
