# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.nginx_ingress_controller import NginxIngressControllerCheck

INSTANCE_HISTO = {'prometheus_url': 'http://localhost:10249/metrics', 'collect_nginx_histograms': True}

CHECK_NAME = 'nginx_ingress_controller'
NAMESPACE = 'nginx_ingress'


@pytest.fixture()
def mock_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


EXPECTED_METRICS = [
    # nginx metrics
    '.nginx.connections.current',
    '.nginx.connections.total',
    '.nginx.requests.total',
    # nginx process metrics
    '.nginx.bytes.read',
    '.nginx.process.count',
    '.nginx.bytes.write',
    '.nginx.cpu.time',
    '.nginx.mem.resident',
    '.nginx.mem.virtual',
    # controller metrics
    '.controller.reload.success',
    '.controller.last.reload.success',
    '.controller.upstream.latency.count',
    '.controller.upstream.latency.sum',
    '.controller.upstream.latency.quantile',
    '.controller.requests',
    '.controller.cpu.time',
    '.controller.mem.resident',
    '.controller.mem.virtual',
]


def test_nginx_ingress_controller(aggregator, instance, mock_data):
    """
    Testing nginx ingress controller.
    """

    c = NginxIngressControllerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(NAMESPACE + metric)

    # By default, the integration does not collect histogram metrics due to high label cardinality
    aggregator.assert_metric(NAMESPACE + '.controller.response.duration.count', count=0)
    aggregator.assert_metric(NAMESPACE + '.controller.response.duration.sum', count=0)
    aggregator.assert_metric(NAMESPACE + '.controller.request.duration.count', count=0)
    aggregator.assert_metric(NAMESPACE + '.controller.request.duration.sum', count=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_with_histograms(aggregator, mock_data):
    """
    Testing nginx ingress controller with `collect_histogram` enabled.
    """
    c = NginxIngressControllerCheck(CHECK_NAME, {}, [INSTANCE_HISTO])
    c.check(INSTANCE_HISTO)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(NAMESPACE + metric)

    aggregator.assert_metric(NAMESPACE + '.controller.response.duration.count')
    aggregator.assert_metric(NAMESPACE + '.controller.response.duration.sum')
    aggregator.assert_metric(NAMESPACE + '.controller.request.duration.count')
    aggregator.assert_metric(NAMESPACE + '.controller.request.duration.sum')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
