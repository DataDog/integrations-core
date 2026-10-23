# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError
from datadog_checks.dev.utils import get_metadata_metrics

from .common import PIPELINES_METRICS, TRIGGERS_METRICS, check, register_metrics


@pytest.mark.parametrize(
    'instance, metrics, namespace',
    [
        pytest.param('pipelines_instance', PIPELINES_METRICS, 'pipelines_controller', id='pipelines'),
        pytest.param('triggers_instance', TRIGGERS_METRICS, 'triggers_controller', id='triggers'),
    ],
)
def test_check(dd_run_check, aggregator, fake_http, fake_http_response, instance, metrics, request, namespace):
    config = request.getfixturevalue(instance)
    endpoint = config[f'{namespace}_endpoint']
    register_metrics(fake_http_response, endpoint)
    dd_run_check(check(config))
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]

    for expected_metric in metrics:
        aggregator.assert_metric(f"tekton.{namespace}.{expected_metric}")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(f"tekton.{namespace}.openmetrics.health", status=AgentCheck.OK, count=1)
    assert len(aggregator.service_check_names) == 1


def test_invalid_url(dd_run_check, aggregator, pipelines_instance, fake_http):
    pipelines_instance["pipelines_controller_endpoint"] = "http://unknowwn"
    fake_http.register_response('GET', 'http://unknowwn', HTTPClientConnectionError('unavailable'))
    with pytest.raises(Exception, match='unavailable'):
        dd_run_check(check(pipelines_instance))
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', 'http://unknowwn')]

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check(
        "tekton.pipelines_controller.openmetrics.health", status=AgentCheck.CRITICAL, count=1
    )


def test_no_endpoint_configured(dd_run_check, aggregator, pipelines_instance):
    del pipelines_instance["pipelines_controller_endpoint"]

    with pytest.raises(
        Exception,
        match="Must specify at least one of the following: pipelines_controller_endpoint, "
        "triggers_controller_endpoint.",
    ):
        dd_run_check(check(pipelines_instance))
