# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import HEAD_METRICS, MOCKED_HEAD_INSTANCE, MOCKED_WORKER_INSTANCE, WORKER_METRICS, mock_http_responses


@pytest.mark.parametrize(
    'instance, metrics',
    [
        pytest.param(MOCKED_HEAD_INSTANCE, HEAD_METRICS, id='head'),
        pytest.param(MOCKED_WORKER_INSTANCE, WORKER_METRICS, id='worker'),
    ],
)
def test_check(dd_run_check, aggregator, mocker, check, instance, metrics):
    mocker.patch("requests.get", wraps=mock_http_responses)
    dd_run_check(check(instance))

    for expected_metric in metrics:
        aggregator.assert_metric(expected_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check("ray.openmetrics.health", status=AgentCheck.OK, count=1)
    assert len(aggregator.service_check_names) == 1


def test_invalid_url(dd_run_check, aggregator, check, mocked_head_instance, mocker):
    mocked_head_instance["openmetrics_endpoint"] = "http://unknowwn"

    mocker.patch("requests.get", wraps=mock_http_responses)
    with pytest.raises(Exception):
        dd_run_check(check(mocked_head_instance))

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check("ray.openmetrics.health", status=AgentCheck.CRITICAL, count=1)
