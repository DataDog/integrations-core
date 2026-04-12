# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from clickhouse_connect.driver.exceptions import Error, OperationalError

from datadog_checks.base import ConfigurationError
from datadog_checks.clickhouse import ClickhouseCheck, queries

from .utils import ensure_csv_safe, parse_described_metrics, raise_error

pytestmark = pytest.mark.unit


def test_config(instance):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.check_id = 'test-clickhouse'

    with mock.patch('clickhouse_connect.get_client') as m:
        mock_client = mock.MagicMock()
        m.return_value = mock_client
        check.connect()
        m.assert_called_once_with(
            host=instance['server'],
            port=instance['port'],
            username=instance['username'],
            password=instance['password'],
            database='default',
            connect_timeout=10,
            send_receive_timeout=10,
            secure=False,
            ca_cert=None,
            verify=True,
            client_name='datadog-test-clickhouse',
            compress=False,
            autogenerate_session_id=False,
            settings={},
            pool_mgr=mock.ANY,
        )


def test_error_query(instance, dd_run_check):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.log = mock.MagicMock()
    del check.check_initializations[-2]

    client = mock.MagicMock()
    client.execute_iter = raise_error
    check._client = client
    with pytest.raises(Exception):
        dd_run_check(check)


@pytest.mark.latest_metrics
@pytest.mark.parametrize(
    'metrics, ignored_columns, metric_source_url',
    [
        (
            queries.SystemMetrics['columns'][1]['items'],
            {'Revision', 'VersionInteger'},
            'https://raw.githubusercontent.com/ClickHouse/ClickHouse/master/src/Common/CurrentMetrics.cpp',
        ),
        (
            queries.SystemEvents['columns'][1]['items'],
            set(),
            'https://raw.githubusercontent.com/ClickHouse/ClickHouse/master/src/Common/ProfileEvents.cpp',
        ),
    ],
    ids=['SystemMetrics', 'SystemEvents'],
)
def test_latest_metrics_supported(metrics, ignored_columns, metric_source_url):
    assert list(metrics) == sorted(metrics)

    described_metrics = parse_described_metrics(metric_source_url)

    difference = set(described_metrics).difference(metrics).difference(ignored_columns)

    if difference:  # no cov
        num_metrics = len(difference)
        raise AssertionError(
            '{} newly documented metric{}!\n{}'.format(
                num_metrics,
                's' if num_metrics > 1 else '',
                '\n'.join(
                    '---> {} | {}'.format(metric, ensure_csv_safe(described_metrics[metric]))
                    for metric in sorted(difference)
                ),
            )
        )


@mock.patch('datadog_checks.base.AgentCheck.is_metadata_collection_enabled', return_value=False)
def test_can_connect_submits_on_every_check_run(is_metadata_collection_enabled, aggregator, instance):
    """
    Regression test: a copy of the `can_connect` service check must be submitted for each check run.
    (It used to be submitted only once on check init, which led to customer seeing "no data" in the UI.)
    """
    check = ClickhouseCheck('clickhouse', {}, [instance])
    with mock.patch("datadog_checks.clickhouse.clickhouse.clickhouse_connect"):
        # Test for consecutive healthy clickhouse.can_connect statuses
        num_runs = 3
        for _ in range(num_runs):
            check.check({})
    aggregator.assert_service_check("clickhouse.can_connect", count=num_runs, status=check.OK)


@mock.patch('datadog_checks.base.AgentCheck.is_metadata_collection_enabled', return_value=False)
def test_can_connect_recovers_after_failed_connection(is_metadata_collection_enabled, aggregator, instance):
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Test 1 healthy connection --> 2 Unhealthy service checks --> 1 healthy connection. Recovered
    with mock.patch("datadog_checks.clickhouse.clickhouse.clickhouse_connect"):
        check.check({})
    with mock.patch('clickhouse_connect.get_client', side_effect=OperationalError('Connection refused')):
        with mock.patch('datadog_checks.clickhouse.ClickhouseCheck.ping_clickhouse', return_value=False):
            with pytest.raises(Exception):
                check.check({})
            with pytest.raises(Exception):
                check.check({})
    with mock.patch("datadog_checks.clickhouse.clickhouse.clickhouse_connect"):
        check.check({})
    aggregator.assert_service_check("clickhouse.can_connect", count=2, status=check.CRITICAL)
    aggregator.assert_service_check("clickhouse.can_connect", count=2, status=check.OK)


@mock.patch('datadog_checks.base.AgentCheck.is_metadata_collection_enabled', return_value=False)
def test_can_connect_recovers_after_failed_ping(is_metadata_collection_enabled, aggregator, instance):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    # Test Exception in ping_clickhouse(), but reestablishes connection.
    with mock.patch("datadog_checks.clickhouse.clickhouse.clickhouse_connect"):
        check.check({})
        with mock.patch('datadog_checks.clickhouse.ClickhouseCheck.ping_clickhouse', side_effect=Error()):
            # connect() should be able to handle an exception in ping_clickhouse() and attempt reconnection
            check.check({})
        check.check({})
    aggregator.assert_service_check("clickhouse.can_connect", count=3, status=check.OK)


def test_validate_config(instance):
    instance['compression'] = 'invalid-compression-type'
    check = ClickhouseCheck('clickhouse', {}, [instance])
    with pytest.raises(ConfigurationError):
        check.validate_config()


def test_deprecated_user_option():
    """Test that the deprecated 'user' option is migrated to 'username' with a warning."""
    instance = {
        'server': 'localhost',
        'port': 8128,
        'user': 'datadog',  # Using deprecated option
        'password': 'test123',
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Check that username was set from user
    assert check._config.username == 'datadog'

    # Check that deprecation warning was added
    assert any('user' in warning and 'deprecated' in warning.lower() for warning in check._validation_result.warnings)


def test_deprecated_user_option_with_username():
    """Test that username takes precedence over user when both are provided."""
    instance = {
        'server': 'localhost',
        'port': 8128,
        'user': 'old_user',  # Using deprecated option
        'username': 'new_user',  # New option takes precedence
        'password': 'test123',
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Check that username was preferred
    assert check._config.username == 'new_user'

    # Check that deprecation warning was still added
    assert any('user' in warning and 'deprecated' in warning.lower() for warning in check._validation_result.warnings)


def test_deprecated_host_option():
    """Test that the deprecated 'host' option is migrated to 'server' with a warning."""
    instance = {
        'host': 'localhost',  # Using deprecated option
        'port': 8128,
        'username': 'datadog',
        'password': 'test123',
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Check that server was set from host
    assert check._config.server == 'localhost'

    # Check that deprecation warning was added
    assert any('host' in warning and 'deprecated' in warning.lower() for warning in check._validation_result.warnings)


def test_missing_server_config():
    """Test that missing server/host configuration triggers an error."""
    instance = {
        # Missing both 'server' and 'host'
        'port': 8128,
        'username': 'datadog',
        'password': 'test123',
    }

    check = ClickhouseCheck('clickhouse', {}, [instance])

    # The error should be in the validation result
    assert not check._validation_result.valid
    assert any('server' in str(error).lower() for error in check._validation_result.errors)


def test_connect_no_password_uses_empty_string():
    """
    Regression test: when no password is configured, connect() must pass password=''
    not password=None. clickhouse_connect encodes None as the literal string 'None'
    in the Authorization header, causing ClickHouse error code 194 (auth failure).
    """
    instance = {
        'server': 'localhost',
        'port': 8123,
        'username': 'default',
        # 'password' intentionally omitted
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.check_id = 'test-no-password'

    assert check._config.password == '', (
        "password must default to '' — None causes auth error 194 in clickhouse_connect"
    )

    with mock.patch('clickhouse_connect.get_client') as m:
        mock_client = mock.MagicMock()
        m.return_value = mock_client
        check.connect()
        _, kwargs = m.call_args
        assert kwargs['password'] == '', "connect() must pass password='' not password=None to clickhouse_connect"


# ---------------------------------------------------------------------------
# _detect_stalled_merges unit tests
# ---------------------------------------------------------------------------

_INSTANCE = {'server': 'localhost', 'port': 8123}


def _make_check():
    return ClickhouseCheck('clickhouse', {}, [_INSTANCE])


def test_detect_stalled_merges_progressing():
    """A merge that has made progress is NOT flagged as stalled."""
    check = _make_check()
    check.stall_threshold_seconds = 300

    key = ('db', 'tbl', 'part_1')
    previous = {key: {'progress': 0.10, 'elapsed': 400.0, 'database': 'db', 'table': 'tbl'}}
    current = {key: {'progress': 0.25, 'elapsed': 500.0, 'database': 'db', 'table': 'tbl'}}

    stalled = check._detect_stalled_merges(current, previous)
    assert stalled == {}


def test_detect_stalled_merges_stalled():
    """A merge with no meaningful progress beyond the threshold IS flagged."""
    check = _make_check()
    check.stall_threshold_seconds = 300

    key = ('db', 'tbl', 'part_1')
    previous = {key: {'progress': 0.10, 'elapsed': 350.0, 'database': 'db', 'table': 'tbl'}}
    current = {key: {'progress': 0.105, 'elapsed': 410.0, 'database': 'db', 'table': 'tbl'}}

    stalled = check._detect_stalled_merges(current, previous)
    assert stalled[('db', 'tbl')] == 1


def test_detect_stalled_merges_counts_multiple_stalled_parts():
    """Multiple stalled merges on the same table are counted separately."""
    check = _make_check()
    check.stall_threshold_seconds = 300

    previous = {
        ('db', 'tbl', 'part_1'): {'progress': 0.10, 'elapsed': 400.0, 'database': 'db', 'table': 'tbl'},
        ('db', 'tbl', 'part_2'): {'progress': 0.20, 'elapsed': 500.0, 'database': 'db', 'table': 'tbl'},
    }
    current = {
        ('db', 'tbl', 'part_1'): {'progress': 0.101, 'elapsed': 460.0, 'database': 'db', 'table': 'tbl'},
        ('db', 'tbl', 'part_2'): {'progress': 0.201, 'elapsed': 560.0, 'database': 'db', 'table': 'tbl'},
    }

    stalled = check._detect_stalled_merges(current, previous)
    assert stalled[('db', 'tbl')] == 2


def test_detect_stalled_merges_completed_merge_evicted():
    """A completed merge (absent from current snapshot) is silently dropped."""
    check = _make_check()
    check.stall_threshold_seconds = 300

    key = ('db', 'tbl', 'completed_part')
    previous = {key: {'progress': 0.90, 'elapsed': 800.0, 'database': 'db', 'table': 'tbl'}}
    current = {}  # merge completed — no longer in system.merges

    stalled = check._detect_stalled_merges(current, previous)
    assert stalled == {}


def test_detect_stalled_merges_below_threshold():
    """A merge with no progress but below the elapsed threshold is NOT stalled."""
    check = _make_check()
    check.stall_threshold_seconds = 300

    key = ('db', 'tbl', 'part_1')
    previous = {key: {'progress': 0.10, 'elapsed': 100.0, 'database': 'db', 'table': 'tbl'}}
    current = {key: {'progress': 0.101, 'elapsed': 160.0, 'database': 'db', 'table': 'tbl'}}

    stalled = check._detect_stalled_merges(current, previous)
    assert stalled == {}


def test_detect_stalled_merges_new_merge_not_stalled():
    """A merge that has no previous snapshot (new this collection) is skipped."""
    check = _make_check()
    check.stall_threshold_seconds = 300

    key = ('db', 'tbl', 'brand_new_part')
    current = {key: {'progress': 0.0, 'elapsed': 400.0, 'database': 'db', 'table': 'tbl'}}

    stalled = check._detect_stalled_merges(current, {})
    assert stalled == {}


# ---------------------------------------------------------------------------
# _compute_mv_staleness unit tests
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta  # noqa: E402


def _clear_check_tags(check):
    """Remove all instance tags so metric assertions are predictable."""
    check.tag_manager.set_tags_from_list([], replace=True)


def test_compute_mv_staleness_source_newer_than_target(aggregator):
    """freshness_lag_seconds is emitted when source is newer than target."""
    check = _make_check()
    _clear_check_tags(check)

    now = datetime.utcnow()
    source_time = now
    target_time = now - timedelta(seconds=120)

    with mock.patch.object(check, '_fetch_mv_catalog', return_value=[
        {'database': 'db', 'view_name': 'mv1', 'source_database': 'db', 'source_table': 'src'}
    ]):
        with mock.patch.object(check, '_fetch_newest_part_times', return_value={
            ('db', 'src'): source_time,
            ('db', '.inner_id.mv1'): target_time,
        }):
            check._compute_mv_staleness()

    aggregator.assert_metric('clickhouse.view.target.freshness_lag_seconds', value=120.0, at_least=1)


def test_compute_mv_staleness_source_absent(aggregator):
    """No metric is emitted when source table has no parts."""
    check = _make_check()
    _clear_check_tags(check)

    with mock.patch.object(check, '_fetch_mv_catalog', return_value=[
        {'database': 'db', 'view_name': 'mv1', 'source_database': 'db', 'source_table': 'src'}
    ]):
        with mock.patch.object(check, '_fetch_newest_part_times', return_value={
            # source key absent
            ('db', '.inner_id.mv1'): datetime.utcnow(),
        }):
            check._compute_mv_staleness()

    assert len(aggregator.metrics('clickhouse.view.target.freshness_lag_seconds')) == 0


def test_compute_mv_staleness_target_absent(aggregator):
    """No metric is emitted when target table has no parts."""
    check = _make_check()
    _clear_check_tags(check)

    with mock.patch.object(check, '_fetch_mv_catalog', return_value=[
        {'database': 'db', 'view_name': 'mv1', 'source_database': 'db', 'source_table': 'src'}
    ]):
        with mock.patch.object(check, '_fetch_newest_part_times', return_value={
            ('db', 'src'): datetime.utcnow(),
            # target key absent
        }):
            check._compute_mv_staleness()

    assert len(aggregator.metrics('clickhouse.view.target.freshness_lag_seconds')) == 0


def test_compute_mv_staleness_lag_clamped_to_zero(aggregator):
    """Negative lag (target newer than source) is clamped to 0."""
    check = _make_check()
    _clear_check_tags(check)

    now = datetime.utcnow()

    with mock.patch.object(check, '_fetch_mv_catalog', return_value=[
        {'database': 'db', 'view_name': 'mv1', 'source_database': 'db', 'source_table': 'src'}
    ]):
        with mock.patch.object(check, '_fetch_newest_part_times', return_value={
            ('db', 'src'): now - timedelta(seconds=60),
            ('db', '.inner_id.mv1'): now,  # target is newer
        }):
            check._compute_mv_staleness()

    aggregator.assert_metric('clickhouse.view.target.freshness_lag_seconds', value=0.0, at_least=1)


# ---------------------------------------------------------------------------
# _collect_view_refreshes version gate unit tests
# ---------------------------------------------------------------------------


def test_view_refreshes_skipped_below_23_4(aggregator):
    """_collect_view_refreshes emits nothing on ClickHouse < 23.4."""
    check = _make_check()
    _clear_check_tags(check)
    check._dbms_version = '22.8.1.1'

    with mock.patch.object(check, 'execute_query_raw') as mock_query:
        check._collect_view_refreshes()

    mock_query.assert_not_called()
    assert check._view_refreshes_supported is False


def test_view_refreshes_runs_on_23_4(aggregator):
    """_collect_view_refreshes queries system.view_refreshes on ClickHouse >= 23.4."""
    check = _make_check()
    _clear_check_tags(check)
    check._dbms_version = '23.4.2.1'

    with mock.patch.object(check, 'execute_query_raw', return_value=[]):
        check._collect_view_refreshes()

    assert check._view_refreshes_supported is True


def test_view_refreshes_marks_unsupported_on_error(aggregator):
    """If system.view_refreshes raises an error, _view_refreshes_supported is set False."""
    check = _make_check()
    _clear_check_tags(check)
    check._dbms_version = '23.5.0.0'
    check._view_refreshes_supported = True  # pre-set to skip version check

    with mock.patch.object(check, 'execute_query_raw', side_effect=Exception("table doesn't exist")):
        check._collect_view_refreshes()

    assert check._view_refreshes_supported is False


def test_view_refreshes_emits_correct_metrics(aggregator):
    """Verify all expected metrics are emitted for a single view_refreshes row."""
    check = _make_check()
    _clear_check_tags(check)
    check._dbms_version = '24.1.0.0'
    check._view_refreshes_supported = True

    fake_row = ('mydb', 'mv_orders', 'Refreshable', 'Running', 2.5, 10, 5000, 1024000, 0, 30.0)

    with mock.patch.object(check, 'execute_query_raw', return_value=[fake_row]):
        check._collect_view_refreshes()

    expected_tags = ['database:mydb', 'view:mv_orders', 'mv_type:Refreshable', 'status:Running']
    aggregator.assert_metric('clickhouse.view.refresh.duration_seconds', value=2.5, tags=expected_tags)
    aggregator.assert_metric('clickhouse.view.rows', value=5000, tags=expected_tags)
    aggregator.assert_metric('clickhouse.view.bytes', value=1024000, tags=expected_tags)
    aggregator.assert_metric('clickhouse.view.refresh.is_failing', value=0, tags=expected_tags)
    aggregator.assert_metric('clickhouse.view.refresh.seconds_since_success', value=30.0, tags=expected_tags)


# ---------------------------------------------------------------------------
# Config: merges_monitoring and materialized_views_monitoring defaults
# ---------------------------------------------------------------------------


def test_merges_monitoring_defaults():
    """merges_monitoring uses sensible defaults when not configured."""
    check = _make_check()
    assert check._config.merges_monitoring is not None
    assert check._config.merges_monitoring.stall_detection_threshold_seconds == 300
    assert check._config.merges_monitoring.mutation_age_alert_hours == 24
    assert check.stall_threshold_seconds == 300


def test_merges_monitoring_custom_threshold():
    """stall_detection_threshold_seconds is propagated to the check."""
    instance = {'server': 'localhost', 'port': 8123, 'merges_monitoring': {'stall_detection_threshold_seconds': 600}}
    check = ClickhouseCheck('clickhouse', {}, [instance])
    assert check.stall_threshold_seconds == 600


def test_materialized_views_monitoring_defaults():
    """materialized_views_monitoring uses sensible defaults when not configured."""
    check = _make_check()
    assert check._config.materialized_views_monitoring is not None
    assert check._config.materialized_views_monitoring.trigger_mv_staleness_threshold_seconds == 600
    assert check.trigger_staleness_threshold == 600


def test_is_version_supported():
    """_is_version_supported correctly compares calver tuples."""
    check = _make_check()
    assert check._is_version_supported('23.4.0.0', min_year=23, min_major=4) is True
    assert check._is_version_supported('23.5.0.0', min_year=23, min_major=4) is True
    assert check._is_version_supported('24.1.0.0', min_year=23, min_major=4) is True
    assert check._is_version_supported('23.3.9.9', min_year=23, min_major=4) is False
    assert check._is_version_supported('22.8.0.0', min_year=23, min_major=4) is False
    assert check._is_version_supported('bad.version', min_year=23, min_major=4) is False
