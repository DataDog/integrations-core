# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kuma import KumaCheck

from .test_metrics import (
    COUNTER_METRICS,
    GAUGE_METRICS,
    HISTOGRAM_METRICS,
    SUMMARY_METRICS,
)


@pytest.fixture
def setup_kuma_check(dd_run_check, instance, mock_http_response):
    mock_http_response(
        file_path=Path(__file__).parent.absolute() / "fixtures" / "metrics" / "control_plane" / "metrics.txt"
    )
    check = KumaCheck('kuma', {}, [instance])

    dd_run_check(check)

    dd_run_check(check)  # Run check again to ensure that shared tags are set.
    return check


EXPECTED_SHARED_TAGS = ['instance_id:kuma-control-plane-749c9bbc86-67tqs-7184', 'kuma_version:2.10.1']


@pytest.mark.parametrize('histogram', HISTOGRAM_METRICS)
def test_histogram_metrics(aggregator, setup_kuma_check, histogram):
    aggregator.assert_metric_has_tags('kuma.' + histogram + '.count', EXPECTED_SHARED_TAGS)
    aggregator.assert_metric_has_tags('kuma.' + histogram + '.sum', EXPECTED_SHARED_TAGS)
    aggregator.assert_metric_has_tags('kuma.' + histogram + '.count', EXPECTED_SHARED_TAGS)


@pytest.mark.parametrize('summary', SUMMARY_METRICS)
def test_summary_metrics(aggregator, setup_kuma_check, summary):
    aggregator.assert_metric_has_tags('kuma.' + summary + '.count', EXPECTED_SHARED_TAGS)
    aggregator.assert_metric_has_tags('kuma.' + summary + '.sum', EXPECTED_SHARED_TAGS)


@pytest.mark.parametrize('gauge', GAUGE_METRICS)
def test_gauge_metrics(aggregator, setup_kuma_check, gauge):
    aggregator.assert_metric_has_tags('kuma.' + gauge, EXPECTED_SHARED_TAGS)


@pytest.mark.parametrize('counter', COUNTER_METRICS)
def test_counter_metrics(aggregator, setup_kuma_check, counter):
    aggregator.assert_metric_has_tags('kuma.' + counter + '.count', EXPECTED_SHARED_TAGS)


def test_metrics_using_metadata(aggregator, setup_kuma_check):
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
