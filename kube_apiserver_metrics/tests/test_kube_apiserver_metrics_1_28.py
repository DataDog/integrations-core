# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.kube_apiserver_metrics import KubeAPIServerMetricsCheck

from .common import HERE

OM_RESPONSE_FIXTURES = os.path.join(HERE, 'fixtures', 'metrics_1.28.0.txt')

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
        'rest_client_requests_total',
        'authenticated_user_requests',
        'apiserver_request_total',
        'apiserver_request_terminations_total',
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
        'request_duration_seconds.sum',
        'request_duration_seconds.count',
        'process_resident_memory_bytes',
        'process_virtual_memory_bytes',
        'etcd.db.total_size',
        'etcd_request_duration_seconds.sum',
        'etcd_request_duration_seconds.count',
        'watch_events_sizes.sum',
        'watch_events_sizes.count',
        'authentication_duration_seconds.sum',
        'authentication_duration_seconds.count',
        'authentication_attempts',
        'storage_objects',
        'storage_list_total',
        'storage_list_fetched_objects_total',
        'storage_list_evaluated_objects_total',
        'storage_list_returned_objects_total',
        'requested_deprecated_apis',
        'kubernetes_feature_enabled',
        'aggregator_unavailable_apiservice',
        'envelope_encryption_dek_cache_fill_percent',
        'flowcontrol_current_executing_requests',
        'flowcontrol_request_concurrency_limit',
        'flowcontrol_current_inqueue_requests',
        'flowcontrol_dispatched_requests_total',
        'etcd_requests_total',
        'etcd_request_errors_total',
    ]
    COUNT_METRICS = [
        'audit_event.count',
        'rest_client_requests_total.count',
        'authenticated_user_requests.count',
        'apiserver_request_total.count',
        'apiserver_request_terminations_total.count',
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
            if "aggregator_unavailable_apiservice" in metric:
                aggregator.assert_metric_has_tag(metric_to_assert, "apiservice_name:v1.")
        aggregator.assert_all_metrics_covered()
