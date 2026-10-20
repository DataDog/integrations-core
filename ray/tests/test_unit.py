# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    HEAD_METRICS,
    MOCKED_HEAD_INSTANCE,
    MOCKED_WORKER_INSTANCE,
    WORKER_METRICS,
    register_metrics_responses,
)


@pytest.mark.parametrize(
    'instance, metrics',
    [
        pytest.param(MOCKED_HEAD_INSTANCE, HEAD_METRICS, id='head'),
        pytest.param(MOCKED_WORKER_INSTANCE, WORKER_METRICS, id='worker'),
    ],
)
def test_check(dd_run_check, aggregator, fake_http_response, check, instance, metrics):
    register_metrics_responses(fake_http_response)
    dd_run_check(check(instance))

    for expected_metric in metrics:
        aggregator.assert_metric(expected_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check("ray.openmetrics.health", status=AgentCheck.OK, count=1)
    assert len(aggregator.service_check_names) == 1


def test_invalid_url(dd_run_check, aggregator, check, mocked_head_instance, fake_http):
    mocked_head_instance["openmetrics_endpoint"] = "http://unknowwn"

    fake_http.register_response('GET', 'http://unknowwn', HTTPClientConnectionError('unknown host'))
    with pytest.raises(Exception):
        dd_run_check(check(mocked_head_instance))

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check("ray.openmetrics.health", status=AgentCheck.CRITICAL, count=1)
