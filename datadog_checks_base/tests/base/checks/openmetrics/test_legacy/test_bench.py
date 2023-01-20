# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base import OpenMetricsBaseCheck
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


def test_ksm_old(benchmark, dd_run_check, mock_http_response, fixture_ksm):
    mock_http_response(file_path=fixture_ksm)
    instance = {'prometheus_url': 'foo', 'namespace': 'bar', 'metrics': ['*']}
    c = OpenMetricsBaseCheck('test', {}, [instance])

    # Run once to get initialization steps out of the way.
    dd_run_check(c)

    benchmark(c.check, instance)


def test_amazon_msk_jmx_metrics_old(benchmark, dd_run_check, mock_http_response, fixture_amazon_msk_jmx_metrics):
    mock_http_response(file_path=fixture_amazon_msk_jmx_metrics)
    instance = {
        'prometheus_url': 'foo',
        'namespace': 'bar',
        'metrics': [AMAZON_MSK_JMX_METRICS_MAP],
        'type_overrides': AMAZON_MSK_JMX_METRICS_OVERRIDES,
    }
    c = OpenMetricsBaseCheck('test', {}, [instance])

    # Run once to get initialization steps out of the way.
    dd_run_check(c)

    benchmark(c.check, instance)


def test_label_joins_old(benchmark, dd_run_check, mock_http_response, fixture_ksm):
    mock_http_response(file_path=fixture_ksm)
    instance = {
        'prometheus_url': 'foo',
        'namespace': 'bar',
        'label_to_hostname': 'node',
        'metrics': ['*'],
        'label_joins': {
            'kube_pod_info': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
            '1': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
            '2': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
            '3': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
            '4': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
            '5': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
            '6': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
            '7': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
            '8': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
            '9': {'labels_to_match': ['pod', 'namespace'], 'labels_to_get': ['node']},
        },
    }
    c = OpenMetricsBaseCheck('test', {}, [instance])

    # Run once to get initialization steps out of the way.
    dd_run_check(c)

    benchmark(c.check, instance)
