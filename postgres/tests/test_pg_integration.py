# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket
import time

import mock
import psycopg2
import pytest
from semver import VersionInfo

from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.util import PartialFormatter, fmt

from .common import (
    COMMON_METRICS,
    DB_NAME,
    DBM_MIGRATED_METRICS,
    HOST,
    PASSWORD,
    PORT,
    POSTGRES_VERSION,
    USER,
    assert_metric_at_least,
    check_activity_metrics,
    check_bgw_metrics,
    check_common_metrics,
    check_connection_metrics,
    check_db_count,
    check_replication_slots,
    check_slru_metrics,
    check_stat_replication,
    check_wal_receiver_metrics,
    requires_static_version,
)
from .utils import requires_over_10, requires_over_14

CONNECTION_METRICS = ['postgresql.max_connections', 'postgresql.percent_usage_connections']

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_common_metrics(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['port:{}'.format(PORT)]
    check_common_metrics(aggregator, expected_tags=expected_tags)
    check_bgw_metrics(aggregator, expected_tags)
    check_connection_metrics(aggregator, expected_tags=expected_tags)
    check_db_count(aggregator, expected_tags=expected_tags)
    check_slru_metrics(aggregator, expected_tags=expected_tags)
    check_stat_replication(aggregator, expected_tags=expected_tags)
    check_wal_receiver_metrics(aggregator, expected_tags=expected_tags, connected=0)

    replication_slot_tags = expected_tags + [
        'slot_name:replication_slot',
        'slot_persistence:permanent',
        'slot_state:active',
        'slot_type:physical',
    ]
    check_replication_slots(aggregator, expected_tags=replication_slot_tags)

    logical_replication_slot_tags = expected_tags + [
        'slot_name:logical_slot',
        'slot_persistence:permanent',
        'slot_state:inactive',
        'slot_type:logical',
    ]
    check_replication_slots(aggregator, expected_tags=logical_replication_slot_tags)

    aggregator.assert_all_metrics_covered()


def test_common_metrics_without_size(aggregator, integration_check, pg_instance):
    pg_instance['collect_database_size_metrics'] = False
    check = integration_check(pg_instance)
    check.check(pg_instance)
    assert 'postgresql.database_size' not in aggregator.metric_names


def _get_conn(user=USER, db=DB_NAME, application_name='test'):
    passwords = {'postgres': 'datad0g', USER: PASSWORD}
    conn = psycopg2.connect(
        host=HOST, dbname=db, user=user, password=passwords[user], application_name=application_name
    )
    return conn


@requires_over_14
def test_session_number(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    check.check(pg_instance)
    expected_tags = pg_instance['tags'] + ['db:postgres', 'port:{}'.format(PORT)]
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("select sessions from pg_stat_database where datname='postgres'")
        session_number = cur.fetchall()[0][0]
    aggregator.assert_metric('postgresql.sessions.count', value=session_number, count=1, tags=expected_tags)

    # Generate a new session in postgres database
    conn = _get_conn('postgres', 'postgres')
    conn.close()

    # Leave time for stats to be flushed in the stats collector
    time.sleep(0.5)

    aggregator.reset()
    check.check(pg_instance)

    aggregator.assert_metric('postgresql.sessions.count', value=session_number + 1, count=1, tags=expected_tags)


@requires_over_14
def test_session_idle_and_killed(aggregator, integration_check, pg_instance):
    # Reset idle time to 0
    postgres_conn = _get_conn('postgres')
    with postgres_conn.cursor() as cur:
        cur.execute("select pg_stat_reset();")
        cur.fetchall()
    # Make sure the stats collector is updated
    time.sleep(0.5)

    check = integration_check(pg_instance)
    check.check(pg_instance)
    expected_tags = pg_instance['tags'] + ['db:{}'.format(DB_NAME), 'port:{}'.format(PORT)]

    aggregator.assert_metric('postgresql.sessions.idle_in_transaction_time', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.sessions.killed', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.sessions.fatal', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.sessions.abandoned', value=0, count=1, tags=expected_tags)

    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute('BEGIN;')
        cur.execute('select txid_current();')
        cur.fetchall()
        # Keep transaction idle for 500ms
        time.sleep(0.5)
        cur.execute('select pg_backend_pid();')
        pid = cur.fetchall()[0][0]

    # Kill session
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT pg_terminate_backend({})".format(pid))
        cur.fetchall()

    # Abandon session
    sock = socket.fromfd(postgres_conn.fileno(), socket.AF_INET, socket.SOCK_STREAM)
    sock.shutdown(socket.SHUT_RDWR)

    aggregator.reset()
    check.check(pg_instance)

    assert_metric_at_least(
        aggregator, 'postgresql.sessions.idle_in_transaction_time', count=1, lower_bound=0.5, tags=expected_tags
    )
    aggregator.assert_metric('postgresql.sessions.killed', value=1, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.sessions.fatal', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.sessions.abandoned', value=1, count=1, tags=expected_tags)


def test_unsupported_replication(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    unpatched_fmt = PartialFormatter()

    called = []

    def format_with_error(value, **kwargs):
        if 'pg_is_in_recovery' in value:
            called.append(True)
            raise psycopg2.errors.FeatureNotSupported("Not available")
        return unpatched_fmt.format(value, **kwargs)

    # This simulate an error in the fmt function, as it's a bit hard to mock psycopg
    with mock.patch.object(fmt, 'format', passthrough=True) as mock_fmt:
        mock_fmt.side_effect = format_with_error
        check.check(pg_instance)

    # Verify our mocking was called
    assert called == [True]

    expected_tags = pg_instance['tags'] + ['port:{}'.format(PORT)]
    check_bgw_metrics(aggregator, expected_tags)

    check_common_metrics(aggregator, expected_tags=expected_tags)


def test_can_connect_service_check(aggregator, integration_check, pg_instance):
    # First: check run with a valid postgres instance
    check = integration_check(pg_instance)
    expected_tags = pg_instance['tags'] + [
        'port:{}'.format(PORT),
        'db:{}'.format(DB_NAME),
    ]
    check.check(pg_instance)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.OK, tags=expected_tags)
    aggregator.reset()

    # Second: keep the connection open but an unexpected error happens during check run
    orig_db = check.db
    check.db = mock.MagicMock(spec=('closed', 'status'), closed=False, status=psycopg2.extensions.STATUS_READY)
    with pytest.raises(AttributeError):
        check.check(pg_instance)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.CRITICAL, tags=expected_tags)
    aggregator.reset()

    # Third: connection still open but this time no error
    check.db = orig_db
    check.check(pg_instance)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.OK, tags=expected_tags)


def test_schema_metrics(aggregator, integration_check, pg_instance):
    pg_instance['table_count_limit'] = 1
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + [
        'db:{}'.format(DB_NAME),
        'port:{}'.format(PORT),
        'schema:public',
    ]
    aggregator.assert_metric('postgresql.table.count', value=1, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.db.count', value=106, count=1)


def test_connections_metrics(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['port:{}'.format(PORT)]
    for name in CONNECTION_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)
    expected_tags += ['db:datadog_test']
    aggregator.assert_metric('postgresql.connections', count=1, tags=expected_tags)


def test_locks_metrics_no_relations(aggregator, integration_check, pg_instance):
    """
    Since 4.0.0, to prevent tag explosion, lock metrics are not collected anymore unless relations are specified
    """
    check = integration_check(pg_instance)
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        with conn.cursor() as cur:
            cur.execute('LOCK persons')
            check.check(pg_instance)

    aggregator.assert_metric('postgresql.locks', count=0)


def test_activity_metrics(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + [
        'port:{}'.format(PORT),
        'db:datadog_test',
        'app:datadog-agent',
        'user:datadog',
    ]
    check_activity_metrics(aggregator, expected_tags)


def test_activity_metrics_no_application_aggregation(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    pg_instance['activity_metrics_excluded_aggregations'] = ['application_name']
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['port:{}'.format(PORT), 'db:datadog_test', 'user:datadog']
    check_activity_metrics(aggregator, expected_tags)


def test_activity_metrics_no_aggregations(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    pg_instance['activity_metrics_excluded_aggregations'] = ['datname', 'application_name', 'usename']
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = pg_instance['tags'] + ['port:{}'.format(PORT)]
    check_activity_metrics(aggregator, expected_tags)


def test_backend_transaction_age(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    check = integration_check(pg_instance)

    check.check(pg_instance)

    dd_agent_tags = pg_instance['tags'] + [
        'port:{}'.format(PORT),
        'db:datadog_test',
        'app:datadog-agent',
        'user:datadog',
    ]
    test_tags = pg_instance['tags'] + ['port:{}'.format(PORT), 'db:datadog_test', 'app:test', 'user:datadog']
    # No transaction in progress, we have 0
    if float(POSTGRES_VERSION) >= 9.6:
        aggregator.assert_metric('postgresql.activity.backend_xmin_age', value=0, count=1, tags=dd_agent_tags)
    else:
        aggregator.assert_metric('postgresql.activity.backend_xmin_age', count=0, tags=dd_agent_tags)
    aggregator.assert_metric('postgresql.activity.xact_start_age', count=1, tags=dd_agent_tags)

    conn1 = _get_conn()
    cur = conn1.cursor()

    conn2 = _get_conn()
    cur2 = conn2.cursor()

    # Start a transaction in repeatable read to force pinning of backend_xmin
    cur.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;')
    # Force assignement of a txid and keep the transaction opened
    cur.execute('select txid_current();')
    # Make sure to fetch the result to make sure we start the timer after the transaction started
    cur.fetchall()
    start_transaction_time = time.time()

    aggregator.reset()
    check.check(pg_instance)

    if float(POSTGRES_VERSION) >= 9.6:
        aggregator.assert_metric('postgresql.activity.backend_xid_age', value=1, count=1, tags=test_tags)
        aggregator.assert_metric('postgresql.activity.backend_xmin_age', value=1, count=1, tags=test_tags)

        aggregator.assert_metric('postgresql.activity.backend_xid_age', count=0, tags=dd_agent_tags)
        aggregator.assert_metric('postgresql.activity.backend_xmin_age', value=1, count=1, tags=dd_agent_tags)
    else:
        aggregator.assert_metric('postgresql.activity.backend_xid_age', count=0, tags=test_tags)
        aggregator.assert_metric('postgresql.activity.backend_xmin_age', count=0, tags=test_tags)

        aggregator.assert_metric('postgresql.activity.backend_xid_age', count=0, tags=dd_agent_tags)
        aggregator.assert_metric('postgresql.activity.backend_xmin_age', count=0, tags=dd_agent_tags)

    aggregator.assert_metric('postgresql.activity.xact_start_age', count=1, tags=test_tags)

    # Open a new session and assign a new txid to it.
    cur2.execute('select txid_current()')

    aggregator.reset()
    transaction_age_lower_bound = time.time() - start_transaction_time
    check.check(pg_instance)

    if float(POSTGRES_VERSION) >= 9.6:
        # Check that the xmin and xid is 2 tx old
        aggregator.assert_metric('postgresql.activity.backend_xid_age', value=2, count=1, tags=test_tags)
        aggregator.assert_metric('postgresql.activity.backend_xmin_age', value=2, count=1, tags=test_tags)

        aggregator.assert_metric('postgresql.activity.backend_xid_age', count=0, tags=dd_agent_tags)
        aggregator.assert_metric('postgresql.activity.backend_xmin_age', value=2, count=1, tags=dd_agent_tags)

    # Check that xact_start_age has a value greater than the trasaction_age lower bound
    aggregator.assert_metric('postgresql.activity.xact_start_age', count=1, tags=test_tags)
    assert_metric_at_least(
        aggregator,
        'postgresql.activity.xact_start_age',
        tags=test_tags,
        count=1,
        lower_bound=transaction_age_lower_bound,
    )


@requires_over_10
def test_wrong_version(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    # Enforce to cache wrong version
    check._version = VersionInfo(*[9, 6, 0])

    check.check(pg_instance)
    assert_state_clean(check)

    check.check(pg_instance)
    assert_state_set(check)


@requires_static_version
def test_version_metadata(integration_check, pg_instance, datadog_agent):
    check = integration_check(pg_instance)
    check.check_id = 'test:123'
    # Enforce to cache wrong version
    check.check(pg_instance)
    version = POSTGRES_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': version[0],
        'resolved_hostname': 'stubbed.hostname',
    }
    if len(version) == 2:
        version_metadata['version.minor'] = version[1]

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(6)  # for raw and patch


def test_state_clears_on_connection_error(integration_check, pg_instance):
    check = integration_check(pg_instance)
    check.check(pg_instance)
    assert_state_set(check)

    def throw_exception_first_time(*args, **kwargs):
        throw_exception_first_time.counter += 1
        if throw_exception_first_time.counter > 1:
            pass  # avoid throwing exception again
        else:
            raise socket.error

    throw_exception_first_time.counter = 0

    with mock.patch('datadog_checks.postgres.PostgreSql._collect_stats', side_effect=throw_exception_first_time):
        with pytest.raises(socket.error):
            check.check(pg_instance)
    assert_state_clean(check)


def test_query_timeout(aggregator, integration_check, pg_instance):
    pg_instance['query_timeout'] = 1000
    check = integration_check(pg_instance)
    check._connect()
    cursor = check.db.cursor()
    with pytest.raises(psycopg2.errors.QueryCanceled):
        cursor.execute("select pg_sleep(2000)")


def test_config_tags_is_unchanged_between_checks(integration_check, pg_instance):
    pg_instance['tag_replication_role'] = True
    check = integration_check(pg_instance)

    expected_tags = pg_instance['tags'] + ['port:{}'.format(PORT), 'db:datadog_test']

    for _ in range(3):
        check.check(pg_instance)
        assert check._config.tags == expected_tags


@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
@pytest.mark.parametrize(
    'dbm_enabled, reported_hostname, expected_hostname',
    [
        (True, '', 'resolved.hostname'),
        (False, '', 'stubbed.hostname'),
        (False, 'forced_hostname', 'forced_hostname'),
        (True, 'forced_hostname', 'forced_hostname'),
    ],
)
def test_correct_hostname(dbm_enabled, reported_hostname, expected_hostname, aggregator, pg_instance):
    pg_instance['dbm'] = dbm_enabled
    pg_instance['collect_activity_metrics'] = True
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}

    pg_instance['disable_generic_tags'] = False  # This flag also affects the hostname
    pg_instance['reported_hostname'] = reported_hostname
    check = PostgreSql('test_instance', {}, [pg_instance])

    with mock.patch(
        'datadog_checks.postgres.PostgreSql.resolve_db_host', return_value='resolved.hostname'
    ) as resolve_db_host:
        check.check(pg_instance)
        if reported_hostname:
            assert resolve_db_host.called is False, 'Expected resolve_db_host.called to be False'
        else:
            assert resolve_db_host.called == dbm_enabled, 'Expected resolve_db_host.called to be ' + str(dbm_enabled)

    expected_tags_no_db = pg_instance['tags'] + ['server:{}'.format(HOST), 'port:{}'.format(PORT)]
    expected_tags_with_db = expected_tags_no_db + ['db:datadog_test']
    expected_activity_tags = expected_tags_with_db + ['app:datadog-agent', 'user:datadog']
    c_metrics = COMMON_METRICS
    if not dbm_enabled:
        c_metrics = c_metrics + DBM_MIGRATED_METRICS
    for name in c_metrics:
        aggregator.assert_metric(name, count=1, tags=expected_tags_with_db, hostname=expected_hostname)
    check_activity_metrics(aggregator, tags=expected_activity_tags, hostname=expected_hostname)

    for name in CONNECTION_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags_no_db, hostname=expected_hostname)

    aggregator.assert_service_check(
        'postgres.can_connect',
        count=1,
        status=PostgreSql.OK,
        tags=expected_tags_with_db,
        hostname=expected_hostname,
    )


def assert_state_clean(check):
    assert check.metrics_cache.instance_metrics is None
    assert check.metrics_cache.bgw_metrics is None
    assert check.metrics_cache.archiver_metrics is None
    assert check.metrics_cache.replication_metrics is None
    assert check.metrics_cache.activity_metrics is None
    assert check._is_aurora is None


def assert_state_set(check):
    assert check.metrics_cache.instance_metrics
    assert check.metrics_cache.bgw_metrics
    if POSTGRES_VERSION != '9.3':
        assert check.metrics_cache.archiver_metrics
    assert check.metrics_cache.replication_metrics
    assert check._is_aurora is False
