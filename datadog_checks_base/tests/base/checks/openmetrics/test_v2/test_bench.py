# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.dev import get_here
from datadog_checks.dev.testing import requires_py3

from ..bench_utils import AMAZON_MSK_JMX_METRICS_MAP, AMAZON_MSK_JMX_METRICS_OVERRIDES

pytestmark = [requires_py3]

HERE = get_here()
FIXTURE_PATH = os.path.abspath(os.path.join(os.path.dirname(HERE), '..', '..', '..', 'fixtures', 'prometheus'))


@pytest.fixture
def fixture_ksm():
    return os.path.join(FIXTURE_PATH, 'ksm.txt')


@pytest.fixture
def fixture_amazon_msk_jmx_metrics():
    return os.path.join(FIXTURE_PATH, 'amazon_msk_jmx_metrics.txt')


def test_ksm_new(benchmark, dd_run_check, mock_http_response, fixture_ksm):
    mock_http_response(file_path=fixture_ksm)
    c = OpenMetricsBaseCheckV2('test', {}, [{'openmetrics_endpoint': 'foo', 'namespace': 'bar', 'metrics': ['.+']}])

    # Run once to get initialization steps out of the way.
    dd_run_check(c)

    benchmark(c.check, None)


def test_amazon_msk_jmx_metrics_new(benchmark, dd_run_check, mock_http_response, fixture_amazon_msk_jmx_metrics):
    mock_http_response(file_path=fixture_amazon_msk_jmx_metrics)

    metrics = []
    for raw_metric_name, metric_name in AMAZON_MSK_JMX_METRICS_MAP.items():
        config = {raw_metric_name: {'name': metric_name}}
        if raw_metric_name in AMAZON_MSK_JMX_METRICS_OVERRIDES:
            config[raw_metric_name]['type'] = AMAZON_MSK_JMX_METRICS_OVERRIDES[raw_metric_name]

        metrics.append(config)

    c = OpenMetricsBaseCheckV2('test', {}, [{'openmetrics_endpoint': 'foo', 'namespace': 'bar', 'metrics': metrics}])

    # Run once to get initialization steps out of the way.
    dd_run_check(c)

    benchmark(c.check, None)


def test_label_joins_new(benchmark, dd_run_check, mock_http_response, fixture_ksm):
    mock_http_response(file_path=fixture_ksm)
    instance = {
        'openmetrics_endpoint': 'foo',
        'namespace': 'bar',
        'hostname_label': 'node',
        'metrics': ['.+'],
        'share_labels': {
            'kube_pod_info': {'match': ['pod', 'namespace'], 'labels': ['node'], 'values': [1]},
            '1': {'match': ['pod', 'namespace'], 'labels': ['node'], 'values': [1]},
            '2': {'match': ['pod', 'namespace'], 'labels': ['node'], 'values': [1]},
            '3': {'match': ['pod', 'namespace'], 'labels': ['node'], 'values': [1]},
            '4': {'match': ['pod', 'namespace'], 'labels': ['node'], 'values': [1]},
            '5': {'match': ['pod', 'namespace'], 'labels': ['node'], 'values': [1]},
            '6': {'match': ['pod', 'namespace'], 'labels': ['node'], 'values': [1]},
            '7': {'match': ['pod', 'namespace'], 'labels': ['node'], 'values': [1]},
            '8': {'match': ['pod', 'namespace'], 'labels': ['node'], 'values': [1]},
            '9': {'match': ['pod', 'namespace'], 'labels': ['node'], 'values': [1]},
        },
    }
    c = OpenMetricsBaseCheckV2('test', {}, [instance])

    # Run once to get initialization steps out of the way.
    dd_run_check(c)

    benchmark(c.check, None)
