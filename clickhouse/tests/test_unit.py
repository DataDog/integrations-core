# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from clickhouse_driver.errors import Error, NetworkError
from six import PY3

from datadog_checks.clickhouse import ClickhouseCheck, queries

from .utils import ensure_csv_safe, parse_described_metrics, raise_error

pytestmark = pytest.mark.unit


def test_config(instance):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.check_id = 'test-clickhouse'

    with mock.patch('clickhouse_driver.Client') as m:
        check.connect()
        m.assert_called_once_with(
            host=instance['server'],
            port=instance['port'],
            user=instance['username'],
            password=instance['password'],
            database='default',
            connect_timeout=10,
            send_receive_timeout=10,
            sync_request_timeout=10,
            compression=False,
            secure=False,
            settings={},
            client_name='datadog-test-clickhouse',
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
    # While we're here, also check key order
    if PY3:
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
    with mock.patch("datadog_checks.clickhouse.clickhouse.clickhouse_driver"):
        # Test for consecutive healthy clickhouse.can_connect statuses
        num_runs = 3
        for _ in range(num_runs):
            check.check({})
    aggregator.assert_service_check("clickhouse.can_connect", count=num_runs, status=check.OK)


@mock.patch('datadog_checks.base.AgentCheck.is_metadata_collection_enabled', return_value=False)
def test_can_connect_recovers_after_failed_connection(is_metadata_collection_enabled, aggregator, instance):
    check = ClickhouseCheck('clickhouse', {}, [instance])

    # Test 1 healthy connection --> 2 Unhealthy service checks --> 1 healthy connection. Recovered
    with mock.patch("datadog_checks.clickhouse.clickhouse.clickhouse_driver"):
        check.check({})
    with mock.patch('clickhouse_driver.Client', side_effect=NetworkError('Connection refused')):
        with mock.patch('datadog_checks.clickhouse.ClickhouseCheck.ping_clickhouse', return_value=False):
            with pytest.raises(Exception):
                check.check({})
            with pytest.raises(Exception):
                check.check({})
    with mock.patch("datadog_checks.clickhouse.clickhouse.clickhouse_driver"):
        check.check({})
    aggregator.assert_service_check("clickhouse.can_connect", count=2, status=check.CRITICAL)
    aggregator.assert_service_check("clickhouse.can_connect", count=2, status=check.OK)


@mock.patch('datadog_checks.base.AgentCheck.is_metadata_collection_enabled', return_value=False)
def test_can_connect_recovers_after_failed_ping(is_metadata_collection_enabled, aggregator, instance):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    # Test Exception in ping_clickhouse(), but reestablishes connection.
    with mock.patch("datadog_checks.clickhouse.clickhouse.clickhouse_driver"):
        check.check({})
        with mock.patch('datadog_checks.clickhouse.ClickhouseCheck.ping_clickhouse', side_effect=Error()):
            # connect() should be able to handle an exception in ping_clickhouse() and attempt reconnection
            check.check({})
        check.check({})
    aggregator.assert_service_check("clickhouse.can_connect", count=3, status=check.OK)
