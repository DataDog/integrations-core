# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import os

import mock
import pytest

from datadog_checks.kube_apiserver_metrics import KubeAPIServerMetricsCheck

customtag = "custom:tag"

instance = {
    'prometheus_url': 'https://localhost:443/metrics',
    'bearer_token_auth': 'false',
    'tags': [customtag],
}


@pytest.fixture()
def mock_get():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics_1.25.3.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain", 'Authorization': "Bearer XXX"},
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
        NAMESPACE + '.etcd.db.total_size',
        NAMESPACE + '.rest_client_requests_total',
        NAMESPACE + '.authenticated_user_requests',
        NAMESPACE + '.apiserver_request_total',
        NAMESPACE + '.apiserver_request_terminations_total',
        NAMESPACE + '.grpc_client_handled_total',
        NAMESPACE + '.grpc_client_msg_received_total',
        NAMESPACE + '.grpc_client_msg_sent_total',
        NAMESPACE + '.grpc_client_started_total',
        NAMESPACE + '.rest_client_request_latency_seconds.sum',
        NAMESPACE + '.rest_client_request_latency_seconds.count',
        NAMESPACE + '.admission_step_admission_latencies_seconds.sum',
        NAMESPACE + '.admission_step_admission_latencies_seconds.count',
        NAMESPACE + '.admission_step_admission_latencies_seconds_summary.sum',
        NAMESPACE + '.admission_step_admission_latencies_seconds_summary.count',
        NAMESPACE + '.admission_step_admission_latencies_seconds_summary.quantile',
        NAMESPACE + '.admission_controller_admission_duration_seconds.sum',
        NAMESPACE + '.admission_controller_admission_duration_seconds.count',
        NAMESPACE + '.request_duration_seconds.sum',
        NAMESPACE + '.request_duration_seconds.count',
        NAMESPACE + '.process_resident_memory_bytes',
        NAMESPACE + '.process_virtual_memory_bytes',
        NAMESPACE + '.etcd_request_duration_seconds.sum',
        NAMESPACE + '.etcd_request_duration_seconds.count',
        NAMESPACE + '.watch_events_sizes.sum',
        NAMESPACE + '.watch_events_sizes.count',
        NAMESPACE + '.authentication_duration_seconds.sum',
        NAMESPACE + '.authentication_duration_seconds.count',
        NAMESPACE + '.authentication_attempts',
        NAMESPACE + '.storage_objects',
        NAMESPACE + '.storage_list_total',
        NAMESPACE + '.storage_list_fetched_objects_total',
        NAMESPACE + '.storage_list_evaluated_objects_total',
        NAMESPACE + '.storage_list_returned_objects_total',
        NAMESPACE + '.requested_deprecated_apis',
        NAMESPACE + '.apiserver_admission_webhook_fail_open_count',
        NAMESPACE + '.admission_webhook_admission_latencies_seconds.sum',
        NAMESPACE + '.admission_webhook_admission_latencies_seconds.count',
        NAMESPACE + '.kubernetes_feature_enabled',
        NAMESPACE + '.aggregator_unavailable_apiservice',
        NAMESPACE + '.envelope_encryption_dek_cache_fill_percent',
        NAMESPACE + '.flowcontrol_request_concurrency_limit',
        NAMESPACE + '.flowcontrol_current_executing_requests',
        NAMESPACE + '.flowcontrol_rejected_requests_total',
        NAMESPACE + '.flowcontrol_current_inqueue_requests',
        NAMESPACE + '.flowcontrol_dispatched_requests_total',
    ]
    COUNT_METRICS = [
        NAMESPACE + '.audit_event.count',
        NAMESPACE + '.rest_client_requests_total.count',
        NAMESPACE + '.authenticated_user_requests.count',
        NAMESPACE + '.apiserver_request_total.count',
        NAMESPACE + '.apiserver_request_terminations_total.count',
        NAMESPACE + '.apiserver_admission_webhook_fail_open_count.count',
    ]

    def test_check(self, dd_run_check, aggregator, mock_get):
        """
        Testing kube_apiserver_metrics metrics collection.
        """

        check = KubeAPIServerMetricsCheck('kube_apiserver_metrics', {}, [instance])
        dd_run_check(check)

        # check that we then get the count metrics also
        dd_run_check(check)

        for metric in self.METRICS + self.COUNT_METRICS:
            aggregator.assert_metric(metric)
            aggregator.assert_metric_has_tag(metric, customtag)
            if "aggregator_unavailable_apiservice" in metric:
                aggregator.assert_metric_has_tag(metric, "apiservice_name:v1.")
        aggregator.assert_all_metrics_covered()
