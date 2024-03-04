# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import MOCKED_PIPELINES_METRICS, MOCKED_TRIGGERS_METRICS, mock_http_responses


@pytest.mark.parametrize(
    'instance, metrics, namespace',
    [
        pytest.param('pipelines_instance', MOCKED_PIPELINES_METRICS, 'pipelines_controller', id='pipelines'),
        pytest.param('triggers_instance', MOCKED_TRIGGERS_METRICS, 'triggers_controller', id='triggers'),
    ],
)
def test_check(dd_run_check, aggregator, mocker, check, instance, metrics, request, namespace):
    mocker.patch("requests.get", wraps=mock_http_responses)
    dd_run_check(check(request.getfixturevalue(instance)))

    for expected_metric in metrics:
        aggregator.assert_metric(f"tekton.{namespace}.{expected_metric}")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(f"tekton.{namespace}.openmetrics.health", status=AgentCheck.OK, count=1)
    assert len(aggregator.service_check_names) == 1


def test_invalid_url(dd_run_check, aggregator, check, pipelines_instance, mocker):
    pipelines_instance["openmetrics_endpoint"] = "http://unknowwn"

    mocker.patch("requests.get", wraps=mock_http_responses)
    with pytest.raises(Exception):
        dd_run_check(check(pipelines_instance))

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check(
        "tekton.pipelines_controller.openmetrics.health", status=AgentCheck.CRITICAL, count=1
    )
