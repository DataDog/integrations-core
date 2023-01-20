# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
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
