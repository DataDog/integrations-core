# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
import re
import subprocess
import time
from collections import Counter
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import closing
from os import environ

import mock
import psutil
import pymysql
import pytest
from pkg_resources import parse_version

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.serialization import json
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.mysql import MySql, statements
from datadog_checks.mysql.statement_samples import StatementTruncationState
from datadog_checks.mysql.version_utils import get_version

from . import common, tags, variables
from .common import MYSQL_VERSION_PARSED

logger = logging.getLogger(__name__)


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


statement_samples_keys = ["query_samples", "statement_samples"]


@pytest.mark.parametrize("statement_samples_key", statement_samples_keys)
@pytest.mark.parametrize("statement_samples_enabled", [True, False])
def test_statement_samples_enabled_config(dbm_instance, statement_samples_key, statement_samples_enabled):
    # test to make sure we continue to support the old key
    for k in statement_samples_keys:
        dbm_instance.pop(k, None)
    dbm_instance[statement_samples_key] = {'enabled': statement_samples_enabled}
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    assert mysql_check._statement_samples._enabled == statement_samples_enabled


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_minimal_config(aggregator, instance_basic):
    mysql_check = MySql(common.CHECK_NAME, {}, [instance_basic])
    mysql_check.check(instance_basic)

    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS_MIN, count=1)

    # Test metrics
    testable_metrics = variables.STATUS_VARS + variables.VARIABLES_VARS + variables.INNODB_VARS + variables.BINLOG_VARS

    for mname in testable_metrics:
        aggregator.assert_metric(mname, at_least=1)

    optional_metrics = (
        variables.COMPLEX_STATUS_VARS
        + variables.COMPLEX_VARIABLES_VARS
        + variables.COMPLEX_INNODB_VARS
        + variables.SYSTEM_METRICS
        + variables.SYNTHETIC_VARS
    )

    _test_optional_metrics(aggregator, optional_metrics)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_complex_config(aggregator, instance_complex):
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_complex])
    mysql_check.check(instance_complex)

    _assert_complex_config(aggregator)
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), check_submission_type=True, exclude=['alice.age', 'bob.age'] + variables.STATEMENT_VARS
    )


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance_complex):
    aggregator = dd_agent_check(instance_complex)

    _assert_complex_config(aggregator)
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), exclude=['alice.age', 'bob.age'] + variables.STATEMENT_VARS
    )


def _assert_complex_config(aggregator):
    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS, count=1)
    aggregator.assert_service_check(
        'mysql.replication.slave_running', status=MySql.OK, tags=tags.SC_TAGS + ['replication_mode:source'], at_least=1
    )
    testable_metrics = (
        variables.STATUS_VARS
        + variables.COMPLEX_STATUS_VARS
        + variables.VARIABLES_VARS
        + variables.COMPLEX_VARIABLES_VARS
        + variables.INNODB_VARS
        + variables.COMPLEX_INNODB_VARS
        + variables.BINLOG_VARS
        + variables.SYSTEM_METRICS
        + variables.SCHEMA_VARS
        + variables.SYNTHETIC_VARS
        + variables.STATEMENT_VARS
    )

    if MYSQL_VERSION_PARSED >= parse_version('5.6'):
        testable_metrics.extend(variables.PERFORMANCE_VARS)

    # Test metrics
    for mname in testable_metrics:
        # These three are currently not guaranteed outside of a Linux
        # environment.
        if mname == 'mysql.performance.user_time' and not Platform.is_linux():
            continue
        if mname == 'mysql.performance.kernel_time' and not Platform.is_linux():
            continue
        if mname == 'mysql.performance.cpu_time' and Platform.is_windows():
            continue

        if mname == 'mysql.performance.query_run_time.avg':
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:testdb'], count=1)
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:mysql'], count=1)
        elif mname == 'mysql.info.schema.size':
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:testdb'], count=1)
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:information_schema'], count=1)
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:performance_schema'], count=1)
        else:
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS, at_least=0)

    # TODO: test this if it is implemented
    # Assert service metadata
    # version_metadata = mysql_check.service_metadata['version']
    # assert len(version_metadata) == 1

    # test custom query metrics
    aggregator.assert_metric('alice.age', value=25)
    aggregator.assert_metric('bob.age', value=20)

    # test optional metrics
    optional_metrics = (
        variables.OPTIONAL_REPLICATION_METRICS
        + variables.OPTIONAL_INNODB_VARS
        + variables.OPTIONAL_STATUS_VARS
        + variables.OPTIONAL_STATUS_VARS_5_6_6
    )
    # Note, this assertion will pass even if some metrics are not present.
    # Manual testing is required for optional metrics
    _test_optional_metrics(aggregator, optional_metrics)

    # Raises when coverage < 100%
    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connection_failure(aggregator, instance_error):
    """
    Service check reports connection failure
    """
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_error])

    with pytest.raises(Exception):
        mysql_check.check(instance_error)

    aggregator.assert_service_check('mysql.can_connect', status=MySql.CRITICAL, tags=tags.SC_FAILURE_TAGS, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_complex_config_replica(aggregator, instance_complex):
    config = copy.deepcopy(instance_complex)
    config['port'] = common.SLAVE_PORT
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[config])

    mysql_check.check(config)

    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS_REPLICA, count=1)

    # Travis MySQL not running replication - FIX in flavored test.
    aggregator.assert_service_check(
        'mysql.replication.slave_running',
        status=MySql.OK,
        tags=tags.SC_TAGS_REPLICA + ['replication_mode:replica'],
        at_least=1,
    )

    testable_metrics = (
        variables.STATUS_VARS
        + variables.COMPLEX_STATUS_VARS
        + variables.VARIABLES_VARS
        + variables.COMPLEX_VARIABLES_VARS
        + variables.INNODB_VARS
        + variables.COMPLEX_INNODB_VARS
        + variables.BINLOG_VARS
        + variables.SYSTEM_METRICS
        + variables.SCHEMA_VARS
        + variables.SYNTHETIC_VARS
        + variables.STATEMENT_VARS
    )

    if MYSQL_VERSION_PARSED >= parse_version('5.6') and environ.get('MYSQL_FLAVOR') != 'mariadb':
        testable_metrics.extend(variables.PERFORMANCE_VARS)

    # Test metrics
    for mname in testable_metrics:
        # These two are currently not guaranteed outside of a Linux
        # environment.
        if mname == 'mysql.performance.user_time' and not Platform.is_linux():
            continue
        if mname == 'mysql.performance.kernel_time' and not Platform.is_linux():
            continue
        if mname == 'mysql.performance.cpu_time' and Platform.is_windows():
            continue
        if mname == 'mysql.performance.query_run_time.avg':
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:testdb'], at_least=1)
        elif mname == 'mysql.info.schema.size':
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:testdb'], count=1)
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:information_schema'], count=1)
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS + ['schema:performance_schema'], count=1)
        else:
            aggregator.assert_metric(mname, tags=tags.METRIC_TAGS, at_least=0)

    # test custom query metrics
    aggregator.assert_metric('alice.age', value=25)
    aggregator.assert_metric('bob.age', value=20)

    # test optional metrics
    optional_metrics = (
        variables.OPTIONAL_REPLICATION_METRICS
        + variables.OPTIONAL_INNODB_VARS
        + variables.OPTIONAL_STATUS_VARS
        + variables.OPTIONAL_STATUS_VARS_5_6_6
    )
    # Note, this assertion will pass even if some metrics are not present.
    # Manual testing is required for optional metrics
    _test_optional_metrics(aggregator, optional_metrics)

    # Raises when coverage < 100%
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), check_submission_type=True, exclude=['alice.age', 'bob.age'] + variables.STATEMENT_VARS
    )


def _obfuscate_sql(query, options=None):
    return re.sub(r'\s+', ' ', query or '').strip()


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
def test_statement_metrics(aggregator, dbm_instance, query, default_schema, datadog_agent, aurora_replication_role):
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])

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
        mysql_check.check(dbm_instance)

        # Run the query and check a second time so statement metrics are computed from the previous run
        run_query(query)
        mysql_check.check(dbm_instance)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert len(events) == 1
    event = events[0]

    assert event['host'] == 'stubbed.hostname'
    assert event['timestamp'] > 0
    assert event['min_collection_interval'] == 15
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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_statement_metrics_with_duplicates(aggregator, dbm_instance, datadog_agent):
    query_one = 'select * from information_schema.processlist where state in (\'starting\')'
    query_two = 'select * from information_schema.processlist where state in (\'starting\', \'Waiting on empty queue\')'
    normalized_query = 'SELECT * FROM `information_schema` . `processlist` where state in ( ? )'
    # The query signature should match the query and consistency of this tag has product impact. Do not change
    # the query signature for this test unless you know what you're doing. The query digest is determined by
    # mysql and varies across versions.
    query_signature = '94caeb4c54f97849'

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])

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
        mysql_check.check(dbm_instance)

        # Run the queries again and check a second time so statement metrics are computed from the previous run using
        # the merged stats of the two queries
        run_query(query_one)
        run_query(query_two)
        mysql_check.check(dbm_instance)

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
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
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
        mysql_check.check(dbm_instance)
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
def test_statement_samples_main_collection_rate_limit(aggregator, dbm_instance):
    # test rate limiting of the main collection loop
    collection_interval = 0.2
    dbm_instance['query_samples']['collection_interval'] = collection_interval
    dbm_instance['query_samples']['run_sync'] = False
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    mysql_check.check(dbm_instance)
    sleep_time = 1
    time.sleep(sleep_time)
    max_collections = int(1 / collection_interval * sleep_time) + 1
    mysql_check.cancel()
    metrics = aggregator.metrics("dd.mysql.collect_statement_samples.time")
    assert max_collections / 2.0 <= len(metrics) <= max_collections


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_statement_samples_unique_plans_rate_limits(aggregator, bob_conn, dbm_instance):
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
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    with closing(bob_conn.cursor()) as cursor:
        for _ in range(3):
            # repeat the same set of queries multiple times to ensure we're testing the per-query TTL rate limit
            for q in queries:
                cursor.execute(q)
                mysql_check.check(dbm_instance)

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


def _expected_dbm_instance_tags(dbm_instance):
    return dbm_instance['tags'] + ['server:{}'.format(common.HOST), 'port:{}'.format(common.PORT)]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_async_job_inactive_stop(aggregator, dbm_instance):
    # confirm that async jobs stop on their own after the check has not been run for a while
    dbm_instance['query_samples']['run_sync'] = False
    dbm_instance['query_metrics']['run_sync'] = False
    # low collection interval for a faster test
    dbm_instance['min_collection_interval'] = 1
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    mysql_check.check(dbm_instance)
    # make sure there were no unhandled exceptions
    mysql_check._statement_samples._job_loop_future.result()
    mysql_check._statement_metrics._job_loop_future.result()
    for job in ['statement-metrics', 'statement-samples']:
        aggregator.assert_metric(
            "dd.mysql.async_job.inactive_stop", tags=_expected_dbm_instance_tags(dbm_instance) + ['job:' + job]
        )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_async_job_cancel(aggregator, dbm_instance):
    dbm_instance['query_samples']['run_sync'] = False
    dbm_instance['query_metrics']['run_sync'] = False
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    mysql_check.check(dbm_instance)
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


@pytest.mark.parametrize("statement_samples_enabled", [True, False])
@pytest.mark.parametrize("statement_metrics_enabled", [True, False])
def test_async_job_enabled(dbm_instance, statement_samples_enabled, statement_metrics_enabled):
    dbm_instance['query_samples'] = {'enabled': statement_samples_enabled, 'run_sync': False}
    dbm_instance['query_metrics'] = {'enabled': statement_metrics_enabled, 'run_sync': False}
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    mysql_check.check(dbm_instance)
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
def test_statement_samples_max_per_digest(dbm_instance):
    # clear out any events from previous test runs
    dbm_instance['query_samples']['events_statements_table'] = 'events_statements_history_long'
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    for _ in range(3):
        mysql_check.check(dbm_instance)
    rows = mysql_check._statement_samples._get_new_events_statements('events_statements_history_long', 1000)
    count_by_digest = Counter(r['digest'] for r in rows)
    for _, count in count_by_digest.items():
        assert count == 1, "we should be reading exactly one row per digest out of the database"


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_statement_samples_invalid_explain_procedure(aggregator, dbm_instance):
    dbm_instance['query_samples']['explain_procedure'] = 'hello'
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    mysql_check.check(dbm_instance)
    aggregator.assert_metric_has_tag_prefix("dd.mysql.query_samples.error", "error:explain-")


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "events_statements_enable_procedure", ["datadog.enable_events_statements_consumers", "invalid_proc"]
)
def test_statement_samples_enable_consumers(dbm_instance, root_conn, events_statements_enable_procedure):
    dbm_instance['query_samples']['events_statements_enable_procedure'] = events_statements_enable_procedure
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])

    # deliberately disable one of the consumers
    with closing(root_conn.cursor()) as cursor:
        cursor.execute(
            "UPDATE performance_schema.setup_consumers SET enabled='NO'  WHERE name = "
            "'events_statements_history_long';"
        )

    original_enabled_consumers = mysql_check._statement_samples._get_enabled_performance_schema_consumers()
    assert original_enabled_consumers == {'events_statements_current', 'events_statements_history'}

    mysql_check.check(dbm_instance)

    enabled_consumers = mysql_check._statement_samples._get_enabled_performance_schema_consumers()
    if events_statements_enable_procedure == "datadog.enable_events_statements_consumers":
        assert enabled_consumers == original_enabled_consumers.union({'events_statements_history_long'})
    else:
        assert enabled_consumers == original_enabled_consumers


def _test_optional_metrics(aggregator, optional_metrics):
    """
    Check optional metrics - They can either be present or not
    """

    before = len(aggregator.not_asserted())

    for mname in optional_metrics:
        aggregator.assert_metric(mname, tags=tags.METRIC_TAGS, at_least=0)

    # Compute match rate
    after = len(aggregator.not_asserted())

    assert before > after


@pytest.mark.unit
def test__get_server_pid():
    """
    Test the logic looping through the processes searching for `mysqld`
    """
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    mysql_check._get_pid_file_variable = mock.MagicMock(return_value=None)
    mysql_check.log = mock.MagicMock()
    dummy_proc = subprocess.Popen(["python"])

    p_iter = psutil.process_iter

    def process_iter():
        """
        Wrap `psutil.process_iter` with a func killing a running process
        while iterating to reproduce a bug in the pid detection.
        We don't use psutil directly here because at the time this will be
        invoked, `psutil.process_iter` will be mocked. Instead we assign it to
        `p_iter` which is then part of the closure (see line above).
        """
        for p in p_iter():
            if dummy_proc.pid == p.pid:
                dummy_proc.terminate()
                dummy_proc.wait()
            # continue as the original `process_iter` function
            yield p

    with mock.patch('datadog_checks.mysql.mysql.psutil.process_iter', process_iter):
        with mock.patch('datadog_checks.mysql.mysql.PROC_NAME', 'this_shouldnt_exist'):
            # the pid should be none but without errors
            assert mysql_check._get_server_pid(None) is None
            assert mysql_check.log.exception.call_count == 0


@pytest.mark.unit
def test_parse_get_version():
    class MockCursor:
        version = (b'5.5.12-log',)

        def execute(self, command):
            pass

        def close(self):
            return MockCursor()

        def fetchone(self):
            return self.version

    class MockDatabase:
        def cursor(self):
            return MockCursor()

    mocked_db = MockDatabase()
    for mocked_db.version in [(b'5.5.12-log',), ('5.5.12-log',)]:
        v = get_version(mocked_db)
        assert v.version == '5.5.12'
        assert v.flavor == 'MySQL'
        assert v.build == 'log'


@pytest.mark.unit
@pytest.mark.parametrize(
    'replica_io_running, replica_sql_running, source_host, slaves_connected, check_status_repl, check_status_source',
    [
        # Replica host only
        pytest.param(('Slave_IO_Running', {}), ('Slave_SQL_Running', {}), 'source', 0, MySql.CRITICAL, None),
        pytest.param(('Replica_IO_Running', {}), ('Replica_SQL_Running', {}), 'source', 0, MySql.CRITICAL, None),
        pytest.param(('Slave_IO_Running', {'a': 'yes'}), ('Slave_SQL_Running', {}), 'source', 0, MySql.WARNING, None),
        pytest.param(
            ('Replica_IO_Running', {'a': 'yes'}), ('Replica_SQL_Running', {}), 'source', 0, MySql.WARNING, None
        ),
        pytest.param(('Slave_IO_Running', {}), ('Slave_SQL_Running', {'a': 'yes'}), 'source', 0, MySql.WARNING, None),
        pytest.param(
            ('Replica_IO_Running', {}), ('Replica_SQL_Running', {'a': 'yes'}), 'source', 0, MySql.WARNING, None
        ),
        pytest.param(
            ('Slave_IO_Running', {'a': 'yes'}), ('Slave_SQL_Running', {'a': 'yes'}), 'source', 0, MySql.OK, None
        ),
        pytest.param(
            ('Replica_IO_Running', {'a': 'yes'}),
            ('Replica_SQL_Running', {'a': 'yes'}),
            'source',
            0,
            MySql.OK,
            None,
        ),
        # Source host only
        pytest.param(('Replica_IO_Running', None), ('Replica_SQL_Running', None), None, 1, None, MySql.OK),
        pytest.param(('Replica_IO_Running', None), ('Replica_SQL_Running', None), None, 0, None, MySql.WARNING),
        # Source and replica host
        pytest.param(('Replica_IO_Running', {}), ('Replica_SQL_Running', {}), 'source', 1, MySql.CRITICAL, MySql.OK),
        pytest.param(
            ('Replica_IO_Running', {'a': 'yes'}), ('Replica_SQL_Running', {}), 'source', 1, MySql.WARNING, MySql.OK
        ),
        pytest.param(
            ('Slave_IO_Running', {'a': 'yes'}),
            ('Slave_SQL_Running', {'a': 'yes'}),
            'source',
            1,
            MySql.OK,
            MySql.OK,
        ),
    ],
)
def test_replication_check_status(
    replica_io_running,
    replica_sql_running,
    source_host,
    slaves_connected,
    check_status_repl,
    check_status_source,
    instance_basic,
    aggregator,
):
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_basic])
    mysql_check.service_check_tags = ['foo:bar']
    mocked_results = {
        'Slaves_connected': slaves_connected,
        'Binlog_enabled': True,
    }
    if replica_io_running[1] is not None:
        mocked_results[replica_io_running[0]] = replica_io_running[1]
    if replica_sql_running[1] is not None:
        mocked_results[replica_sql_running[0]] = replica_sql_running[1]
    if source_host:
        mocked_results['Master_Host'] = source_host

    mysql_check._check_replication_status(mocked_results)
    expected_service_check_len = 0

    if check_status_repl is not None:
        aggregator.assert_service_check(
            'mysql.replication.slave_running', check_status_repl, tags=['foo:bar', 'replication_mode:replica'], count=1
        )
        aggregator.assert_service_check(
            'mysql.replication.replica_running',
            check_status_repl,
            tags=['foo:bar', 'replication_mode:replica'],
            count=1,
        )
        expected_service_check_len += 1

    if check_status_source is not None:
        aggregator.assert_service_check(
            'mysql.replication.slave_running', check_status_source, tags=['foo:bar', 'replication_mode:source'], count=1
        )
        aggregator.assert_service_check(
            'mysql.replication.replica_running',
            check_status_source,
            tags=['foo:bar', 'replication_mode:source'],
            count=1,
        )
        expected_service_check_len += 1

    assert len(aggregator.service_checks('mysql.replication.slave_running')) == expected_service_check_len


def test__get_is_aurora():
    def new_check():
        return MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])

    class MockCursor:
        def __init__(self, rows, side_effect=None):
            self.rows = rows
            self.side_effect = side_effect

        def __call__(self, *args, **kwargs):
            return self

        def execute(self, command):
            if self.side_effect:
                raise self.side_effect

        def close(self):
            return MockCursor([])

        def fetchall(self):
            return self.rows

    class MockDatabase:
        def __init__(self, cursor):
            self.cursor = cursor

        def cursor(self):
            return self.cursor

    check = new_check()
    assert True is check._get_is_aurora(MockDatabase(MockCursor(rows=[('1.72.1',)])))
    assert True is check._get_is_aurora(None)
    assert True is check._is_aurora

    check = new_check()
    assert True is check._get_is_aurora(
        MockDatabase(
            MockCursor(
                rows=[
                    ('1.72.1',),
                    ('1.72.1',),
                ]
            )
        )
    )
    assert True is check._get_is_aurora(None)
    assert True is check._is_aurora

    check = new_check()
    assert False is check._get_is_aurora(MockDatabase(MockCursor(rows=[])))
    assert False is check._get_is_aurora(None)
    assert False is check._is_aurora

    check = new_check()
    assert False is check._get_is_aurora(MockDatabase(MockCursor(rows=None, side_effect=ValueError())))
    assert None is check._is_aurora
    assert False is check._get_is_aurora(None)


@pytest.mark.unit
def test__get_runtime_aurora_tags():
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])

    class MockCursor:
        def __init__(self, rows, side_effect=None):
            self.rows = rows
            self.side_effect = side_effect

        def __call__(self, *args, **kwargs):
            return self

        def execute(self, command):
            if self.side_effect:
                raise self.side_effect

        def close(self):
            return MockCursor(None)

        def fetchone(self):
            return self.rows.pop(0)

    class MockDatabase:
        def __init__(self, cursor):
            self.cursor = cursor

        def cursor(self):
            return self.cursor

    reader_row = ('reader',)
    writer_row = ('writer',)

    tags = mysql_check._get_runtime_aurora_tags(MockDatabase(MockCursor(rows=[reader_row])))
    assert tags == ['replication_role:reader']

    tags = mysql_check._get_runtime_aurora_tags(MockDatabase(MockCursor(rows=[writer_row])))
    assert tags == ['replication_role:writer']

    tags = mysql_check._get_runtime_aurora_tags(MockDatabase(MockCursor(rows=[(1, 'reader')])))
    assert tags == []

    # Error cases for non-aurora databases; any error should be caught and not fail the check

    tags = mysql_check._get_runtime_aurora_tags(
        MockDatabase(
            MockCursor(
                rows=[], side_effect=pymysql.err.InternalError(pymysql.constants.ER.UNKNOWN_TABLE, 'Unknown Table')
            )
        )
    )
    assert tags == []

    tags = mysql_check._get_runtime_aurora_tags(
        MockDatabase(
            MockCursor(
                rows=[],
                side_effect=pymysql.err.ProgrammingError(pymysql.constants.ER.DBACCESS_DENIED_ERROR, 'Access Denied'),
            )
        )
    )
    assert tags == []


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_version_metadata(instance_basic, datadog_agent, version_metadata):
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_basic])
    mysql_check.check_id = 'test:123'

    mysql_check.check(instance_basic)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, instance_custom_queries, dd_run_check):
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[instance_custom_queries])
    dd_run_check(mysql_check)

    aggregator.assert_metric('alice.age', value=25, tags=tags.METRIC_TAGS)
    aggregator.assert_metric('bob.age', value=20, tags=tags.METRIC_TAGS)
