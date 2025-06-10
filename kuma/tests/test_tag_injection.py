# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any, Callable, Dict  # noqa: F401

import pytest
from prometheus_client.core import CounterMetricFamily, Sample

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.kuma import KumaCheck
from datadog_checks.kuma.check import KumaOpenMetricsScraper


@pytest.fixture
def setup_check(dd_run_check, instance, mock_http_response):
    """Fixture to set up and run the KumaCheck with a mocked HTTP response."""
    mock_http_response(
        file_path=Path(__file__).parent.absolute() / "fixtures" / "metrics" / "control_plane" / "metrics_code_class.txt"
    )
    check = KumaCheck('kuma', {}, [instance])
    dd_run_check(check)

@pytest.mark.parametrize(
    'code,expected_class',
    [
        pytest.param('200', '2XX', id='2xx-ok'),
        pytest.param('302', '3XX', id='3xx-found'),
        pytest.param('401', '4XX', id='4xx-unauthorized'),
        pytest.param('500', '5XX', id='5xx-internal'),
    ],
)
@pytest.mark.usefixtures("aggregator", "setup_check")
def test_code_class_injection_valid_codes(aggregator, code, expected_class):
    """Test that valid HTTP status codes get correct code_class tags"""
    metric_name = 'kuma.api_server.http_requests_inflight'
    aggregator.assert_metric(metric_name)

    # Test that the specific code gets correct code_class - filter metrics with the code first
    matching_metrics = [
        metric_point for metric_point in aggregator.metrics(metric_name) if f'code:{code}' in metric_point.tags
    ]

    assert matching_metrics, f"No metric found for {metric_name} with tag code:{code}"

    for metric_point in matching_metrics:
        assert (
            f'code_class:{expected_class}' in metric_point.tags
        ), f"Expected code_class:{expected_class} for code:{code}, got tags: {metric_point.tags}"


@pytest.mark.parametrize(
    'edge_code',
    [
        pytest.param('20', id='edge-2digit'),
        pytest.param('2000', id='edge-4digit'),
        pytest.param('abc', id='edge-non-numeric'),
        pytest.param('2a0', id='edge-mixed'),
        pytest.param('', id='edge-empty'),
    ],
)
@pytest.mark.usefixtures("aggregator", "setup_check")
def test_code_class_injection_edge_cases(aggregator, edge_code):
    """Test cases where code tags should not get code_class tags"""
    metric_name = 'kuma.api_server.http_requests_inflight'
    aggregator.assert_metric(metric_name)

    # These should NOT have code_class - filter metrics with the specific code first
    matching_metrics = [
        metric_point for metric_point in aggregator.metrics(metric_name) if f'code:{edge_code}' in metric_point.tags
    ]

    assert matching_metrics, f"No metric found for {metric_name} with tag code:{edge_code}"

    for metric_point in matching_metrics:
        assert not any(
            'code_class:' in tag for tag in metric_point.tags
        ), f"Code:{edge_code} should not have code_class, got tags: {metric_point.tags}"


@pytest.mark.usefixtures("aggregator", "setup_check")
def test_code_class_injection_no_code_label(aggregator):
    """Test that metrics without code label do not get code_class tags"""
    metric_name = 'kuma.api_server.http_requests_inflight'
    aggregator.assert_metric(metric_name)

    found_metric = False
    # No code label should not have code_class
    for metric_point in aggregator.metrics(metric_name):
        if 'handler:/no-code' in metric_point.tags:
            found_metric = True
            assert not any(
                'code_class:' in tag for tag in metric_point.tags
            ), f"Metric with handler:/no-code should not have code_class, got tags: {metric_point.tags}"
    assert found_metric, f"No metric found for {metric_name} with tag handler:/no-code"


@pytest.mark.parametrize(
    'code,expected_class',
    [
        pytest.param('200', '2XX', id='2xx-ok'),
        pytest.param('302', '3XX', id='3xx-found'),
        pytest.param('401', '4XX', id='4xx-unauthorized'),
        pytest.param('500', '5XX', id='5xx-internal'),
        pytest.param('20', None, id='edge-2digit'),
        pytest.param('2000', None, id='edge-4digit'),
        pytest.param('abc', None, id='edge-non-numeric'),
        pytest.param('2a0', None, id='edge-mixed'),
        pytest.param('', None, id='edge-empty'),
        pytest.param(None, None, id='edge-no-code'),
    ],
)
def test_code_class_injection_unit(code, expected_class):
    """Unit test for the _inject_code_class method"""

    metric = CounterMetricFamily('test_metric', 'Test metric')
    if code is not None:
        sample = Sample('test_metric', {'code': code}, 1.0, None)
    else:
        sample = Sample('test_metric', {}, 1.0, None)
    metric.samples = [sample]

    modified_metric = KumaOpenMetricsScraper.inject_code_class(metric)
    sample = modified_metric.samples[0]

    assert sample.labels.get('code_class') == expected_class, f"Expected code_class {expected_class} for code {code}"


def test_code_class_preserves_labels_and_idempotent():
    """Test that code_class injection preserves labels and is idempotent"""

    # Test preserving labels
    metric = CounterMetricFamily('test_metric', 'Test')
    original_labels = {'code': '200', 'method': 'GET', 'handler': '/api', 'custom': 'value'}
    metric.samples = [Sample('test_metric', original_labels.copy(), 42.0, None)]

    modified = KumaOpenMetricsScraper.inject_code_class(metric)
    sample = modified.samples[0]

    # All original labels preserved
    for k, v in original_labels.items():
        assert sample.labels[k] == v
    assert sample.labels['code_class'] == '2XX'
    assert sample.value == 42.0

    # Test idempotency
    modified_twice = KumaOpenMetricsScraper.inject_code_class(modified)
    sample = modified_twice.samples[0]
    assert sample.labels['code_class'] == '2XX'  # should remain 2XX
    assert sum(1 for k in sample.labels if k == 'code_class') == 1
