# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.nginx_ingress_controller import NginxIngressControllerCheck

instance = {'prometheus_url': 'http://localhost:10249/metrics'}

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


def test_nginx_ingress_controller(aggregator, mock_data):
    """
    Testing nginx ingress controller.
    """

    c = NginxIngressControllerCheck(CHECK_NAME, None, {}, [instance])
    c.check(instance)
    # nginx metrics
    aggregator.assert_metric(NAMESPACE + '.nginx.connections.current')
    aggregator.assert_metric(NAMESPACE + '.nginx.connections.total')
    aggregator.assert_metric(NAMESPACE + '.nginx.requests.total')
    # nginx process metrics
    aggregator.assert_metric(NAMESPACE + '.nginx.process.count')
    aggregator.assert_metric(NAMESPACE + '.nginx.bytes.read')
    aggregator.assert_metric(NAMESPACE + '.nginx.bytes.write')
    aggregator.assert_metric(NAMESPACE + '.nginx.cpu.time')
    aggregator.assert_metric(NAMESPACE + '.nginx.mem.resident')
    aggregator.assert_metric(NAMESPACE + '.nginx.mem.virtual')
    # controller metrics
    aggregator.assert_metric(NAMESPACE + '.controller.reload.success')
    aggregator.assert_metric(NAMESPACE + '.controller.upstream.latency.count')
    aggregator.assert_metric(NAMESPACE + '.controller.upstream.latency.sum')
    aggregator.assert_metric(NAMESPACE + '.controller.upstream.latency.quantile')
    aggregator.assert_metric(NAMESPACE + '.controller.requests')
    aggregator.assert_metric(NAMESPACE + '.controller.cpu.time')
    aggregator.assert_metric(NAMESPACE + '.controller.mem.resident')
    aggregator.assert_metric(NAMESPACE + '.controller.mem.virtual')

    aggregator.assert_all_metrics_covered()
