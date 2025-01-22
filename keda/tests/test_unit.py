# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.keda import KedaCheck

from .common import TEST_METRICS, get_fixture_path


def test_check_mock_keda_openmetrics(dd_run_check, instance, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('keda_metrics.txt'))
    check = KedaCheck('keda', {}, [instance])
    dd_run_check(check)

    for metric in TEST_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('keda.openmetrics.health', ServiceCheck.OK)


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='The setting `openmetrics_endpoint` is required',
    ):
        check = KedaCheck('keda', {}, [{}])
        dd_run_check(check)
