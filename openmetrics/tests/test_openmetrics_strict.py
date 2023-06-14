# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from six import PY2

from datadog_checks.openmetrics import OpenMetricsCheck

from .common import CHECK_NAME

pytestmark = [
    pytest.mark.usefixtures("strict_poll_mock"),
    pytest.mark.skipif(PY2, reason='Test only available on Python 3'),
]

instance_new_strict = {
    'openmetrics_endpoint': 'http://localhost:10249/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1'],
    'collect_histogram_buckets': True,
    'use_latest_spec': True,
}


def test_linkerd_v2_new_strict(aggregator, dd_run_check, caplog):
    from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper

    check = OpenMetricsCheck('openmetrics', {}, [instance_new_strict])
    scraper = OpenMetricsScraper(check, instance_new_strict)
    dd_run_check(check)

    aggregator.assert_metric(
        '{}.renamed.metric1'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host1', 'flavor:test', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        '{}.metric2'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'timestamp:123', 'node:host2', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        '{}.counter1.count'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host2'],
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    aggregator.assert_all_metrics_covered()

    assert check.http.options['headers']['Accept'] == '*/*'
    assert scraper.http.options['headers']['Accept'] == 'application/openmetrics-text; version=0.0.1; charset=utf-8'
    assert caplog.text == ''
