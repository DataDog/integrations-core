# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kuma import KumaCheck

import pytest
from pathlib import Path

EXPECTED_METRICS = [
]

EXPECTED_SUMMARIES = [
]
def test_check(dd_run_check, aggregator, instance, mock_http_response):
    # FIXME
    return
    mock_http_response(file_path=Path(__file__).parent.absolute() / "fixtures" / "metrics" / "kuma.txt")
    check = KumaCheck('kuma', {}, [instance])
    dd_run_check(check)
    for m in EXPECTED_METRICS:
        aggregator.assert_metric('kuma.' + m)
    for sm in EXPECTED_SUMMARIES:
        aggregator.assert_metric('kuma.' + sm + '.count')
        aggregator.assert_metric('kuma.' + sm + '.sum')
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

def test_histogram_buckets_as_distributions_default_true():
    instance = {'openmetrics_endpoint': 'http://localhost:5680/metrics'}
    check = KumaCheck('kuma', {}, [instance])
    merged_config = check.get_config_with_defaults(instance)
    value = merged_config.get('histogram_buckets_as_distributions', None)
    assert value is True, (
        f"Expected histogram_buckets_as_distributions to default to True, got {value!r}"
    )
