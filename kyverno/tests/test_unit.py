# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kyverno import KyvernoCheck

from .common import (
    ADMISSION_METRICS,
    BACKGROUND_METRICS,
    COMMON_METRICS,
    OM_MOCKED_INSTANCE,
    REPORTS_METRICS,
    get_fixture_path,
)


@pytest.mark.parametrize(
    'fixture_name, expected_metrics',
    [
        ('admission', ADMISSION_METRICS),
        ('background', BACKGROUND_METRICS),
        ('cleanup', []),
        ('reports', REPORTS_METRICS),
    ],
)
def test_kyverno_mock_metrics(dd_run_check, aggregator, mock_http_response, fixture_name, expected_metrics):
    mock_http_response(file_path=get_fixture_path(f'{fixture_name}_controller.txt'))
    check = KyvernoCheck('kyverno', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in expected_metrics + COMMON_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('kyverno.openmetrics.health', ServiceCheck.OK)


def test_kyverno_mock_invalid_endpoint(dd_run_check, aggregator, mock_http_response):
    mock_http_response(status_code=503)
    check = KyvernoCheck('kyverno', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('kyverno.openmetrics.health', ServiceCheck.CRITICAL)


def test_kyverno_label_remap(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('remap_labels.txt'))
    check = KyvernoCheck('kyverno', {}, [OM_MOCKED_INSTANCE])
    relabeled_tags = ['kyverno_namespace:foo', 'kyverno_name:baz', 'go_version:go1.21.10']
    dd_run_check(check)

    aggregator.assert_metric('kyverno.go.info')
    for tag in relabeled_tags:
        aggregator.assert_metric_has_tag('kyverno.go.info', tag)
