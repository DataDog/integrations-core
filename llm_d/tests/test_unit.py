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
from datadog_checks.llm_d import LlmDCheck

from .common import (
    COORDINATOR_HISTOGRAMS,
    COORDINATOR_METRICS,
    ROUTER_HISTOGRAMS,
    ROUTER_METRICS,
    SIDECAR_HISTOGRAMS,
    SIDECAR_METRICS,
    get_fixture_path,
)


def run_check(dd_run_check, instance, fixture_file):
    check = LlmDCheck('llm_d', {}, [instance])
    with mock.patch('requests.Session.get', return_value=MockResponse(file_path=get_fixture_path(fixture_file))):
        dd_run_check(check)


@pytest.mark.parametrize(
    ('fixture_file', 'metrics', 'histograms'),
    [
        pytest.param('llm_d_router_metrics.txt', ROUTER_METRICS, ROUTER_HISTOGRAMS, id='router'),
        pytest.param('llm_d_sidecar_metrics.txt', SIDECAR_METRICS, SIDECAR_HISTOGRAMS, id='sidecar'),
        pytest.param('llm_d_coordinator_metrics.txt', COORDINATOR_METRICS, COORDINATOR_HISTOGRAMS, id='coordinator'),
    ],
)
def test_check_collects_mapped_metrics(dd_run_check, aggregator, router_instance, fixture_file, metrics, histograms):
    run_check(dd_run_check, router_instance, fixture_file)

    for metric in metrics:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

    for metric in histograms:
        aggregator.assert_histogram_bucket(
            metric, None, None, None, monotonic=True, hostname=None, tags=None, at_least=1
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('llm_d.openmetrics.health', ServiceCheck.OK)


@pytest.mark.parametrize(
    ('fixture_file', 'metric', 'tag'),
    [
        ('llm_d_router_metrics.txt', 'llm_d.epp.pool.ready_endpoints', 'inference_pool:llama-3-1-8b-pool'),
        ('llm_d_router_metrics.txt', 'llm_d.epp.endpoint.queue_size', 'inference_pool:llama-3-1-8b-pool'),
        ('llm_d_router_metrics.txt', 'llm_d.epp.scheduler.attempts.count', 'endpoint_namespace:llm-d'),
        ('llm_d_router_metrics.txt', 'llm_d.epp.scheduler.attempts.count', 'endpoint_port:8000'),
        ('llm_d_router_metrics.txt', 'llm_d.epp.inflight.requests', 'endpoint_namespace:llm-d'),
    ],
)
def test_labels_are_renamed_to_avoid_collisions(dd_run_check, aggregator, router_instance, fixture_file, metric, tag):
    run_check(dd_run_check, router_instance, fixture_file)

    aggregator.assert_metric_has_tag(metric, tag)


def test_emits_critical_openmetrics_service_check_when_service_is_down(
    dd_run_check, aggregator, router_instance, mock_http_response
):
    mock_http_response(status_code=404)
    check = LlmDCheck('llm_d', {}, [router_instance])

    with pytest.raises(Exception, match='requests.exceptions.HTTPError'):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('llm_d.openmetrics.health', ServiceCheck.CRITICAL)


def test_check_skipped_when_gpu_monitoring_disabled(router_instance):
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': False}):
        with pytest.raises(SkipInstanceError):
            LlmDCheck('llm_d', {}, [router_instance])
