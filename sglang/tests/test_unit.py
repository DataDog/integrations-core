# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.errors import SkipInstanceError
from datadog_checks.base.stubs import datadog_agent
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.sglang import SglangCheck

from .common import HISTOGRAMS, METRICS, get_fixture_path


def test_check_collects_metrics_with_percentiles_enabled(dd_run_check, aggregator, instance):
    check = SglangCheck('sglang', {}, [instance])

    with mock.patch(
        'requests.Session.get', return_value=MockResponse(file_path=get_fixture_path('sglang_metrics.txt'))
    ):
        dd_run_check(check)

    for metric in METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

    for metric in HISTOGRAMS:
        aggregator.assert_histogram_bucket(
            metric, None, None, None, monotonic=True, hostname=None, tags=None, at_least=1
        )

    aggregator.assert_metric_has_tag('sglang.http.requests.active', 'http_endpoint:/generate')
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('sglang.openmetrics.health', ServiceCheck.OK)


def test_emits_critical_openmetrics_service_check_when_service_is_down(
    dd_run_check, aggregator, instance, mock_http_response
):
    mock_http_response(status_code=404)
    check = SglangCheck('sglang', {}, [instance])

    with pytest.raises(Exception, match='requests.exceptions.HTTPError'):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('sglang.openmetrics.health', ServiceCheck.CRITICAL)


def test_check_skipped_when_gpu_monitoring_disabled(instance):
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': False}):
        with pytest.raises(SkipInstanceError):
            SglangCheck('sglang', {}, [instance])
