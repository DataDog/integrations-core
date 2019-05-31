# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import os
import tempfile
import mock
import pytest

from datadog_checks.kube_apiserver_metrics import KubeAPIServerMetricsCheck
from .common import APISERVER_INSTANCE_BEARER_TOKEN

customtag = "custom:tag"

instance = {'prometheus_url': 'localhost:443/metrics',
            'scheme': 'https',
            'tags': [customtag]}

instanceSecure = {
            'prometheus_url': 'localhost:443/metrics',
            'scheme': 'https',
            'bearer_token_auth': 'true',
            'tags': [customtag]
}

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


class TestKubeAPIServerMetrics:
    """Basic Test for kube_apiserver integration."""

    CHECK_NAME = 'kube_apiserver_metrics'
    NAMESPACE = 'kube_apiserver'
    METRICS = [
        NAMESPACE + '.longrunning_gauge',
        NAMESPACE + '.current_inflight_requests',
        NAMESPACE + '.audit_event',
        NAMESPACE + '.go_threads',
        NAMESPACE + '.go_goroutines',
        NAMESPACE + '.APIServiceRegistrationController_depth',
        NAMESPACE + '.etcd_object_counts',
        NAMESPACE + '.rest_client_requests_total',
        NAMESPACE + '.apiserver_request_count',
        NAMESPACE + '.apiserver_dropped_requests_total',
        NAMESPACE + '.http_requests_total',
        NAMESPACE + '.authenticated_user_requests',
    ]
    COUNT_METRICS = [
        NAMESPACE + '.audit_event.count',
        NAMESPACE + '.rest_client_requests_total.count',
        NAMESPACE + '.apiserver_request_count.count',
        NAMESPACE + '.apiserver_dropped_requests_total.count',
        NAMESPACE + '.http_requests_total.count',
        NAMESPACE + '.authenticated_user_requests.count',
    ]

    def test_check(self, aggregator, mock_get):
        """
        Testing kube_apiserver_metrics check.
        """

        check = KubeAPIServerMetricsCheck('kube_apiserver_metrics', {}, {}, [instance])
        check.check(instance)

        # check that we then get the count metrics also
        check.check(instance)

        for metric in self.METRICS + self.COUNT_METRICS:
            aggregator.assert_metric(metric)
            aggregator.assert_metric_has_tag(metric, customtag)
        aggregator.assert_all_metrics_covered()

    def test_bearer(self):
        """
        Testing the bearer token configuration.
        """
        temp_dir = tempfile.mkdtemp()
        temp_bearer_file = os.path.join(temp_dir, "foo")
        with open(temp_bearer_file, "w+") as f:
            f.write("XXX")
        instanceSecure["bearer_token_path"] = temp_bearer_file

        check = KubeAPIServerMetricsCheck('kube_apiserver_metrics', {}, {}, [instanceSecure])
        apiserver_instance = check._create_kube_apiserver_metrics_instance(instanceSecure)
        configured_instance = check.get_scraper_config(apiserver_instance)

        os.remove(temp_bearer_file)
        assert configured_instance["_bearer_token"] == APISERVER_INSTANCE_BEARER_TOKEN
