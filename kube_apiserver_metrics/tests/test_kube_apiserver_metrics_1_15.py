# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.kube_apiserver_metrics import KubeAPIServerMetricsCheck

from .common import HERE

OM_RESPONSE_FIXTURES = os.path.join(HERE, 'fixtures', 'metrics_1.15.0.txt')

customtag = "custom:tag"

instance = {
    'prometheus_url': 'https://localhost:443/metrics',
    'bearer_token_auth': 'false',
    'tags': [customtag],
}


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
        'apiserver_request_total',
        'grpc_client_handled_total',
        'grpc_client_msg_received_total',
        'grpc_client_msg_sent_total',
        'grpc_client_started_total',
        'rest_client_request_latency_seconds.sum',
        'rest_client_request_latency_seconds.count',
        'admission_step_admission_latencies_seconds.sum',
        'admission_step_admission_latencies_seconds.count',
        'admission_step_admission_latencies_seconds_summary.sum',
        'admission_step_admission_latencies_seconds_summary.count',
        'admission_step_admission_latencies_seconds_summary.quantile',
        'admission_controller_admission_duration_seconds.sum',
        'admission_controller_admission_duration_seconds.count',
        'request_latencies.sum',
        'request_latencies.count',
        'request_duration_seconds.sum',
        'request_duration_seconds.count',
        'registered_watchers',
        'process_resident_memory_bytes',
        'process_virtual_memory_bytes',
        'etcd_request_duration_seconds.sum',
        'etcd_request_duration_seconds.count',
    ]
    COUNT_METRICS = [
        'audit_event.count',
        'rest_client_requests_total.count',
        'apiserver_request_count.count',
        'apiserver_dropped_requests_total.count',
        'http_requests_total.count',
        'authenticated_user_requests.count',
        'apiserver_request_total.count',
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
