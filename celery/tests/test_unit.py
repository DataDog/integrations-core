# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.celery import CeleryCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import METRICS, get_fixture_path


def _openmetrics_response(file_path: str) -> FakeHTTPResponse:
    with open(file_path, 'rb') as response_file:
        content = response_file.read()
    text = content.decode('utf-8')
    return FakeHTTPResponse(content=content, text=text, lines=text.splitlines())


def test_check(dd_run_check, aggregator, instance, fake_http):
    fake_http.register_response(
        'GET',
        instance['openmetrics_endpoint'],
        _openmetrics_response(get_fixture_path('flower_metrics.txt')),
        match_options={'stream': True},
    )

    check = CeleryCheck('celery', {}, [instance])
    dd_run_check(check)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("celery.flower.openmetrics.health", ServiceCheck.OK)
    fake_http.assert_all_responses_consumed()


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  Field required',
    ):
        check = CeleryCheck('celery', {}, [{}])
        dd_run_check(check)


def test_emits_critical_openemtrics_service_check_when_service_is_down(dd_run_check, aggregator, instance, fake_http):
    """
    If we fail to reach the openmetrics endpoint the openmetrics service check should report as critical
    """
    fake_http.register_response(
        'GET',
        instance['openmetrics_endpoint'],
        FakeHTTPResponse(
            status_code=404,
            status_error=HTTPClientStatusError('404 Client Error'),
        ),
        match_options={'stream': True},
    )
    check = CeleryCheck("celery", {}, [instance])
    with pytest.raises(Exception, match="HTTPClientStatusError"):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check("celery.flower.openmetrics.health", ServiceCheck.CRITICAL)
    fake_http.assert_all_responses_consumed()
