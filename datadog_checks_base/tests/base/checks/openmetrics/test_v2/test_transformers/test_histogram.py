# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3

from ..utils import get_check

pytestmark = [
    requires_py3,
]


def assert_metric_counts(aggregator, payload):
    num_bucket_metrics = 0
    num_sum_metrics = 0
    num_count_metrics = 0

    lines = [line.strip() for line in payload.strip().splitlines()]
    metric_name = lines[0].split()[2]
    lines = lines[2:]

    for line in lines:
        if line.startswith('{}_sum'.format(metric_name)):
            num_sum_metrics += 1
        elif line.startswith('{}_count'.format(metric_name)):
            num_count_metrics += 1
        elif 'Inf"' not in line:
            num_bucket_metrics += 1

    assert len(aggregator.metrics('test.{}.bucket'.format(metric_name))) == num_bucket_metrics
    assert len(aggregator.metrics('test.{}.sum'.format(metric_name))) == num_sum_metrics
    assert len(aggregator.metrics('test.{}.count'.format(metric_name))) == num_count_metrics


def test_default(aggregator, dd_run_check, mock_http_response):
    payload = """
        # HELP etcd_disk_wal_fsync_duration_seconds The latency distributions of fsync called by wal.
        # TYPE etcd_disk_wal_fsync_duration_seconds histogram
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.001"} 2
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.002"} 2
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.004"} 2
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.008"} 2
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.016"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.032"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.064"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.128"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.256"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.512"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="1.024"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="2.048"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="4.096"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="8.192"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="+Inf"} 4
        etcd_disk_wal_fsync_duration_seconds_sum{kind="fs",app="vault"} 0.026131671
        etcd_disk_wal_fsync_duration_seconds_count{kind="fs",app="vault"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.001"} 718
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.002"} 740
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.004"} 743
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.008"} 748
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.016"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.032"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.064"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.128"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.256"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.512"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="1.024"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="2.048"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="4.096"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="8.192"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="+Inf"} 751
        etcd_disk_wal_fsync_duration_seconds_sum{kind="fs",app="kubernetes"} 0.3097010759999998
        etcd_disk_wal_fsync_duration_seconds_count{kind="fs",app="kubernetes"} 751
        """
    mock_http_response(payload)
    check = get_check({'metrics': ['.+']})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.etcd_disk_wal_fsync_duration_seconds.bucket',
        2,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'kind:fs', 'app:vault', 'upper_bound:0.001'],
    )
    aggregator.assert_metric(
        'test.etcd_disk_wal_fsync_duration_seconds.sum',
        0.026131671,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'kind:fs', 'app:vault'],
    )
    aggregator.assert_metric(
        'test.etcd_disk_wal_fsync_duration_seconds.count',
        4,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'kind:fs', 'app:vault'],
    )

    aggregator.assert_metric(
        'test.etcd_disk_wal_fsync_duration_seconds.bucket',
        718,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'kind:fs', 'app:kubernetes', 'upper_bound:0.001'],
    )
    aggregator.assert_metric(
        'test.etcd_disk_wal_fsync_duration_seconds.sum',
        0.3097010759999998,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'kind:fs', 'app:kubernetes'],
    )
    aggregator.assert_metric(
        'test.etcd_disk_wal_fsync_duration_seconds.count',
        751,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'kind:fs', 'app:kubernetes'],
    )

    aggregator.assert_all_metrics_covered()
    assert_metric_counts(aggregator, payload)


def test_disable_histogram_buckets(aggregator, dd_run_check, mock_http_response):
    payload = """
        # HELP etcd_disk_wal_fsync_duration_seconds The latency distributions of fsync called by wal.
        # TYPE etcd_disk_wal_fsync_duration_seconds histogram
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.001"} 2
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.002"} 2
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.004"} 2
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.008"} 2
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.016"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.032"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.064"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.128"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.256"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="0.512"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="1.024"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="2.048"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="4.096"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="8.192"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="vault",le="+Inf"} 4
        etcd_disk_wal_fsync_duration_seconds_sum{kind="fs",app="vault"} 0.026131671
        etcd_disk_wal_fsync_duration_seconds_count{kind="fs",app="vault"} 4
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.001"} 718
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.002"} 740
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.004"} 743
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.008"} 748
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.016"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.032"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.064"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.128"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.256"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="0.512"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="1.024"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="2.048"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="4.096"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="8.192"} 751
        etcd_disk_wal_fsync_duration_seconds_bucket{kind="fs",app="kubernetes",le="+Inf"} 751
        etcd_disk_wal_fsync_duration_seconds_sum{kind="fs",app="kubernetes"} 0.3097010759999998
        etcd_disk_wal_fsync_duration_seconds_count{kind="fs",app="kubernetes"} 751
        """
    mock_http_response(payload)
    check = get_check({'metrics': ['.+'], 'collect_histogram_buckets': False})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.etcd_disk_wal_fsync_duration_seconds.sum',
        0.026131671,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'kind:fs', 'app:vault'],
    )
    aggregator.assert_metric(
        'test.etcd_disk_wal_fsync_duration_seconds.count',
        4,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'kind:fs', 'app:vault'],
    )

    aggregator.assert_metric(
        'test.etcd_disk_wal_fsync_duration_seconds.sum',
        0.3097010759999998,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'kind:fs', 'app:kubernetes'],
    )
    aggregator.assert_metric(
        'test.etcd_disk_wal_fsync_duration_seconds.count',
        751,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'kind:fs', 'app:kubernetes'],
    )

    aggregator.assert_all_metrics_covered()
    assert len(aggregator.metrics('test.etcd_disk_wal_fsync_duration_seconds.sum')) == 2
    assert len(aggregator.metrics('test.etcd_disk_wal_fsync_duration_seconds.count')) == 2


def test_non_cumulative_histogram_buckets(aggregator, dd_run_check, mock_http_response):
    payload = """
        # HELP rest_client_request_latency_seconds Request latency in seconds. Broken down by verb and URL.
        # TYPE rest_client_request_latency_seconds histogram
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.004"} 702
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.001"} 254
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.002"} 621
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.008"} 727
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.016"} 738
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.032"} 744
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.064"} 748
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.128"} 754
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.256"} 755
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.512"} 755
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="+Inf"} 755
        rest_client_request_latency_seconds_sum{url="http://127.0.0.1:8080/api",verb="GET"} 2.185820220000001
        rest_client_request_latency_seconds_count{url="http://127.0.0.1:8080/api",verb="GET"} 755
        """
    mock_http_response(payload)
    check = get_check({'metrics': ['.+'], 'non_cumulative_histogram_buckets': True})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.bucket',
        81,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.004', 'lower_bound:0.002'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.bucket',
        254,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.001', 'lower_bound:0'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.bucket',
        367,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.002', 'lower_bound:0.001'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.bucket',
        25,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.008', 'lower_bound:0.004'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.bucket',
        11,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.016', 'lower_bound:0.008'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.bucket',
        6,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.032', 'lower_bound:0.016'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.bucket',
        4,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.064', 'lower_bound:0.032'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.bucket',
        6,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.128', 'lower_bound:0.064'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.bucket',
        1,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.256', 'lower_bound:0.128'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.bucket',
        0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.512', 'lower_bound:0.256'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.sum',
        2.185820220000001,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.count',
        755,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET'],
    )

    aggregator.assert_all_metrics_covered()
    assert_metric_counts(aggregator, payload)


def test_non_cumulative_histogram_buckets_single_bucket(aggregator, dd_run_check, mock_http_response):
    payload = """
        # HELP rest_client_request_latency_seconds Request latency in seconds. Broken down by verb and URL.
        # TYPE rest_client_request_latency_seconds histogram
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="+Inf"} 755
        rest_client_request_latency_seconds_sum{url="http://127.0.0.1:8080/api",verb="GET"} 2.185820220000001
        rest_client_request_latency_seconds_count{url="http://127.0.0.1:8080/api",verb="GET"} 755
        """
    mock_http_response(payload)
    check = get_check({'metrics': ['.+'], 'non_cumulative_histogram_buckets': True})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.sum',
        2.185820220000001,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.count',
        755,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET'],
    )

    aggregator.assert_all_metrics_covered()


def test_histogram_buckets_as_distributions(aggregator, dd_run_check, mock_http_response):
    payload = """
        # HELP rest_client_request_latency_seconds Request latency in seconds. Broken down by verb and URL.
        # TYPE rest_client_request_latency_seconds histogram
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.004"} 702
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.001"} 254
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.002"} 621
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.008"} 727
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.016"} 738
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.032"} 744
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.064"} 748
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.128"} 754
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.256"} 755
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.512"} 755
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="+Inf"} 755
        rest_client_request_latency_seconds_sum{url="http://127.0.0.1:8080/api",verb="GET"} 2.185820220000001
        rest_client_request_latency_seconds_count{url="http://127.0.0.1:8080/api",verb="GET"} 755
        """
    mock_http_response(payload)
    check = get_check(
        {
            'metrics': ['.+'],
            'histogram_buckets_as_distributions': True,
            # Implicitly activated
            'collect_histogram_buckets': False,
        }
    )
    dd_run_check(check)

    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        81,
        0.002,
        0.004,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.004', 'lower_bound:0.002'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        254,
        0,
        0.001,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.001', 'lower_bound:0'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        367,
        0.001,
        0.002,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.002', 'lower_bound:0.001'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        25,
        0.004,
        0.008,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.008', 'lower_bound:0.004'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        11,
        0.008,
        0.016,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.016', 'lower_bound:0.008'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        6,
        0.016,
        0.032,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.032', 'lower_bound:0.016'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        4,
        0.032,
        0.064,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.064', 'lower_bound:0.032'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        6,
        0.064,
        0.128,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.128', 'lower_bound:0.064'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        1,
        0.128,
        0.256,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.256', 'lower_bound:0.128'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        0,
        0.256,
        0.512,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.512', 'lower_bound:0.256'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        0,
        0.512,
        float('Inf'),
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:inf', 'lower_bound:0.512'],
    )

    aggregator.assert_all_metrics_covered()


def test_histogram_buckets_as_distributions_with_counters(aggregator, dd_run_check, mock_http_response):
    payload = """
        # HELP rest_client_request_latency_seconds Request latency in seconds. Broken down by verb and URL.
        # TYPE rest_client_request_latency_seconds histogram
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.004"} 702
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.001"} 254
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.002"} 621
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.008"} 727
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.016"} 738
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.032"} 744
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.064"} 748
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.128"} 754
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.256"} 755
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="0.512"} 755
        rest_client_request_latency_seconds_bucket{url="http://127.0.0.1:8080/api",verb="GET",le="+Inf"} 755
        rest_client_request_latency_seconds_sum{url="http://127.0.0.1:8080/api",verb="GET"} 2.185820220000001
        rest_client_request_latency_seconds_count{url="http://127.0.0.1:8080/api",verb="GET"} 755
        """
    mock_http_response(payload)
    check = get_check(
        {
            'metrics': ['.+'],
            'collect_counters_with_distributions': True,
            # Implicitly activated
            'histogram_buckets_as_distributions': False,
            'collect_histogram_buckets': False,
        }
    )
    dd_run_check(check)

    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.sum',
        2.185820220000001,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET'],
    )
    aggregator.assert_metric(
        'test.rest_client_request_latency_seconds.count',
        755,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET'],
    )

    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        81,
        0.002,
        0.004,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.004', 'lower_bound:0.002'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        254,
        0,
        0.001,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.001', 'lower_bound:0'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        367,
        0.001,
        0.002,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.002', 'lower_bound:0.001'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        25,
        0.004,
        0.008,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.008', 'lower_bound:0.004'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        11,
        0.008,
        0.016,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.016', 'lower_bound:0.008'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        6,
        0.016,
        0.032,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.032', 'lower_bound:0.016'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        4,
        0.032,
        0.064,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.064', 'lower_bound:0.032'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        6,
        0.064,
        0.128,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.128', 'lower_bound:0.064'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        1,
        0.128,
        0.256,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.256', 'lower_bound:0.128'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        0,
        0.256,
        0.512,
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:0.512', 'lower_bound:0.256'],
    )
    aggregator.assert_histogram_bucket(
        'test.rest_client_request_latency_seconds',
        0,
        0.512,
        float('Inf'),
        True,
        '',
        ['endpoint:test', 'url:http://127.0.0.1:8080/api', 'verb:GET', 'upper_bound:inf', 'lower_bound:0.512'],
    )

    aggregator.assert_all_metrics_covered()
