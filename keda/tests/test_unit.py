# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.keda import KedaCheck

from .common import TEST_METRICS, get_fixture_path

pytestmark = pytest.mark.unit


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:11 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert KedaCheck.DEFAULT_METRIC_LIMIT == 0


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
        match='\nopenmetrics_endpoint\n  Field required',
    ):
        check = KedaCheck('keda', {}, [{}])
        dd_run_check(check)
