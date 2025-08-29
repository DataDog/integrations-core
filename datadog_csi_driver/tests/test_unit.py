# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.datadog_csi_driver import DatadogCSIDriverCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import METRICS_MOCK, NAMESPACE, get_fixture_path


def test_check(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    check = DatadogCSIDriverCheck(NAMESPACE, {}, [instance])
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tags(
            metric,
            [
                'status:success',
                'path:/var/run/datadog',
                'type:DSDSocketDirectory',
            ],
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
