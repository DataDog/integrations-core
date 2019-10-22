# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.clickhouse import ClickhouseCheck, queries

from .utils import ensure_csv_safe, parse_described_metrics

pytestmark = pytest.mark.unit

def error(*args, **kwargs):
    raise Exception('test')


def test_error_query(instance):
    check = ClickhouseCheck('clickhouse', {}, [instance])
    check.log = mock.MagicMock()
    del check.check_initializations[-2]

    client = mock.MagicMock()
    client.execute_iter = error
    check._client = client

    check.run()
    check.log.error.assert_any_call('Error querying %s: %s', 'system.metrics', mock.ANY)


@pytest.mark.parametrize(
    'metrics, ignored_columns, metric_source_url',
    [
        (
            queries.SystemMetrics.query_data['columns'][1]['items'],
            {'Revision', 'VersionInteger'},
            'https://raw.githubusercontent.com/ClickHouse/ClickHouse/master/dbms/src/Common/CurrentMetrics.cpp',
        ),
        (
            queries.SystemEvents.query_data['columns'][1]['items'],
            set(),
            'https://raw.githubusercontent.com/ClickHouse/ClickHouse/master/dbms/src/Common/ProfileEvents.cpp',
        ),
    ],
    ids=['SystemMetrics', 'SystemEvents'],
)
def test_current_support(metrics, ignored_columns, metric_source_url):
    # While we're here, also check key order
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
