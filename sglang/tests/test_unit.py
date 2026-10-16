# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from unittest import mock

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.errors import SkipInstanceError
from datadog_checks.base.stubs import datadog_agent
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.sglang import SglangCheck

from .common import HISTOGRAMS, METRICS, get_fixture_path


def test_check_collects_metrics_with_percentiles_enabled(
    dd_run_check, aggregator, instance, fake_http, fake_http_response
):
    fake_http_response(
        instance['openmetrics_endpoint'],
        Path(get_fixture_path('sglang_metrics.txt')).read_bytes(),
        match_options={'stream': True},
    )
    check = SglangCheck('sglang', {}, [instance])
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
    fake_http.assert_all_responses_consumed()


def test_startup_and_weight_update_metrics_keep_distinct_meanings(
    dd_run_check, aggregator, instance, fake_http, fake_http_response
):
    fake_http_response(
        instance['openmetrics_endpoint'],
        '''
        # TYPE sglang:engine_startup_time gauge
        sglang:engine_startup_time 9.2
        # TYPE sglang:engine_load_weights_time gauge
        sglang:engine_load_weights_time 6.1
        # TYPE sglang:startup_time_seconds gauge
        sglang:startup_time_seconds{phase="load_weight"} 6.3
        # TYPE sglang:weight_load_duration_seconds gauge
        sglang:weight_load_duration_seconds{source="disk"} 1.4
        ''',
        match_options={'stream': True},
    )
    check = SglangCheck('sglang', {}, [instance])
    dd_run_check(check)

    for metric in (
        'sglang.startup.seconds',
        'sglang.weight_load.seconds',
        'sglang.startup.phase.seconds',
        'sglang.weight_update.seconds',
    ):
        aggregator.assert_metric(metric)

    aggregator.assert_metric_has_tag('sglang.startup.phase.seconds', 'phase:load_weight')
    aggregator.assert_metric_has_tag('sglang.weight_update.seconds', 'source:disk')
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    fake_http.assert_all_responses_consumed()


def test_emits_critical_openmetrics_service_check_when_service_is_down(
    dd_run_check, aggregator, instance, fake_http, fake_http_response
):
    fake_http_response(instance['openmetrics_endpoint'], status_code=404, match_options={'stream': True})
    check = SglangCheck('sglang', {}, [instance])

    with pytest.raises(Exception, match='HTTPClientStatusError'):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('sglang.openmetrics.health', ServiceCheck.CRITICAL)
    fake_http.assert_all_responses_consumed()


def test_check_skipped_when_gpu_monitoring_disabled(instance):
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': False}):
        with pytest.raises(SkipInstanceError):
            SglangCheck('sglang', {}, [instance])
