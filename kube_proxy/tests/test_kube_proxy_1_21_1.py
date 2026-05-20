# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.kube_proxy import KubeProxyCheck

from .common import make_mock_metrics

instance = {'prometheus_url': 'http://localhost:10249/metrics'}

# Constants
CHECK_NAME = 'kube_proxy'
NAMESPACE = 'kubeproxy'


@pytest.fixture()
def mock_iptables(mock_openmetrics_http):
    return make_mock_metrics(mock_openmetrics_http, 'metrics_iptables_1.21.1.txt')


@pytest.fixture()
def mock_userspace(mock_openmetrics_http):
    return make_mock_metrics(mock_openmetrics_http, 'metrics_userspace_1.21.1.txt')


def test_check_iptables(aggregator, mock_iptables, mock_healthcheck_wrapper):
    """
    Testing Kube_proxy in iptables mode.
    """
    c = KubeProxyCheck(CHECK_NAME, {}, [instance])
    c.check(instance)
    aggregator.assert_metric(NAMESPACE + '.cpu.time')
    aggregator.assert_metric(NAMESPACE + '.mem.resident')
    aggregator.assert_metric(NAMESPACE + '.mem.virtual')
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['code:200', 'host:kind-control-plane:6443', 'method:GET']
    )
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['code:201', 'host:kind-control-plane:6443', 'method:POST']
    )
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.duration.count')
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.duration.sum')
    aggregator.assert_metric(NAMESPACE + '.rest.client.exec_plugin.certificate.rotation.count')
    aggregator.assert_metric(NAMESPACE + '.rest.client.exec_plugin.certificate.rotation.sum')
    aggregator.assert_metric(NAMESPACE + '.rest.client.request.duration.count')
    aggregator.assert_metric(NAMESPACE + '.rest.client.request.duration.sum')
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.endpoint_changes.pending')
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.endpoint_changes.total')
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.iptables')
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.iptables.restore_failures')
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.last_queued_timestamp')
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.last_timestamp')
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.service_changes.pending')
    aggregator.assert_metric(NAMESPACE + '.sync_proxy.rules.service_changes.total')
    aggregator.assert_all_metrics_covered()


def test_check_userspace(aggregator, mock_userspace, mock_healthcheck_wrapper):
    """
    Testing Kube_proxy in userspace mode.
    """
    c = KubeProxyCheck(CHECK_NAME, {}, [instance])
    c.check(instance)
    aggregator.assert_metric(NAMESPACE + '.cpu.time')
    aggregator.assert_metric(NAMESPACE + '.mem.resident')
    aggregator.assert_metric(NAMESPACE + '.mem.virtual')
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['code:200', 'host:kind-control-plane:6443', 'method:GET']
    )
    aggregator.assert_metric(
        NAMESPACE + '.rest.client.requests', tags=['code:201', 'host:kind-control-plane:6443', 'method:POST']
    )
    aggregator.assert_metric(NAMESPACE + '.rest.client.exec_plugin.certificate.rotation.count')
    aggregator.assert_metric(NAMESPACE + '.rest.client.exec_plugin.certificate.rotation.sum')
    aggregator.assert_metric(NAMESPACE + '.rest.client.request.duration.count')
    aggregator.assert_metric(NAMESPACE + '.rest.client.request.duration.sum')
    aggregator.assert_all_metrics_covered()
