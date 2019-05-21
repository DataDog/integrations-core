# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import os

from datadog_checks.kube_apiserver_metrics import KubeApiserverMetricsCheck
import mock
import pytest

customtag = "custom:tag"

instance = {'prometheus_url': 'localhost:443/metrics',
            'scheme': 'https',
            'bearer_token_path': '/tmp/foo',
            'tags': [customtag]}


@pytest.fixture()
def mock_get():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain", 'Authorization': "Bearer XXX"}
        ),
    ):
        yield


@pytest.fixture()
def mock_bearer_retrieve():
    with mock.patch(
        'datadog_checks.kube_apiserver_metrics.KubeApiserverMetricsCheck.get_bearer_token',
        return_value=True
    ):
        yield


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator

    aggregator.reset()
    return aggregator


class TestKubeApiserverMetrics:
    """Basic Test for kube_dns integration."""

    CHECK_NAME = 'kube_apiserver_metrics'
    NAMESPACE = 'kube_apiserver'
    METRICS = [
        NAMESPACE + '.longrunning_gauge',
        NAMESPACE + '.current_inflight_requests',
        NAMESPACE + '.audit_event',

    ]
    COUNT_METRICS = [
        NAMESPACE + '.audit_event.count',
    ]

    def test_check(self, aggregator, mock_get, mock_bearer_retrieve):
        """
        Testing kube_apiserver_metrics check.
        """

        check = KubeApiserverMetricsCheck('kube_apiserver_metrics', {}, {}, [instance])
        check.check(instance)

        # check that we then get the count metrics also
        check.check(instance)

        for metric in self.METRICS + self.COUNT_METRICS:
            aggregator.assert_metric(metric)
            aggregator.assert_metric_has_tag(metric, customtag)
        aggregator.assert_all_metrics_covered()
