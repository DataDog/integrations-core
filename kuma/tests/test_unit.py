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


@pytest.fixture()
def setup_kuma_check(dd_run_check, instance, mock_http_response):
    mock_http_response(
        file_path=Path(__file__).parent.absolute() / "fixtures" / "metrics" / "control_plane" / "metrics.txt"
    )
    check = KumaCheck('kuma', {}, [instance])

    dd_run_check(check)
    dd_run_check(check)  # Run check again to ensure that shared tags are set.


EXPECTED_SHARED_TAGS = ['instance_id:kuma-control-plane-749c9bbc86-67tqs-7184', 'kuma_version:2.10.1']


@pytest.mark.usefixtures("aggregator", "setup_kuma_check")
@pytest.mark.parametrize(
    'metrics, suffixes',
    [
        pytest.param(HISTOGRAM_METRICS, ['.count', '.sum', '.bucket'], id='histograms'),
        pytest.param(SUMMARY_METRICS, ['.count', '.sum'], id='summaries'),
        pytest.param(GAUGE_METRICS, [], id='gauges'),
        pytest.param(COUNTER_METRICS, ['.count'], id='counters'),
    ],
)
def test_histogram_metrics(aggregator, metrics, suffixes):
    # Collect all the assertion failures and raise them at the end,
    # so that we can see all the missing metrics and tags at once.
    errors = []
    for metric_name in metrics:
        for suffix in suffixes:
            try:
                aggregator.assert_metric_has_tags('kuma.' + metric_name + suffix, EXPECTED_SHARED_TAGS)
            except AssertionError as e:
                error_message = (
                    f"--> Assertion failed for: {aggregator.assert_metric_has_tags.__name__}\n"
                    f"    Args: {metric_name + suffix}\n"
                    f"    Error: {e}"
                )
                errors.append(error_message)
    if errors:
        raise AssertionError("Found metric or tag mismatches:\n" + "\n".join(errors))


@pytest.mark.usefixtures("aggregator", "setup_kuma_check")
def test_metrics_using_metadata(aggregator):
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
