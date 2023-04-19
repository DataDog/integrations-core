# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import tempfile

import mock
import pytest

from datadog_checks.kube_apiserver_metrics import KubeAPIServerMetricsCheck

from .common import APISERVER_INSTANCE_BEARER_TOKEN, HERE

OM_RESPONSE_FIXTURES = os.path.join(HERE, 'fixtures', 'metrics.txt')

customtag = "custom:tag"

minimal_instance = {'prometheus_url': 'https://localhost:443/metrics'}
minimal_instance_legacy = {'prometheus_url': 'localhost:443/metrics'}

instance = {
    'prometheus_url': 'https://localhost:443/metrics',
    'bearer_token_auth': 'false',
    'tags': [customtag],
}

instanceSecure = {
    'prometheus_url': 'https://localhost:443/metrics',
    'bearer_token_auth': 'true',
    'tags': [customtag],
}


@pytest.fixture()
def mock_read_bearer_token():
    with mock.patch('datadog_checks.checks.openmetrics.OpenMetricsBaseCheck._get_bearer_token', return_value="XXX"):
        yield


class TestKubeAPIServerMetrics:
    """Basic Test for kube_apiserver integration."""

    METRICS = [
        'longrunning_gauge',
        'current_inflight_requests',
        'audit_event',
        'go_threads',
        'go_goroutines',
        'APIServiceRegistrationController_depth',
        'etcd_object_counts',
        'rest_client_requests_total',
        'apiserver_request_count',
        'apiserver_dropped_requests_total',
        'http_requests_total',
        'authenticated_user_requests',
        'rest_client_request_latency_seconds.sum',
        'rest_client_request_latency_seconds.count',
        'admission_webhook_admission_latencies_seconds.sum',
        'admission_webhook_admission_latencies_seconds.count',
        'admission_step_admission_latencies_seconds.sum',
        'admission_step_admission_latencies_seconds.count',
        'admission_step_admission_latencies_seconds_summary.sum',
        'admission_step_admission_latencies_seconds_summary.count',
        'admission_step_admission_latencies_seconds_summary.quantile',
        'admission_controller_admission_duration_seconds.sum',
        'admission_controller_admission_duration_seconds.count',
        'request_latencies.sum',
        'request_latencies.count',
        'process_resident_memory_bytes',
        'process_virtual_memory_bytes',
    ]
    COUNT_METRICS = [
        'audit_event.count',
        'rest_client_requests_total.count',
        'apiserver_request_count.count',
        'apiserver_dropped_requests_total.count',
        'http_requests_total.count',
        'authenticated_user_requests.count',
    ]

    def test_check(self, dd_run_check, aggregator, mock_http_response):
        """
        Testing kube_apiserver_metrics metrics collection.
        """
        NAMESPACE = 'kube_apiserver'
        mock_http_response(file_path=OM_RESPONSE_FIXTURES)
        check = KubeAPIServerMetricsCheck('kube_apiserver_metrics', {}, [instance])
        dd_run_check(check)

        # check that we then get the count metrics also
        dd_run_check(check)

        for metric in self.METRICS + self.COUNT_METRICS:
            metric_to_assert = NAMESPACE + "." + metric
            aggregator.assert_metric(metric_to_assert)
            aggregator.assert_metric_has_tag(metric_to_assert, customtag)
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

        check = KubeAPIServerMetricsCheck('kube_apiserver_metrics', {}, [instanceSecure])
        apiserver_instance = check._create_kube_apiserver_metrics_instance(instanceSecure)
        configured_instance = check.get_scraper_config(apiserver_instance)

        os.remove(temp_bearer_file)
        assert configured_instance["_bearer_token"] == APISERVER_INSTANCE_BEARER_TOKEN

    def test_default_config(self, dd_run_check, aggregator, mock_read_bearer_token):
        """
        Testing the default configuration.
        """
        check = KubeAPIServerMetricsCheck('kube_apiserver_metrics', {}, [minimal_instance])

        check.process = mock.MagicMock()
        dd_run_check(check)

        apiserver_instance = check.kube_apiserver_config

        assert not apiserver_instance["ssl_verify"]
        assert apiserver_instance["bearer_token_auth"]
        assert apiserver_instance["prometheus_url"] == "https://localhost:443/metrics"

    def test_default_config_legacy(self, dd_run_check, aggregator, mock_read_bearer_token):
        """
        Testing the default legacy configuration.
        """
        check = KubeAPIServerMetricsCheck('kube_apiserver_metrics', {}, [minimal_instance_legacy])
        check.process = mock.MagicMock()
        dd_run_check(check)

        apiserver_instance = check.kube_apiserver_config

        assert not apiserver_instance["ssl_verify"]
        assert apiserver_instance["bearer_token_auth"]
        assert apiserver_instance["prometheus_url"] == "https://localhost:443/metrics"
