# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.errors import SkipInstanceError
from datadog_checks.base.stubs import datadog_agent
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.tensorrt_llm import TensorrtLlmCheck

from .common import (
    CONDITIONAL_HISTOGRAMS,
    CONDITIONAL_METRICS,
    HISTOGRAMS,
    METRICS_1_3_0,
    METRICS_1_4_0RC4,
    get_fixture_path,
)


def run_check(dd_run_check, fake_http_response, instance, fixture_file):
    with open(get_fixture_path(fixture_file)) as f:
        fake_http_response(instance['openmetrics_endpoint'], f.read())
    dd_run_check(TensorrtLlmCheck('tensorrt_llm', {}, [instance]))


@pytest.mark.parametrize(
    ('fixture_file', 'metrics', 'histograms'),
    [
        pytest.param('tensorrt_llm_1.3.0_metrics.txt', METRICS_1_3_0, HISTOGRAMS, id='1.3.0'),
        pytest.param('tensorrt_llm_1.4.0rc4_metrics.txt', METRICS_1_4_0RC4, HISTOGRAMS, id='1.4.0rc4'),
        pytest.param(
            'tensorrt_llm_conditional_metrics.txt', CONDITIONAL_METRICS, CONDITIONAL_HISTOGRAMS, id='conditional'
        ),
    ],
)
def test_check_collects_mapped_metrics(
    dd_run_check, aggregator, fake_http_response, instance, fixture_file, metrics, histograms
):
    run_check(dd_run_check, fake_http_response, instance, fixture_file)

    for metric in metrics:
        aggregator.assert_metric(metric)

    for metric in histograms:
        aggregator.assert_histogram_bucket(
            metric, None, None, None, monotonic=True, hostname=None, tags=None, at_least=1
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('tensorrt_llm.openmetrics.health', ServiceCheck.OK)


@pytest.mark.parametrize(
    ('metric', 'value', 'tags'),
    [
        ('tensorrt_llm.num_requests.running', 16, ['model_name:qwen3-0.6b', 'engine_type:pytorch']),
        ('tensorrt_llm.num_requests.waiting', 0, ['model_name:qwen3-0.6b', 'engine_type:pytorch']),
        ('tensorrt_llm.kv_cache.usage', 0.05397727272727273, ['model_name:qwen3-0.6b', 'dp_rank:0']),
        ('tensorrt_llm.kv_cache.max_blocks', 3520, ['model_name:qwen3-0.6b', 'dp_rank:0']),
        ('tensorrt_llm.spec_decode.accept_length', 1.4375, ['model_name:qwen3-0.6b']),
    ],
)
def test_mapped_values_and_labels(dd_run_check, aggregator, fake_http_response, instance, metric, value, tags):
    run_check(dd_run_check, fake_http_response, instance, 'tensorrt_llm_1.4.0rc4_metrics.txt')

    aggregator.assert_metric(metric, value=value)
    for tag in tags:
        aggregator.assert_metric_has_tag(metric, tag)


def test_pid_label_is_excluded_when_instance_sets_exclude_labels(
    dd_run_check, aggregator, fake_http_response, instance
):
    instance['exclude_labels'] = ['engine_type']
    run_check(dd_run_check, fake_http_response, instance, 'tensorrt_llm_1.3.0_metrics.txt')

    for metric in aggregator.metric_names:
        for sample in aggregator.metrics(metric):
            assert not any(tag.startswith(('pid:', 'engine_type:')) for tag in sample.tags), (metric, sample.tags)


def test_emits_critical_openmetrics_service_check_when_service_is_down(
    dd_run_check, aggregator, fake_http_response, instance
):
    fake_http_response(instance['openmetrics_endpoint'], status_code=404)
    check = TensorrtLlmCheck('tensorrt_llm', {}, [instance])

    with pytest.raises(Exception, match='HTTPClientStatusError'):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('tensorrt_llm.openmetrics.health', ServiceCheck.CRITICAL)


def test_check_skipped_when_gpu_monitoring_disabled(instance):
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': False}):
        with pytest.raises(SkipInstanceError):
            TensorrtLlmCheck('tensorrt_llm', {}, [instance])
