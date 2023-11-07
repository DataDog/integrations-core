# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.karpenter import KarpenterCheck

from .common import RENAMED_LABELS, TEST_METRICS, get_fixture_path


def test_check_mock_karpenter_openmetrics(dd_run_check, instance, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('karpenter_metrics.txt'))
    check = KarpenterCheck('karpenter', {}, [instance])
    dd_run_check(check)

    for metric in TEST_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('karpenter.openmetrics.health', ServiceCheck.OK)


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  Field required',
    ):
        check = KarpenterCheck('karpenter', {}, [{}])
        dd_run_check(check)


def test_custom_validation(dd_run_check):
    instance = {'openmetrics_endpoint': 'karpenter:2112/metrics'}
    for k, v in instance.items():
        with pytest.raises(
            Exception,
            match=f'{k}: {v} is incorrectly configured',
        ):
            check = KarpenterCheck('karpenter', {}, [instance])
            dd_run_check(check)


def test_rename_labels(dd_run_check, instance, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('rename_labels_metrics.txt'))
    check = KarpenterCheck('karpenter', {}, [instance])
    dd_run_check(check)
    for tag in RENAMED_LABELS:
        aggregator.assert_metric_has_tag("karpenter.go_info", tag)
