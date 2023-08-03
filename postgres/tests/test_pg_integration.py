# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket
import time

import mock
import psycopg
import pytest
from semver import VersionInfo

from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.util import PartialFormatter, fmt

from .common import (
    COMMON_METRICS,
    DB_NAME,
    DBM_MIGRATED_METRICS,
    HOST,
    POSTGRES_VERSION,
    _get_expected_tags,
    assert_metric_at_least,
    check_activity_metrics,
    check_bgw_metrics,
    check_common_metrics,
    check_conflict_metrics,
    check_connection_metrics,
    check_control_metrics,
    check_db_count,
    check_file_wal_metrics,
    check_logical_replication_slots,
    check_physical_replication_slots,
    check_slru_metrics,
    check_snapshot_txid_metrics,
    check_stat_replication,
    check_stat_wal_metrics,
    check_uptime_metrics,
    check_wal_receiver_metrics,
    requires_static_version,
)
from .utils import _get_conn, _get_superconn, requires_over_10, requires_over_14

CONNECTION_METRICS = ['postgresql.max_connections', 'postgresql.percent_usage_connections']

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.mark.parametrize(
    'is_aurora',
    [True, False],
)
def test_common_metrics(aggregator, integration_check, pg_instance, is_aurora):
    check = integration_check(pg_instance)
    check._is_aurora = is_aurora
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance)
    check_common_metrics(aggregator, expected_tags=expected_tags)
    check_control_metrics(aggregator, expected_tags=expected_tags)
    check_bgw_metrics(aggregator, expected_tags)
    check_connection_metrics(aggregator, expected_tags=expected_tags)
    check_conflict_metrics(aggregator, expected_tags=expected_tags)
    check_db_count(aggregator, expected_tags=expected_tags)
    check_slru_metrics(aggregator, expected_tags=expected_tags)
    check_stat_replication(aggregator, expected_tags=expected_tags)
    if is_aurora is False:
        check_wal_receiver_metrics(aggregator, expected_tags=expected_tags, connected=0)
    check_uptime_metrics(aggregator, expected_tags=expected_tags)

    check_logical_replication_slots(aggregator, expected_tags)
    check_physical_replication_slots(aggregator, expected_tags)
    check_snapshot_txid_metrics(aggregator, expected_tags=expected_tags)
    check_stat_wal_metrics(aggregator, expected_tags=expected_tags)
    check_file_wal_metrics(aggregator, expected_tags=expected_tags)

    aggregator.assert_all_metrics_covered()


def test_snapshot_xmin(aggregator, integration_check, pg_instance):
    with psycopg.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        with conn.cursor() as cur:
            cur.execute('select txid_snapshot_xmin(txid_current_snapshot());')
            xmin = float(cur.fetchall()[0][0])
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance)
    aggregator.assert_metric('postgresql.snapshot.xmin', value=xmin, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.snapshot.xmax', value=xmin, count=1, tags=expected_tags)

    with psycopg.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g", autocommit=True) as conn:
        with conn.cursor() as cur:
            # Force increases of txid
            cur.execute('select txid_current();')
            cur.execute('select txid_current();')

    check = integration_check(pg_instance)
    check.check(pg_instance)
    aggregator.assert_metric('postgresql.snapshot.xmin', value=xmin + 2, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.snapshot.xmax', value=xmin + 2, count=1, tags=expected_tags)


def test_snapshot_xip(aggregator, integration_check, pg_instance):
    conn1 = _get_conn(pg_instance)
    cur = conn1.cursor()

    # Start a transaction
    cur.execute('BEGIN;')
    # Force assignement of a txid and keep the transaction opened
    cur.execute('select txid_current();')
    # Make sure to fetch the result to make sure we start the timer after the transaction started
    cur.fetchall()

    conn2 = _get_conn(pg_instance)
    with conn2.cursor() as cur2:
        # Force increases of txid
        cur2.execute('select txid_current();')

    check = integration_check(pg_instance)
    check.check(pg_instance)
    expected_tags = _get_expected_tags(check, pg_instance)
    aggregator.assert_metric('postgresql.snapshot.xip_count', value=1, count=1, tags=expected_tags)


def test_common_metrics_without_size(aggregator, integration_check, pg_instance):
    pg_instance['collect_database_size_metrics'] = False
    check = integration_check(pg_instance)
    check.check(pg_instance)
    assert 'postgresql.database_size' not in aggregator.metric_names


def test_uptime(aggregator, integration_check, pg_instance):
    conn = _get_conn(pg_instance)
    with conn.cursor() as cur:
        cur.execute("SELECT FLOOR(EXTRACT(EPOCH FROM current_timestamp - pg_postmaster_start_time()))")
        uptime = cur.fetchall()[0][0]
    check = integration_check(pg_instance)
    check.check(pg_instance)
    expected_tags = _get_expected_tags(check, pg_instance)
    assert_metric_at_least(
        aggregator, 'postgresql.uptime', count=1, lower_bound=uptime, higher_bound=uptime + 1, tags=expected_tags
    )


@requires_over_14
def test_session_number(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    check.check(pg_instance)
    expected_tags = _get_expected_tags(check, pg_instance, db='postgres')
    conn = _get_conn(pg_instance)
    with conn.cursor() as cur:
        cur.execute("select sessions from pg_stat_database where datname='postgres'")
        session_number = cur.fetchall()[0][0]
    aggregator.assert_metric('postgresql.sessions.count', value=session_number, count=1, tags=expected_tags)

    # Generate a new session in postgres database
    conn = _get_conn(pg_instance, dbname='postgres')
    conn.close()

    # Leave time for stats to be flushed in the stats collector
    time.sleep(0.5)

    aggregator.reset()
    check.check(pg_instance)

    aggregator.assert_metric('postgresql.sessions.count', value=session_number + 1, count=1, tags=expected_tags)


@requires_over_14
def test_session_idle_and_killed(aggregator, integration_check, pg_instance):
    # Reset idle time to 0
    postgres_conn = _get_superconn(pg_instance)
    with postgres_conn.cursor() as cur:
        cur.execute("select pg_stat_reset();")
        cur.fetchall()
    # Make sure the stats collector is updated
    time.sleep(0.5)

    check = integration_check(pg_instance)
    check.check(pg_instance)
    expected_tags = _get_expected_tags(check, pg_instance, db=DB_NAME)

    aggregator.assert_metric('postgresql.sessions.idle_in_transaction_time', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.sessions.killed', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.sessions.fatal', value=0, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.sessions.abandoned', value=0, count=1, tags=expected_tags)

    conn = _get_conn(pg_instance)
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
            raise psycopg.errors.FeatureNotSupported("Not available")
        return unpatched_fmt.format(value, **kwargs)

    # This simulate an error in the fmt function, as it's a bit hard to mock psycopg
    with mock.patch.object(fmt, 'format', passthrough=True) as mock_fmt:
        mock_fmt.side_effect = format_with_error
        check.check(pg_instance)

    # Verify our mocking was called
    assert called == [True]

    expected_tags = _get_expected_tags(check, pg_instance)
    check_bgw_metrics(aggregator, expected_tags)

    check_common_metrics(aggregator, expected_tags=expected_tags)


def test_can_connect_service_check(aggregator, integration_check, pg_instance):
    # First: check run with a valid postgres instance
    check = integration_check(pg_instance)

    check.check(pg_instance)
    expected_tags = _get_expected_tags(check, pg_instance, db=DB_NAME)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.OK, tags=expected_tags)
    aggregator.reset()

    # Second: keep the connection open but an unexpected error happens during check run
    orig_db = check.db
    check.db = mock.MagicMock(spec=('closed', 'status'), closed=False, status=psycopg.pq.ConnStatus.OK)
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

    expected_tags = _get_expected_tags(check, pg_instance, db=DB_NAME, schema='public')
    aggregator.assert_metric('postgresql.table.count', value=1, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.db.count', value=106, count=1)


def test_connections_metrics(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance)
    for name in CONNECTION_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)
    expected_tags += ['db:datadog_test']
    aggregator.assert_metric('postgresql.connections', count=1, tags=expected_tags)


def test_locks_metrics_no_relations(aggregator, integration_check, pg_instance):
    """
    Since 4.0.0, to prevent tag explosion, lock metrics are not collected anymore unless relations are specified
    """
    check = integration_check(pg_instance)
    with psycopg.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        with conn.cursor() as cur:
            cur.execute('LOCK persons')
            check.check(pg_instance)

    aggregator.assert_metric('postgresql.locks', count=0)


def test_activity_metrics(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance, db=DB_NAME, app='datadog-agent', user='datadog')
    check_activity_metrics(aggregator, expected_tags)


def test_activity_metrics_no_application_aggregation(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    pg_instance['activity_metrics_excluded_aggregations'] = ['application_name']
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance, db=DB_NAME, user='datadog')
    check_activity_metrics(aggregator, expected_tags)


def test_activity_metrics_no_aggregations(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    pg_instance['activity_metrics_excluded_aggregations'] = ['datname', 'application_name', 'usename']
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance)
    check_activity_metrics(aggregator, expected_tags)


def test_backend_transaction_age(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    check = integration_check(pg_instance)

    check.check(pg_instance)

    dd_agent_tags = _get_expected_tags(check, pg_instance, db=DB_NAME, app='datadog-agent', user='datadog')
    test_tags = _get_expected_tags(check, pg_instance, db=DB_NAME, app='test', user='datadog')
    # No transaction in progress, we have 0
    if float(POSTGRES_VERSION) >= 9.6:
        aggregator.assert_metric('postgresql.activity.backend_xmin_age', value=0, count=1, tags=dd_agent_tags)
    else:
        aggregator.assert_metric('postgresql.activity.backend_xmin_age', count=0, tags=dd_agent_tags)
    aggregator.assert_metric('postgresql.activity.xact_start_age', count=1, tags=dd_agent_tags)

    conn1 = _get_conn(pg_instance)
    cur = conn1.cursor()

    conn2 = _get_conn(pg_instance)
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
    }
    if len(version) == 2:
        version_metadata['version.minor'] = version[1]

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(5)  # for raw and patch


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


@requires_over_14
def test_wal_stats(aggregator, integration_check, pg_instance):
    conn = _get_superconn(pg_instance)
    with conn.cursor() as cur:
        cur.execute("select wal_records, wal_fpi, wal_bytes from pg_stat_wal;")
        (wal_records, wal_fpi, wal_bytes) = cur.fetchall()[0]
        cur.execute("insert into persons (lastname) values ('test');")

    # Wait for pg_stat_wal to be updated
    for _ in range(10):
        with conn.cursor() as cur:
            cur.execute("select wal_records, wal_bytes from pg_stat_wal;")
            new_wal_records = cur.fetchall()[0][0]
            if new_wal_records > wal_records:
                break
        time.sleep(0.1)

    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance)
    aggregator.assert_metric('postgresql.wal.records', count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.wal.bytes', count=1, tags=expected_tags)

    # Expect at least one Heap + one Transaction additional records in the WAL
    assert_metric_at_least(
        aggregator, 'postgresql.wal.records', tags=expected_tags, count=1, lower_bound=wal_records + 2
    )
    # We should have at least one full page write
    assert_metric_at_least(aggregator, 'postgresql.wal.bytes', tags=expected_tags, count=1, lower_bound=wal_bytes + 100)
    aggregator.assert_metric('postgresql.wal.full_page_images', tags=expected_tags, count=1, value=wal_fpi + 1)


def test_query_timeout(integration_check, pg_instance):
    pg_instance['query_timeout'] = 1000
    check = integration_check(pg_instance)
    check._connect()
    cursor = check.db.cursor()
    with pytest.raises(psycopg.errors.QueryCanceled):
        cursor.execute("select pg_sleep(2000)")


@requires_over_10
def test_wal_metrics(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    # Default PG's wal size is 16MB
    wal_size = 16777216

    postgres_conn = _get_superconn(pg_instance)
    with postgres_conn.cursor() as cur:
        cur.execute("select count(*) from pg_ls_waldir();")
        expected_num_wals = cur.fetchall()[0][0]

    check.check(pg_instance)

    expected_wal_size = expected_num_wals * wal_size
    dd_agent_tags = _get_expected_tags(check, pg_instance)
    aggregator.assert_metric('postgresql.wal_count', count=1, value=expected_num_wals, tags=dd_agent_tags)
    aggregator.assert_metric('postgresql.wal_size', count=1, value=expected_wal_size, tags=dd_agent_tags)

    with postgres_conn.cursor() as cur:
        # Force a wal switch
        cur.execute("select pg_switch_wal();")
        cur.fetchall()
        # Checkpoint to accelerate new wal file
        cur.execute("CHECKPOINT;")

    aggregator.reset()
    check.check(pg_instance)

    expected_num_wals += 1
    expected_wal_size = expected_num_wals * wal_size
    aggregator.assert_metric('postgresql.wal_count', count=1, value=expected_num_wals, tags=dd_agent_tags)
    aggregator.assert_metric('postgresql.wal_size', count=1, value=expected_wal_size, tags=dd_agent_tags)


def test_pg_control(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    check.check(pg_instance)

    dd_agent_tags = _get_expected_tags(check, pg_instance)
    aggregator.assert_metric('postgresql.control.timeline_id', count=1, value=1, tags=dd_agent_tags)

    postgres_conn = _get_superconn(pg_instance)
    with postgres_conn.cursor() as cur:
        cur.execute("CHECKPOINT;")

    aggregator.reset()
    check.check(pg_instance)
    # checkpoint should be less than 2s old
    assert_metric_at_least(
        aggregator, 'postgresql.control.checkpoint_delay', count=1, higher_bound=2.0, tags=dd_agent_tags
    )


def test_config_tags_is_unchanged_between_checks(integration_check, pg_instance):
    pg_instance['tag_replication_role'] = True
    check = integration_check(pg_instance)

    # Put elements in set as we don't care about order, only elements equality
    expected_tags = set(_get_expected_tags(check, pg_instance, db=DB_NAME))
    for _ in range(3):
        check.check(pg_instance)
        assert set(check._config.tags) == expected_tags


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
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['collect_resources'] = {'enabled': False}

    pg_instance['disable_generic_tags'] = False  # This flag also affects the hostname
    pg_instance['reported_hostname'] = reported_hostname

    with mock.patch(
        'datadog_checks.postgres.PostgreSql.resolve_db_host', return_value=expected_hostname
    ) as resolve_db_host:
        check = PostgreSql('test_instance', {}, [pg_instance])
        check.check(pg_instance)
        if reported_hostname:
            assert resolve_db_host.called is False, 'Expected resolve_db_host.called to be False'
        else:
            assert resolve_db_host.called == dbm_enabled, 'Expected resolve_db_host.called to be ' + str(dbm_enabled)

    expected_tags_no_db = _get_expected_tags(check, pg_instance, server=HOST)
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
