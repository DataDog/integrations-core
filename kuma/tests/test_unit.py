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
    return check


@pytest.mark.parametrize('histogram', HISTOGRAM_METRICS)
def test_histogram_metrics(aggregator, setup_kuma_check, histogram):
    histogram_name = 'kuma.' + histogram
    assert len(aggregator.histogram_bucket(histogram_name)) > 0, f"Histogram {histogram_name} not found"


@pytest.mark.parametrize('summary', SUMMARY_METRICS)
def test_summary_metrics(aggregator, setup_kuma_check, summary):
    aggregator.assert_metric('kuma.' + summary + '.count')
    aggregator.assert_metric('kuma.' + summary + '.sum')


@pytest.mark.parametrize('gauge', GAUGE_METRICS)
def test_gauge_metrics(aggregator, setup_kuma_check, gauge):
    aggregator.assert_metric('kuma.' + gauge)


@pytest.mark.parametrize('counter', COUNTER_METRICS)
def test_counter_metrics(aggregator, setup_kuma_check, counter):
    aggregator.assert_metric('kuma.' + counter + '.count')


def test_metrics_using_metadata(aggregator, setup_kuma_check):
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
