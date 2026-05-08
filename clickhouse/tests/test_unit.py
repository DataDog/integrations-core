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


def test_config_verify_false(instance):
    """Regression: verify: false must be forwarded to the shared pool manager.

    When pool_mgr is provided to clickhouse-connect, it skips creating its own
    TLS-aware pool, so TLS settings must be baked into the pool at creation time.
    """
    instance = {**instance, 'verify': False}
    with mock.patch('clickhouse_connect.driver.httputil.get_pool_manager') as mock_pool:
        mock_pool.return_value = mock.MagicMock()
        ClickhouseCheck('clickhouse', {}, [instance])
        mock_pool.assert_called_once_with(maxsize=8, num_pools=4, verify=False, ca_cert=None)


def test_config_tls_ca_cert_forwarded_to_pool_manager(instance):
    """Regression: tls_ca_cert must be forwarded to the shared pool manager.

    Same failure mode as verify=False: if ca_cert isn't baked into the pre-supplied
    pool manager, clickhouse-connect's get_client can't apply it later.
    """
    instance = {**instance, 'tls_ca_cert': '/path/to/ca.pem'}
    with mock.patch('clickhouse_connect.driver.httputil.get_pool_manager') as mock_pool:
        mock_pool.return_value = mock.MagicMock()
        ClickhouseCheck('clickhouse', {}, [instance])
        mock_pool.assert_called_once_with(maxsize=8, num_pools=4, verify=True, ca_cert='/path/to/ca.pem')


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


@pytest.mark.parametrize("bad_value", [0, -1, -100])
def test_query_errors_zero_samples_per_hour_defaults(bad_value):
    """Zero or negative samples_per_hour_per_query must not crash the constructor via ZeroDivisionError."""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'dbm': True,
        'query_errors': {'enabled': True, 'samples_per_hour_per_query': bad_value},
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    assert check._config.query_errors.samples_per_hour_per_query > 0
    assert any('query_errors.samples_per_hour_per_query' in w for w in check._validation_result.warnings)


@pytest.mark.parametrize("bad_value", [0, -1, -100])
def test_query_completions_zero_samples_per_hour_defaults(bad_value):
    """Zero or negative samples_per_hour_per_query must not crash the constructor via ZeroDivisionError."""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'dbm': True,
        'query_completions': {'enabled': True, 'samples_per_hour_per_query': bad_value},
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    assert check._config.query_completions.samples_per_hour_per_query > 0
    assert any('query_completions.samples_per_hour_per_query' in w for w in check._validation_result.warnings)
