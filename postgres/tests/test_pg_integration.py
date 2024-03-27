# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import contextlib
import socket
import time

import mock
import psycopg2
import pytest
from flaky import flaky

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.stubs import datadog_agent
from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.__about__ import __version__
from datadog_checks.postgres.util import DatabaseHealthCheckError, PartialFormatter, fmt

from .common import (
    COMMON_METRICS,
    DB_NAME,
    DBM_MIGRATED_METRICS,
    HOST,
    PASSWORD_ADMIN,
    POSTGRES_VERSION,
    USER_ADMIN,
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
    check_performance_metrics,
    check_physical_replication_slots,
    check_slru_metrics,
    check_snapshot_txid_metrics,
    check_stat_replication,
    check_stat_wal_metrics,
    check_uptime_metrics,
    check_wal_receiver_metrics,
    requires_static_version,
)
from .utils import (
    _get_conn,
    _get_superconn,
    _wait_for_value,
    kill_vacuum,
    requires_over_10,
    requires_over_14,
    run_one_check,
    run_vacuum_thread,
)

CONNECTION_METRICS = ['postgresql.max_connections', 'postgresql.percent_usage_connections']

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.mark.parametrize(
    'is_aurora',
    [True, False],
)
def test_common_metrics(aggregator, integration_check, pg_instance, is_aurora):
    check = integration_check(pg_instance)
    check.is_aurora = is_aurora
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
        check_file_wal_metrics(aggregator, expected_tags=expected_tags)
        check_stat_wal_metrics(aggregator, expected_tags=expected_tags)
    check_uptime_metrics(aggregator, expected_tags=expected_tags)

    check_logical_replication_slots(aggregator, expected_tags)
    check_physical_replication_slots(aggregator, expected_tags)
    check_snapshot_txid_metrics(aggregator, expected_tags=expected_tags)

    check_performance_metrics(aggregator, expected_tags=check.debug_stats_kwargs()['tags'], is_aurora=is_aurora)

    aggregator.assert_all_metrics_covered()


def _increase_txid(cur):
    # Force increases of txid
    if float(POSTGRES_VERSION) >= 13.0:
        query = 'select pg_current_xact_id();'
    else:
        query = 'select txid_current();'
    cur.execute(query)


def test_snapshot_xmin(aggregator, integration_check, pg_instance):
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        conn.set_session(autocommit=True)
        with conn.cursor() as cur:
            if float(POSTGRES_VERSION) >= 13.0:
                query = 'select pg_snapshot_xmin(pg_current_snapshot());'
            else:
                query = 'select txid_snapshot_xmin(txid_current_snapshot());'
            cur.execute(query)
            xmin = float(cur.fetchall()[0][0])
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance)
    aggregator.assert_metric('postgresql.snapshot.xmin', count=1, tags=expected_tags)
    assert aggregator.metrics('postgresql.snapshot.xmin')[0].value >= xmin
    aggregator.assert_metric('postgresql.snapshot.xmax', count=1, tags=expected_tags)
    assert aggregator.metrics('postgresql.snapshot.xmax')[0].value >= xmin

    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        # Force autocommit
        conn.set_session(autocommit=True)
        with conn.cursor() as cur:
            _increase_txid(cur)

    aggregator.reset()
    check = integration_check(pg_instance)
    check.check(pg_instance)
    aggregator.assert_metric('postgresql.snapshot.xmin', count=1, tags=expected_tags)
    assert aggregator.metrics('postgresql.snapshot.xmin')[0].value > xmin
    aggregator.assert_metric('postgresql.snapshot.xmax', count=1, tags=expected_tags)
    assert aggregator.metrics('postgresql.snapshot.xmax')[0].value > xmin


def test_snapshot_xip(aggregator, integration_check, pg_instance):
    conn1 = _get_conn(pg_instance)
    cur = conn1.cursor()

    # Start a transaction
    cur.execute('BEGIN;')
    # Force assignement of a txid and keep the transaction opened
    _increase_txid(cur)
    # Make sure to fetch the result to make sure we start the timer after the transaction started
    cur.fetchall()

    with _get_conn(pg_instance) as conn2:
        with conn2.cursor() as cur2:
            # Force increases of txid
            _increase_txid(cur2)

    check = integration_check(pg_instance)
    check.check(pg_instance)

    # Cleanup
    cur.close()
    conn1.close()

    expected_tags = _get_expected_tags(check, pg_instance)
    aggregator.assert_metric('postgresql.snapshot.xip_count', value=1, count=1, tags=expected_tags)


def test_common_metrics_without_size(aggregator, integration_check, pg_instance):
    pg_instance['collect_database_size_metrics'] = False
    check = integration_check(pg_instance)
    check.check(pg_instance)
    assert 'postgresql.database_size' not in aggregator.metric_names


def test_uptime(aggregator, integration_check, pg_instance):
    with _get_conn(pg_instance) as conn:
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
    with _get_conn(pg_instance) as conn:
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
        _increase_txid(cur)
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

    expected_tags = _get_expected_tags(check, pg_instance)
    check_bgw_metrics(aggregator, expected_tags)

    check_common_metrics(aggregator, expected_tags=expected_tags)


def test_can_connect_service_check(aggregator, integration_check, pg_instance):
    # First: check run with a valid postgres instance
    check = integration_check(pg_instance)

    check.check(pg_instance)
    expected_tags = _get_expected_tags(check, pg_instance, with_db=True)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.OK, tags=expected_tags)
    aggregator.reset()

    # Second: keep the connection open but an unexpected error happens during check run
    orig_db = check.db

    # Second: keep the connection open but an unexpected error happens during check run
    with pytest.raises(AttributeError):
        check.db = mock.MagicMock(side_effect=AttributeError('foo'))
        check.check(pg_instance)
    # Since we can't connect to the host, we can't gather the replication role
    tags_without_role = _get_expected_tags(
        check, pg_instance, with_db=True, with_version=False, with_sys_id=False, role=None
    )
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.CRITICAL, tags=tags_without_role)
    aggregator.reset()

    # Third: connection still open but this time no error
    check.db = orig_db
    check.check(pg_instance)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.OK, tags=expected_tags)

    # Forth: connection health check failed
    with pytest.raises(DatabaseHealthCheckError):
        db = mock.MagicMock()
        db.cursor().__enter__().execute.side_effect = psycopg2.OperationalError('foo')

        @contextlib.contextmanager
        def mock_db():
            yield db

        check.db = mock_db
        check.check(pg_instance)
    aggregator.assert_service_check('postgres.can_connect', count=1, status=PostgreSql.CRITICAL, tags=tags_without_role)
    aggregator.reset()


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
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
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
    # datname is a required aggregation because our activity metric query is always grouping by database id.
    # Setting it should issue a warning, be ignored and still produce an aggregation by db
    pg_instance['activity_metrics_excluded_aggregations'] = ['datname', 'application_name', 'usename']
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance, db=DB_NAME)
    check_activity_metrics(aggregator, expected_tags)


@requires_over_10
def test_activity_vacuum_excluded(aggregator, integration_check, pg_instance):
    pg_instance['collect_activity_metrics'] = True
    check = integration_check(pg_instance)

    # Run vacuum in a thread
    thread = run_vacuum_thread(pg_instance, 'VACUUM (DISABLE_PAGE_SKIPPING, ANALYZE) persons', application_name='test')

    # Wait for vacuum to be running
    _wait_for_value(
        pg_instance,
        lower_threshold=0,
        query="SELECT count(*) from pg_stat_activity WHERE backend_type = 'client backend' AND query ~* '^vacuum';",
    )

    conn_increase_txid = _get_conn(pg_instance, user=USER_ADMIN, password=PASSWORD_ADMIN, application_name='test')
    cur = conn_increase_txid.cursor()
    # Increase txid counter
    _increase_txid(cur)
    _increase_txid(cur)
    # Start a transaction with xmin age = 1
    cur.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;')
    _increase_txid(cur)

    # Gather metrics
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance, db=DB_NAME, app='test', user=USER_ADMIN)
    aggregator.assert_metric('postgresql.waiting_queries', value=1, count=1, tags=expected_tags)
    # Vacuum process with 3 xmin age should not be reported
    aggregator.assert_metric('postgresql.activity.backend_xmin_age', count=1, tags=expected_tags)
    # We can not predict the value of backend_xid_age, most of the time it will be 1 here, but the value is a bit flaky
    assert aggregator.metrics('postgresql.activity.backend_xmin_age')[0].value <= 2

    # Cleaning
    kill_vacuum(pg_instance)
    cur.close()
    conn_increase_txid.close()
    thread.join()


@flaky(max_runs=5)
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

    # Start a transaction in repeatable read to force pinning of backend_xmin
    cur.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;')
    # Force assignement of a txid and keep the transaction opened
    _increase_txid(cur)
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

    with _get_conn(pg_instance) as conn2:
        with conn2.cursor() as cur2:
            # Open a new session and assign a new txid to it.
            _increase_txid(cur2)

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

    # cleanup
    cur.close()
    conn1.close()


@requires_over_10
def test_wrong_version(integration_check, pg_instance):
    check = integration_check(pg_instance)
    # Enforce the wrong version
    check._version_utils.get_raw_version = mock.MagicMock(return_value="9.6.0")

    check.check(pg_instance)
    assert_state_clean(check)
    # Reset the mock to a good version
    check._version_utils.get_raw_version = mock.MagicMock(return_value="13.0.0")

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
@pytest.mark.parametrize(
    'is_aurora',
    [True, False],
)
@flaky(max_runs=5)
def test_wal_stats(aggregator, integration_check, pg_instance, is_aurora):
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
    check.is_aurora = is_aurora
    if is_aurora is True:
        return
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
    assert_metric_at_least(
        aggregator, 'postgresql.wal.full_page_images', tags=expected_tags, count=1, lower_bound=wal_fpi
    )


def test_query_timeout(integration_check, pg_instance):
    pg_instance['query_timeout'] = 1000
    check = integration_check(pg_instance)
    check._connect()
    with pytest.raises(psycopg2.errors.QueryCanceled):
        with check.db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("select pg_sleep(2000)")


@requires_over_10
@pytest.mark.parametrize(
    'is_aurora',
    [True, False],
)
def test_wal_metrics(aggregator, integration_check, pg_instance, is_aurora):
    check = integration_check(pg_instance)
    check.is_aurora = is_aurora

    if is_aurora is True:
        return
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
    expected_tags = set(
        _get_expected_tags(check, pg_instance, db=DB_NAME, with_version=False, with_sys_id=False, role=None)
    )
    for _ in range(3):
        check.check(pg_instance)
        assert set(check._config.tags) == expected_tags


@mock.patch.dict('os.environ', {'DDEV_SKIP_GENERIC_TAGS_CHECK': 'true'})
@pytest.mark.parametrize(
    'dbm_enabled, reported_hostname, expected_hostname',
    [
        (True, '', 'resolved.hostname'),
        (False, '', 'resolved.hostname'),
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
            assert resolve_db_host.called is True

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


@pytest.mark.parametrize(
    'dbm_enabled, reported_hostname',
    [
        (True, None),
        (False, None),
        (True, 'forced_hostname'),
        (True, 'forced_hostname'),
    ],
)
def test_database_instance_metadata(aggregator, pg_instance, dbm_enabled, reported_hostname):
    pg_instance['dbm'] = dbm_enabled
    # this will block on cancel and wait for the coll interval of 600 seconds,
    # unless the collection_interval is set to a short amount of time
    pg_instance['collect_resources'] = {'collection_interval': 0.1}
    if reported_hostname:
        pg_instance['reported_hostname'] = reported_hostname
    expected_host = reported_hostname if reported_hostname else 'stubbed.hostname'
    expected_tags = pg_instance['tags'] + ['port:{}'.format(pg_instance['port'])]
    check = PostgreSql('test_instance', {}, [pg_instance])
    run_one_check(check, pg_instance)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'database_instance'), None)
    assert event is not None
    assert event['host'] == expected_host
    assert event['dbms'] == "postgres"
    assert event['tags'].sort() == expected_tags.sort()
    assert event['integration_version'] == __version__
    assert event['collection_interval'] == 1800
    assert event['metadata'] == {
        'dbm': dbm_enabled,
        'connection_host': pg_instance['host'],
    }

    # Run a second time and expect the metadata to not be emitted again because of the cache TTL
    aggregator.reset()
    run_one_check(check, pg_instance)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'database_instance'), None)
    assert event is None


@pytest.mark.parametrize(
    "aws_metadata, expected_error, error_msg, expected_managed_auth_enabled",
    [
        (
            {
                "instance_endpoint": "mydb.cfxgae8cilcf.us-east-1.rds.amazonaws.com",
            },
            None,
            None,
            False,
        ),
        (
            {
                "instance_endpoint": "mydb.cfxgae8cilcf.us-east-1.rds.amazonaws.com",
                "region": "us-east-1",
            },
            psycopg2.OperationalError,
            'password authentication failed',
            True,
        ),
        (
            {
                "instance_endpoint": "mydb.cfxgae8cilcf.us-east-1.rds.amazonaws.com",
                "region": "us-east-1",
                "managed_authentication": {
                    "enabled": True,
                },
            },
            psycopg2.OperationalError,
            'password authentication failed',
            True,
        ),
        (
            {
                'region': 'us-east-1',
            },
            psycopg2.OperationalError,
            'password authentication failed',
            True,
        ),
        (
            {
                "region": "us-east-1",
                "managed_authentication": {
                    "enabled": 'false',
                },
            },
            None,
            None,
            False,
        ),
        (
            {
                'region': 'us-east-1',
                "managed_authentication": {
                    "enabled": 'true',
                },
            },
            psycopg2.OperationalError,
            'password authentication failed',
            True,
        ),
        (
            {
                "managed_authentication": {
                    "enabled": 'true',
                }
            },
            ConfigurationError,
            'AWS region must be set when using AWS managed authentication',
            None,  # IAM auth requires region so this should fail
        ),
    ],
)
def test_database_instance_cloud_metadata_aws(
    aggregator, integration_check, pg_instance, aws_metadata, expected_error, error_msg, expected_managed_auth_enabled
):
    '''
    This test is to verify different combinations of aws metadata and managed_authentication settings.
    In legacy config, managed_authentication is inferred from the presence of region.
    With the updated config, managed_authentication is explicitly set.
    This test verifies that the check runs with the expected managed_authentication setting and tags.
    '''
    pg_instance["aws"] = aws_metadata
    if not expected_error:
        check = integration_check(pg_instance)
        check.check(pg_instance)
    else:
        # When IAM auth is enabled, unit test should fail with password authentication error
        # this is because boto3.generate_rds_iam_token will always return a token (presigned url)
        with mock.patch('datadog_checks.postgres.aws.generate_rds_iam_token') as mocked_generate_rds_iam_token:
            mocked_generate_rds_iam_token.return_value = 'faketoken'
            with pytest.raises(expected_error, match=error_msg):
                check = integration_check(pg_instance)
                check.check(pg_instance)
            if expected_managed_auth_enabled:
                assert mocked_generate_rds_iam_token.called

    if not expected_error == ConfigurationError:
        # we only assert the check ran if we don't expect a ConfigurationError
        assert check.cloud_metadata['aws']['managed_authentication']['enabled'] == expected_managed_auth_enabled

        role = None if expected_error else 'master'
        expected_tags = _get_expected_tags(check, pg_instance, with_db=True, role=role)
        if "instance_endpoint" in aws_metadata:
            expected_tags.append("dd.internal.resource:aws_rds_instance:{}".format(aws_metadata["instance_endpoint"]))

        status = check.CRITICAL if expected_error else check.OK
        aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=status, tags=expected_tags)


@pytest.mark.parametrize(
    "azure_metadata, managed_identity, expected_error, error_msg, expected_managed_auth_enabled",
    [
        (
            {
                "deployment_type": "flexible_server",
                "fully_qualified_domain_name": "my-postgres-database.database.windows.net",
            },
            None,
            None,
            None,
            False,
        ),
        (
            {
                "deployment_type": "flexible_server",
                "fully_qualified_domain_name": "my-postgres-database.database.windows.net",
            },
            {
                "client_id": "my-client-id",
            },
            psycopg2.OperationalError,
            'password authentication failed',
            True,
        ),
        (
            {
                "deployment_type": "flexible_server",
                "fully_qualified_domain_name": "my-postgres-database.database.windows.net",
                "managed_authentication": {
                    "enabled": False,
                },
            },
            {
                "client_id": "my-client-id",
            },
            None,
            None,
            False,
        ),
        (
            {
                "deployment_type": "flexible_server",
                "fully_qualified_domain_name": "my-postgres-database.database.windows.net",
                "managed_authentication": {
                    "enabled": 'false',
                },
            },
            {
                "client_id": "my-client-id",
            },
            None,
            None,
            False,
        ),
        (
            {
                "deployment_type": "flexible_server",
                "fully_qualified_domain_name": "my-postgres-database.database.windows.net",
                "managed_authentication": {
                    "enabled": True,
                    "client_id": "my-client-id",
                },
            },
            {
                "client_id": "my-client-id",
            },
            psycopg2.OperationalError,
            'password authentication failed',
            True,
        ),
        (
            {
                "deployment_type": "flexible_server",
                "fully_qualified_domain_name": "my-postgres-database.database.windows.net",
                "managed_authentication": {
                    "enabled": 'true',
                    "client_id": "my-client-id",
                    'identity_scope': 'https://database.windows.net/.default',
                },
            },
            None,
            psycopg2.OperationalError,
            'password authentication failed',
            True,
        ),
        (
            {
                "deployment_type": "flexible_server",
                "fully_qualified_domain_name": "my-postgres-database.database.windows.net",
                "managed_authentication": {
                    "enabled": True,
                },
            },
            None,
            ConfigurationError,
            'Azure client_id must be set when using Azure managed authentication',
            None,
        ),
    ],
)
def test_database_instance_cloud_metadata_azure(
    aggregator,
    integration_check,
    pg_instance,
    azure_metadata,
    managed_identity,
    expected_error,
    error_msg,
    expected_managed_auth_enabled,
):
    '''
    This test is to verify different combinations of aws metadata and managed_authentication settings.
    In legacy config, managed_authentication is inferred from the presence of region.
    With the updated config, managed_authentication is explicitly set.
    This test verifies that the check runs with the expected managed_authentication setting and tags.
    '''
    pg_instance["azure"] = azure_metadata
    if managed_identity:
        pg_instance["managed_identity"] = managed_identity
    if not expected_error:
        check = integration_check(pg_instance)
        check.check(pg_instance)
    else:
        # When IAM auth is enabled, unit test should fail with password authentication error
        # this is because boto3.generate_rds_iam_token will always return a token (presigned url)
        with mock.patch(
            'datadog_checks.postgres.azure.generate_managed_identity_token'
        ) as generate_managed_identity_token:
            generate_managed_identity_token.return_value = 'faketoken'
            with pytest.raises(expected_error, match=error_msg):
                check = integration_check(pg_instance)
                check.check(pg_instance)
            if expected_managed_auth_enabled:
                assert generate_managed_identity_token.called

    if not expected_error == ConfigurationError:
        # we only assert the check ran if we don't expect a ConfigurationError
        assert check.cloud_metadata['azure']['managed_authentication']['enabled'] == expected_managed_auth_enabled

        role = None if expected_error else 'master'
        expected_tags = _get_expected_tags(check, pg_instance, with_db=True, role=role)
        if "fully_qualified_domain_name" in azure_metadata:
            expected_tags.append(
                "dd.internal.resource:azure_postgresql_flexible_server:{}".format(
                    azure_metadata["fully_qualified_domain_name"]
                )
            )

        status = check.CRITICAL if expected_error else check.OK
        aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=status, tags=expected_tags)

        if managed_identity:
            assert check.warnings == [
                (
                    'DEPRECATION NOTICE: The managed_identity option is deprecated and will be removed '
                    'in a future version. Please use the new azure.managed_authentication option instead.'
                )
            ]


def assert_state_clean(check):
    assert check.metrics_cache.instance_metrics is None
    assert check.metrics_cache.bgw_metrics is None
    assert check.metrics_cache.archiver_metrics is None
    assert check.metrics_cache.replication_metrics is None
    assert check.metrics_cache.activity_metrics is None


def assert_state_set(check):
    assert check.metrics_cache.instance_metrics
    assert check.metrics_cache.bgw_metrics
    if POSTGRES_VERSION != '9.3':
        assert check.metrics_cache.archiver_metrics
    assert check.metrics_cache.replication_metrics


@requires_over_10
def test_replication_tag(aggregator, integration_check, pg_instance):
    test_metric = 'postgresql.db.count'

    pg_instance['tag_replication_role'] = False
    check = integration_check(pg_instance)

    # no replication
    check.check(pg_instance)
    aggregator.assert_metric(test_metric, tags=_get_expected_tags(check, pg_instance, role=None))
    aggregator.reset()

    # role = master
    pg_instance['tag_replication_role'] = True
    check = integration_check(pg_instance)

    check.check(pg_instance)
    aggregator.assert_metric(test_metric, tags=_get_expected_tags(check, pg_instance, role='master'))
    aggregator.reset()

    # switchover: master -> standby
    standby_role = 'standby'
    check._get_replication_role = mock.MagicMock(return_value=standby_role)
    check.check(pg_instance)
    aggregator.assert_metric(test_metric, tags=_get_expected_tags(check, pg_instance, role=standby_role))


@pytest.mark.parametrize(
    'collect_wal_metrics',
    [True, False, None],
)
@requires_over_10
def test_collect_wal_metrics_metrics(aggregator, integration_check, pg_instance, collect_wal_metrics):
    pg_instance['collect_wal_metrics'] = collect_wal_metrics
    check = integration_check(pg_instance)
    check.is_aurora = False
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance)
    # if collect_wal_metrics is not set, wal metrics are collected on pg >= 10 by default
    expected_count = 0 if collect_wal_metrics is False else 1
    check_file_wal_metrics(aggregator, expected_tags=expected_tags, count=expected_count)


@pytest.mark.parametrize(
    'instance_propagate_agent_tags,init_config_propagate_agent_tags,should_propagate_agent_tags',
    [
        pytest.param(True, True, True, id="both true"),
        pytest.param(True, False, True, id="instance config true prevails"),
        pytest.param(False, True, False, id="instance config false prevails"),
        pytest.param(False, False, False, id="both false"),
        pytest.param(None, True, True, id="init_config true applies to all instances"),
        pytest.param(None, False, False, id="init_config false applies to all instances"),
        pytest.param(None, None, False, id="default to false"),
        pytest.param(True, None, True, id="instance config true prevails, init_config is None"),
        pytest.param(False, None, False, id="instance config false prevails, init_config is None"),
    ],
)
def test_propagate_agent_tags(
    aggregator,
    integration_check,
    pg_instance,
    instance_propagate_agent_tags,
    init_config_propagate_agent_tags,
    should_propagate_agent_tags,
):
    init_config = {}
    if instance_propagate_agent_tags is not None:
        pg_instance['propagate_agent_tags'] = instance_propagate_agent_tags
    if init_config_propagate_agent_tags is not None:
        init_config['propagate_agent_tags'] = init_config_propagate_agent_tags

    agent_tags = ["my-env:test-env", "random:tag", "bar:foo"]

    with mock.patch.object(datadog_agent, 'get_config', passthrough=True) as mock_agent:
        mock_agent.side_effect = lambda option: agent_tags
        check = integration_check(pg_instance, init_config)
        assert check._config._should_propagate_agent_tags(pg_instance, init_config) == should_propagate_agent_tags
        if should_propagate_agent_tags:
            assert all(tag in check.tags for tag in agent_tags)
            check.check(pg_instance)
            expected_tags = _get_expected_tags(check, pg_instance, with_db=True)
            aggregator.assert_service_check(
                'postgres.can_connect', count=1, status=PostgreSql.OK, tags=expected_tags + agent_tags
            )
